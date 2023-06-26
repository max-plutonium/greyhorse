from functools import partial
from typing import Callable, Type, Mapping, Any, Sequence, TypeVar, cast, Generic

from sqlalchemy import update, CursorResult, select, delete, ColumnCollection, Column, inspect, tuple_, func, \
    literal_column, exists
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncSession as SqlaAsyncSession
from sqlalchemy.orm import Session as SqlaSyncSession, attributes
from sqlalchemy.orm.base import instance_state

from greyhorse_core.data.repositories.base import IdType, ModelType, ModelFactory, EntityType, EntityFactory
from greyhorse_core.data.repositories.filterable import FilterableRepository
from greyhorse_core.engines.base import SyncSessionFactory as BaseSyncSessionFactory, \
    AsyncSessionFactory as BaseAsyncSessionFactory
from greyhorse_core.utils.invoke import is_awaitable
from greyhorse_sqla.model import SqlaModel
from greyhorse_sqla.query import SqlaFiltersQuery, SqlaSortingQuery

SyncSessionFactory = BaseSyncSessionFactory[SqlaSyncSession]
AsyncSessionFactory = BaseAsyncSessionFactory[SqlaAsyncSession]

SqlaModelType = TypeVar('SqlaModelType', bound=SqlaModel, covariant=True)
SqlaModelTypeFactory = Callable[..., SqlaModelType]


class SqlaRepository(
    FilterableRepository[IdType, EntityType, SqlaFiltersQuery, SqlaSortingQuery],
    Generic[IdType, EntityType],
):
    def __init__(
        self, class_: Type[EntityType],
        session_factory: AsyncSessionFactory,
        factory: EntityFactory | None = None,
    ):
        super().__init__(class_, factory)
        self._session_factory = session_factory
        self._model_factory = partial(self._construct_instances, self.entity_factory)

        try:
            column_names_map = inspect(class_).c
        except NoInspectionAvailable:
            self._column_names_map = dict()
        else:
            column_names_map = zip([column.name for column in column_names_map], column_names_map.keys())
            self._column_names_map = dict(column_names_map)

    def _get_id_columns(self) -> ColumnCollection:
        return self.entity_class.__table__.primary_key.columns

    def _get_field_by_column(self, c: Column) -> str:
        return self._column_names_map.get(c.name)

    async def _construct_instances(
            self, model_factory: ModelFactory, _from_cache: bool = False,
            **kwargs: Mapping[str, Any]) -> ModelType:
        if not _from_cache:
            return model_factory(**kwargs)

        instance = model_factory()
        assert instance

        if is_awaitable(instance):
            instance = await instance

        for k, v in kwargs.items():
            try:
                attributes.set_committed_value(instance, k, v)
            except KeyError:
                setattr(instance, k, v)

        state = attributes.instance_state(instance)
        if state.session_id or state.key:
            return instance

        async with self._session_factory() as session:
            state.session_id = session.sync_session.hash_key

            def _set(sync_session):
                # noinspection PyProtectedMember
                sync_session._register_persistent(state)  # type: ignore

            await session.run_sync(_set)

        return instance

    #
    # Retrieve operations
    #

    async def get(self, id_value: IdType, **kwargs) -> ModelType | None:
        query = self.query_get(id_value, **kwargs)
        async with self._session_factory() as session:
            res = await session.execute(query)
            return res.scalar_one_or_none()

    async def get_any(self, indices: Sequence[IdType], **kwargs) -> Sequence[ModelType | None]:
        query = self.query_any(indices, **kwargs)
        async with self._session_factory() as session:
            res = await session.scalars(query)
            objects = res.all()
        objects = {obj.get_id_value(): obj for obj in objects if obj is not None}
        return [objects[id_value] if id_value in objects else None for id_value in indices]

    async def list(
        self, filters: SqlaFiltersQuery | None = None,
        sorting: SqlaSortingQuery | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ) -> Sequence[ModelType]:
        query = self.query_list(filters, sorting, skip, limit, **kwargs)
        async with self._session_factory() as session:
            res = await session.scalars(query)
            return res.all()

    async def sublist(
        self, field, filters: SqlaFiltersQuery | None = None,
        sorting: SqlaSortingQuery | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ) -> Sequence[EntityType]:
        query = field.select().offset(skip if skip >= 0 else 0)
        if limit > 0:
            query = query.limit(limit)
        if filters:
            query = filters.apply(query)
        if sorting:
            query = sorting.apply(query)
        if options := kwargs.get('options'):
            query = query.options(*options)
        if execution_options := kwargs.get('execution_options'):
            query = query.execution_options(**execution_options)

        async with self._session_factory() as session:
            res = await session.scalars(query)
            return res.all()

    async def count(self, filters: SqlaFiltersQuery | None = None, **kwargs) -> int:
        query = self.query_count(filters, **kwargs)
        async with self._session_factory() as session:
            return await session.scalar(query)

    async def exists(self, id_value: IdType, **kwargs) -> bool:
        query = self.query_exists(id_value, **kwargs)
        async with self._session_factory() as session:
            return bool(await session.scalar(query))

    async def exists_by(self, filters: SqlaFiltersQuery, **kwargs) -> bool:
        query = self.query_exists_by(filters, **kwargs)
        async with self._session_factory() as session:
            return bool(await session.scalar(query))

    async def load(self, instance: ModelType, only: Sequence[str] | None = None) -> bool:
        iss = instance_state(instance)

        if iss.was_deleted or iss.transient:
            return False

        only = set(only) if only else None
        async with self._session_factory() as session:
            await session.refresh(instance, attribute_names=only)
            return True

    #
    # Modification operations
    #

    async def create(self, data: Mapping[str, Any], **kwargs) -> ModelType | None:
        instance = await self.construct(data, **kwargs)
        async with self._session_factory() as session:
            session.add(instance)
            await session.flush(objects=[instance])
        return instance

    async def update_by_id(self, id_value: IdType, data: Mapping[str, Any], **kwargs) -> bool:
        query = self.query_get(id_value, query=update(self.entity_class).values(**data))
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            return cursor.rowcount == 1

    async def update_by(self, filters: SqlaFiltersQuery, data: Mapping[str, Any], **kwargs) -> int:
        query = self.query_update(filters, **kwargs).values(**data)
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            # noinspection PyTypeChecker
            return cursor.rowcount

    async def save(self, instance: ModelType, **kwargs) -> bool:
        iss = instance_state(instance)

        if iss.was_deleted:
            return False

        async with self._session_factory() as session:
            if iss.transient:
                session.add(instance)
            await session.flush(objects=[instance])
            return True

    async def save_all(self, objects: Sequence[ModelType], **kwargs) -> bool:
        async with self._session_factory() as session:
            for obj in objects:
                session.add(obj)

            await session.run_sync(lambda s: s.bulk_save_objects(objects))
            await session.flush(objects=objects)
            return True

    async def delete(self, instance: ModelType) -> bool:
        if instance_state(instance).was_deleted:
            return False

        async with self._session_factory() as session:
            await session.delete(instance)
            await session.flush(objects=[instance])
            return True

    async def delete_all(self, indices: Sequence[IdType] | None = None) -> int:
        if indices is None:
            query = self.query_for_delete()
        else:
            query = self.query_any(indices, query=self.query_for_delete())

        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            # noinspection PyTypeChecker
            return cursor.rowcount

    async def delete_by_id(self, id_value: IdType) -> bool:
        query = self.query_get(id_value, query=self.query_for_delete())
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            return 1 == cursor.rowcount

    async def delete_by(self, filters: SqlaFiltersQuery, **kwargs) -> int:
        query = self.query_delete(filters, **kwargs)
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            # noinspection PyTypeChecker
            return cursor.rowcount

    #
    # Query operations
    #

    def query_for_select(self, **kwargs):
        return select(self.entity_class)

    def query_for_update(self, **kwargs):
        return update(self.entity_class)

    def query_for_delete(self, **kwargs):
        return delete(self.entity_class)

    def query_get(self, id_value: IdType, query=None, **kwargs):
        if not isinstance(id_value, (list, tuple, dict)):
            ident_ = [id_value]
        else:
            ident_ = id_value
        columns = self._get_id_columns()
        if len(ident_) != len(columns):
            raise ValueError(
                f'Incorrect number of values as primary key: expected {len(columns)}, got {len(ident_)}.')

        clause = query if query is not None else self.query_for_select(**kwargs)
        for i, c in enumerate(columns):
            try:
                val = ident_[i]
            except KeyError:
                val = ident_[self._get_field_by_column(c)]
            clause = clause.where(c == val)
        return clause

    def query_any(self, indices: Sequence[IdType], query=None, **kwargs):
        columns = self._get_id_columns()
        clause = query if query is not None else self.query_for_select(**kwargs)
        vals_clause = []

        for ident in indices:
            if not isinstance(ident, (list, tuple, dict)):
                ident_ = [ident]
            else:
                ident_ = ident

            if len(ident_) != len(columns):
                raise ValueError(
                    f'Incorrect number of values as primary key: expected {len(columns)}, got {len(ident_)}.')

            vals = []
            for i, c in enumerate(columns):
                try:
                    val = ident_[i]
                except KeyError:
                    val = ident_[self._get_field_by_column(c)]
                vals.append(val)

            if len(vals) == 1:
                vals_clause.append(vals[0])
            elif len(vals) > 1:
                vals_clause.append((*vals,))

        if len(columns) == 1:
            clause = clause.where(columns[columns.keys()[0]].in_(vals_clause))
        elif len(columns) > 1:
            clause = clause.where(tuple_(*columns).in_(vals_clause))
        return clause

    def query_list(
        self, filters: SqlaFiltersQuery | None = None,
        sorting: SqlaSortingQuery | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ):
        query = self.query_for_select(**kwargs).offset(skip if skip >= 0 else 0)
        if limit > 0:
            query = query.limit(limit)
        if filters:
            query = filters.apply(query)
        if sorting:
            query = sorting.apply(query)
        return query

    def query_count(self, filters: SqlaFiltersQuery | None = None, **kwargs):
        if filters:
            query = filters.apply(self.query_for_select())
        else:
            query = self.entity_class.__table__

        return select(func.count(literal_column('1'))).select_from(query.alias())

    def query_exists(self, id_value: IdType, **kwargs):
        return self.query_get(id_value, query=exists(), **kwargs).select()

    def query_exists_by(self, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(exists(self.entity_class)).select()

    def query_update(self, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(self.query_for_update(**kwargs))

    def query_delete(self, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(self.query_for_delete(**kwargs))


class SqlaModelRepository(
    SqlaRepository[IdType, SqlaModelType],
):
    def __init__(
        self, model_class: Type[SqlaModelType],
        session_factory: AsyncSessionFactory,
        model_factory: SqlaModelTypeFactory | None = None,
    ):
        super().__init__(model_class, session_factory, model_factory)
        model_class.bind(self)
