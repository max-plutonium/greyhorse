from contextlib import AbstractContextManager, AbstractAsyncContextManager
from functools import partial
from typing import Callable, Type, Mapping, Any, Sequence, TypeVar, cast

from sqlalchemy import update, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession as SqlaAsyncSession
from sqlalchemy.orm import Session as SqlaSyncSession, attributes
from sqlalchemy.orm.base import instance_state

from greyhorse_core.data.repositories.base import IdType, ModelType, ModelFactory
from greyhorse_core.data.repositories.filterable import FilterableRepository
from greyhorse_core.utils.invoke import is_awaitable
from greyhorse_sqla.model import SqlaModel
from greyhorse_sqla.query import SqlaFiltersQuery, SqlaSortingQuery

SyncSessionFactory = Callable[[], AbstractContextManager[SqlaSyncSession]]
AsyncSessionFactory = Callable[[], AbstractAsyncContextManager[SqlaAsyncSession]]

SqlaModelType = TypeVar('SqlaModelType', bound=SqlaModel, covariant=True)
SqlaModelTypeFactory = Callable[..., SqlaModelType]


class SqlaModelRepository(
    FilterableRepository[IdType, SqlaModelType, SqlaFiltersQuery, SqlaSortingQuery],
):
    def __init__(
        self, model_class: Type[SqlaModelType],
        session_factory: AsyncSessionFactory,
        model_factory: SqlaModelTypeFactory | None = None,
    ):
        super().__init__(model_class, model_factory)
        self._session_factory = session_factory
        self._model_factory = partial(self._construct_instances, self._model_factory)

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
        query = self.model_class.query_get(id_value, **kwargs)
        async with self._session_factory() as session:
            res = await session.execute(query)
            return res.scalar_one_or_none()

    async def get_any(self, indices: Sequence[IdType], **kwargs) -> Sequence[ModelType | None]:
        query = self.model_class.query_any(indices, **kwargs)
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
        query = self.model_class.query_list(filters, sorting, skip, limit, **kwargs)
        async with self._session_factory() as session:
            res = await session.scalars(query)
            return res.all()

    async def count(self, filters: SqlaFiltersQuery | None = None, **kwargs) -> int:
        query = self.model_class.query_count(filters, **kwargs)
        async with self._session_factory() as session:
            return await session.scalar(query)

    async def exists(self, id_value: IdType, **kwargs) -> bool:
        query = self.model_class.query_exists(id_value, **kwargs)
        async with self._session_factory() as session:
            return bool(await session.scalar(query))

    async def exists_by(self, filters: SqlaFiltersQuery, **kwargs) -> bool:
        query = self.model_class.query_exists_by(filters, **kwargs)
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
        instance = await self.model_class.construct(data, **kwargs)
        async with self._session_factory() as session:
            session.add(instance)
            await session.flush(objects=[instance])
        return instance

    async def update_by_id(self, id_value: IdType, data: Mapping[str, Any], **kwargs) -> bool:
        query = self.model_class.query_get(id_value, query=update(self.model_class).values(**data))
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            return cursor.rowcount == 1

    async def update_by(self, filters: SqlaFiltersQuery, data: Mapping[str, Any], **kwargs) -> int:
        query = self.model_class.query_update(filters, **kwargs).values(**data)
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
            query = self.model_class.query_for_delete()
        else:
            query = self.model_class.query_any(indices, query=self.model_class.query_for_delete())

        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            # noinspection PyTypeChecker
            return cursor.rowcount

    async def delete_by_id(self, id_value: IdType) -> bool:
        query = self.model_class.query_get(id_value, query=self.model_class.query_for_delete())
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            return 1 == cursor.rowcount

    async def delete_by(self, filters: SqlaFiltersQuery, **kwargs) -> int:
        query = self.model_class.query_delete(filters, **kwargs)
        async with self._session_factory() as session:
            cursor = cast(CursorResult, await session.execute(query))
            # noinspection PyTypeChecker
            return cursor.rowcount
