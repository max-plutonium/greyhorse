from collections.abc import AsyncIterable, Iterable, Mapping
from typing import Any, cast, override

from greyhorse.app.contexts import AsyncMutContext
from greyhorse.data.query import Query
from greyhorse.data.repositories import AsyncMutFilterable, AsyncMutRepository, EntityError
from greyhorse.maybe import Maybe
from greyhorse.result import Ok, Result
from sqlalchemy import (
    Column,
    ColumnCollection,
    CursorResult,
    delete,
    exists,
    func,
    inspect,
    literal_column,
    select,
    tuple_,
    update,
)
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm.base import instance_state

from greyhorse_sqla.contexts import AsyncSession
from greyhorse_sqla.query import SqlaQuery


class AsyncSqlaRepository[E, ID](AsyncMutRepository[E, ID], AsyncMutFilterable[E, ID]):
    def __init__(self, mut_ctx: AsyncMutContext[AsyncSession]) -> None:
        self._mut_ctx = mut_ctx
        self._entity_class = self.wrapped_type[0]

        try:
            column_names_map = inspect(self._entity_class).c
        except NoInspectionAvailable:
            self._column_names_map = dict()
        else:
            column_names_map = zip(
                [column.name for column in column_names_map],
                column_names_map.keys(),
                strict=False,
            )
            self._column_names_map = dict(column_names_map)

    async def construct(self, data: Mapping[str, Any]) -> Result[E, EntityError]:
        return Ok(self._entity_class(**data))

    @override
    @property
    def query_class(self) -> type[Query]:
        return SqlaQuery

    #
    # Retrieve operations
    #

    @override
    async def get(self, id_value: ID) -> Maybe[E]:
        query = self.query_get(id_value)

        async with self._mut_ctx as session:
            res = await session.execute(query)
            return Maybe(res.scalar_one_or_none())

    @override
    async def get_any(self, indices: Iterable[ID]) -> Iterable[Maybe[E]]:
        query = self.query_any(indices)

        async with self._mut_ctx as session:
            res = await session.scalars(query)
            objects = res.all()

        objects = {self._get_id_value(obj): obj for obj in objects if obj is not None}
        return [Maybe(objects.get(id_value, None)) for id_value in indices]

    @override
    async def exists(self, id_value: ID) -> bool:
        query = self.query_exists(id_value)
        async with self._mut_ctx as session:
            return bool(await session.scalar(query))

    @override
    async def load(self, instance: E, only: Iterable[str] | None = None) -> bool:
        iss = instance_state(instance)

        if iss.was_deleted or iss.transient:
            return False

        only = set(only) if only else None
        async with self._mut_ctx as session:
            await session.refresh(instance, attribute_names=only)
            return True

    @override
    async def list(
        self, query: Query | None = None, skip: int = 0, limit: int = 0
    ) -> AsyncIterable[E]:
        query = self.query_list(query, skip, limit)

        async with self._mut_ctx as session:
            for item in await session.scalars(query):
                yield item

    @override
    async def sublist(
        self,
        field: object,
        query: Query | None = None,
        skip: int = 0,
        limit: int = 0,
        **kwargs: dict[str, Any],
    ) -> Iterable[E]:
        sqla_query = field.select().offset(skip if skip >= 0 else 0)
        if limit > 0:
            sqla_query = sqla_query.limit(limit)

        if query is not None:
            sqla_query = query.apply_filter(sqla_query)
            sqla_query = query.apply_sorting(sqla_query)

        if options := kwargs.get('options'):
            sqla_query = sqla_query.options(*options)
        if execution_options := kwargs.get('execution_options'):
            sqla_query = sqla_query.execution_options(**execution_options)

        async with self._mut_ctx as session:
            for item in await session.scalars(sqla_query):
                yield item

    @override
    async def count(self, query: Query | None = None) -> int:
        sqla_query = self.query_count(query)

        async with self._mut_ctx as session:
            return await session.scalar(sqla_query)

    @override
    async def exists_by(self, query: Query) -> bool:
        sqla_query = self.query_exists_by(query)

        async with self._mut_ctx as session:
            return bool(await session.scalar(sqla_query))

    #
    # Modification operations
    #

    @override
    async def create(self, data: Mapping[str, Any]) -> Result[E, EntityError]:
        if not (res := await self.construct(data)):
            return res

        instance = res.unwrap()

        async with self._mut_ctx as session:
            session.add(instance)
            await session.flush(objects=[instance])

        return res

    @override
    async def update_by_id(
        self, id_value: ID, data: Mapping[str, Any]
    ) -> Result[None, EntityError]:
        query = self.query_get(id_value, query=update(self._entity_class).values(**data))

        async with self._mut_ctx as session:
            cursor = cast(CursorResult, await session.execute(query))

        match cursor.rowcount:
            case 1:
                return Ok()
            case 0:
                return EntityError.Empty().to_result()
            case _:
                return EntityError.NotOnlyOne().to_result()

    @override
    async def save(self, instance: E) -> Result[None, EntityError]:
        iss = instance_state(instance)

        if iss.was_deleted:
            return EntityError.Deleted().to_result()

        async with self._mut_ctx as session:
            if iss.transient:
                session.add(instance)
            await session.flush(objects=[instance])

        return Ok()

    @override
    async def save_all(self, objects: Iterable[E]) -> int:
        count = 0

        async with self._mut_ctx as session:
            for obj in objects:
                session.add(obj)
                count += 1

            await session.run_sync(lambda s: s.bulk_save_objects(objects))
            await session.flush(objects=list(objects))

        return count

    @override
    async def delete(self, instance: E) -> bool:
        if instance_state(instance).was_deleted:
            return False

        async with self._mut_ctx as session:
            await session.delete(instance)
            await session.flush(objects=[instance])
            return True

    @override
    async def delete_all(self, indices: Iterable[ID] | None = None) -> int:
        if indices is None:
            query = self.query_for_delete()
        else:
            query = self.query_any(indices, query=self.query_for_delete())

        async with self._mut_ctx as session:
            cursor = cast(CursorResult, await session.execute(query))
            return cursor.rowcount  # type: ignore

    @override
    async def delete_by_id(self, id_value: ID) -> bool:
        query = self.query_get(id_value, query=self.query_for_delete())
        async with self._mut_ctx as session:
            cursor = cast(CursorResult, await session.execute(query))
            return cursor.rowcount == 1

    @override
    async def update_by(self, query: Query, data: Mapping[str, Any]) -> int:
        sqla_query = self.query_update(query).values(**data)

        async with self._mut_ctx as session:
            cursor = cast(CursorResult, await session.execute(sqla_query))
            return cursor.rowcount  # type: ignore

    @override
    async def delete_by(self, query: Query) -> int:
        sqla_query = self.query_delete(query)

        async with self._mut_ctx as session:
            cursor = cast(CursorResult, await session.execute(sqla_query))
            return cursor.rowcount  # type: ignore

    #
    # Query operations
    #

    def query_for_select(self):  # noqa: ANN201
        return select(self._entity_class)

    def query_for_update(self):  # noqa: ANN201
        return update(self._entity_class)

    def query_for_delete(self):  # noqa: ANN201
        return delete(self._entity_class)

    def query_get(self, id_value: ID, query=None):  # noqa: ANN001,ANN201
        ident_ = [id_value] if not isinstance(id_value, list | tuple | dict) else id_value
        columns = self._get_id_columns()
        if len(ident_) != len(columns):
            raise ValueError(
                f'Incorrect number of values as primary key: expected {len(columns)}, '
                f'got {len(ident_)}.'
            )

        clause = query if query is not None else self.query_for_select()
        for i, c in enumerate(columns):
            try:
                val = ident_[i]
            except KeyError:
                val = ident_[self._get_field_by_column(c)]  # type: ignore
            clause = clause.where(c == val)
        return clause

    def query_any(self, indices: Iterable[ID], query=None):  # noqa: ANN001,ANN201
        columns = self._get_id_columns()
        clause = query if query is not None else self.query_for_select()
        vals_clause = []

        for ident in indices:
            ident_ = [ident] if not isinstance(ident, list | tuple | dict) else ident

            if len(ident_) != len(columns):
                raise ValueError(
                    f'Incorrect number of values as primary key: expected {len(columns)}, '
                    f'got {len(ident_)}.'
                )

            vals = []
            for i, c in enumerate(columns):
                try:
                    val = ident_[i]
                except KeyError:
                    val = ident_[self._get_field_by_column(c)]  # type: ignore
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

    def query_exists(self, id_value: ID):  # noqa: ANN201
        return self.query_get(id_value, query=exists()).select()

    def query_list(self, query: Query | None = None, skip: int = 0, limit: int = 0):  # noqa: ANN201
        sqla_query = self.query_for_select().offset(skip if skip >= 0 else 0)
        if limit > 0:
            sqla_query = sqla_query.limit(limit)
        if query is not None:
            sqla_query = query.apply_filter(sqla_query)
            sqla_query = query.apply_sorting(sqla_query)
        return sqla_query

    def query_count(self, query: Query | None = None):  # noqa: ANN201
        if query is not None:
            sqla_query = query.apply_filter(self.query_for_select())
        else:
            sqla_query = self._entity_class.__table__  # type: ignore

        return select(func.count(literal_column('1'))).select_from(sqla_query.alias())

    def query_exists_by(self, query: Query):  # noqa: ANN201
        return query.apply_filter(exists(self._entity_class)).select()

    def query_update(self, query: Query):  # noqa: ANN201
        return query.apply_filter(self.query_for_update())

    def query_delete(self, query: Query):  # noqa: ANN201
        return query.apply_filter(self.query_for_delete())

    #
    # Private
    #

    def _get_id_columns(self) -> ColumnCollection:
        return self._entity_class.__table__.primary_key.columns  # type: ignore

    def _get_field_by_column(self, c: Column) -> str:
        return self._column_names_map.get(c.name)

    def _get_column_values(
        self, obj: E, columns: ColumnCollection, force_tuple: bool = False
    ) -> object | tuple[object]:
        rv = [getattr(obj, self._get_field_by_column(c)) for c in columns]
        return rv[0] if len(rv) == 1 and not force_tuple else tuple(rv)

    def _get_id_value(self, obj: E) -> ID:
        return self._get_column_values(obj, self._entity_class.__table__.primary_key.columns)  # type: ignore
