from typing import override

from greyhorse.app.abc.providers import FactoryProvider, FactoryError
from greyhorse.app.abc.services import ProvisionError
from greyhorse.app.entities.controllers import SyncController
from greyhorse.app.entities.services import SyncService, provider
from greyhorse.maybe import Maybe
from greyhorse.result import Result, Ok, Err, do
from ..common.functional import FunctionalOperator, FunctionalOpProvider
from ..common.resources import DictResContext, MutDictResContext, DictCtxProvider, DictMutCtxProvider


class FunctionalOperatorImpl(FunctionalOperator):
    def __init__(self, ctx: DictResContext, mut_ctx: MutDictResContext):
        self.ctx = ctx
        self.mut_ctx = mut_ctx

    @override
    def add_number(self, value: int) -> Result[None, str]:
        with self.mut_ctx as ctx:
            ctx['number'] = value
            self.mut_ctx.apply()

        return Ok(None)

    @override
    def get_number(self) -> Result[int, str]:
        with self.ctx as ctx:
            value = Maybe(ctx.get('number'))

        return value.ok_or('Number is not initialized')

    @override
    def remove_number(self) -> Result[bool, str]:
        with self.mut_ctx as ctx:
            value = Maybe(ctx.pop('number', None))
            self.mut_ctx.apply()

        return value.ok_or('Number is not initialized').map(lambda _: True)


class FunctionalOpProviderImpl(FactoryProvider[FunctionalOperator]):
    def __init__(self, ctx_prov: DictCtxProvider, mut_ctx_prov: DictMutCtxProvider):
        self._ctx_prov = ctx_prov
        self._mut_ctx_prov = mut_ctx_prov

    @override
    def create(self) -> Result[FunctionalOperator, FactoryError]:
        result: Result[tuple[DictResContext, MutDictResContext], str] = do(
            Ok((c1, c2))
            for c1 in self._ctx_prov.borrow()
            for c2 in self._mut_ctx_prov.acquire()
        )

        match result:
            case Ok((ctx, mut_ctx)):
                return Ok(FunctionalOperatorImpl(ctx, mut_ctx))
            case Err(e):
                return FactoryError.Internal(
                    name='FunctionalOperator', details=e,
                ).to_result()

        return FactoryError.Internal(
            name='FunctionalOperator', details='Unexpected return',
        ).to_result()

    @override
    def destroy(self, instance: FunctionalOperatorImpl):
        self._mut_ctx_prov.release(instance.mut_ctx)
        self._ctx_prov.reclaim(instance.ctx)
        del instance


class DictOperatorCtrl(SyncController):
    def __init__(self, ctx_prov: DictCtxProvider, mut_ctx_prov: DictMutCtxProvider):
        self._provider = FunctionalOpProviderImpl(ctx_prov, mut_ctx_prov)

    def get_provider(self):
        return self._provider


class DictOperatorService(SyncService):
    def __init__(self, ctx_prov: DictCtxProvider, mut_ctx_prov: DictMutCtxProvider):
        super().__init__()
        self._provider = FunctionalOpProviderImpl(ctx_prov, mut_ctx_prov)

    @provider(FunctionalOpProvider)
    def create_op(self) -> Result[FunctionalOpProvider, ProvisionError]:
        return Ok(self._provider)
