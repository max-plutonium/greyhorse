from greyhorse.app.schemas.components import ComponentConf, ModuleConf, ProvidersConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf

from ..common.functional import FunctionalOperator, FunctionalOpProvider
from ..common.resources import (
    DictCtxProvider,
    DictMutCtxProvider,
    DictResContext,
    MutDictResContext,
)
from ..components.functional import DictOperatorCtrl, DictOperatorService
from ..components.resources import DictProviderService


def __init__():
    return ModuleConf(
        enabled=True,
        can_provide=[FunctionalOperator],
        components={
            'domain': ComponentConf(
                enabled=True,
                provider_imports=[
                    ProvidersConf(resource=DictResContext, providers=[DictCtxProvider]),
                    ProvidersConf(resource=MutDictResContext, providers=[DictMutCtxProvider]),
                ],
                services=[SvcConf(type=DictProviderService)],
            ),
            'app': ComponentConf(
                enabled=True,
                provider_grants=[
                    ProvidersConf(resource=DictResContext, providers=[DictCtxProvider]),
                    ProvidersConf(resource=MutDictResContext, providers=[DictMutCtxProvider]),
                ],
                provider_imports=[
                    ProvidersConf(resource=FunctionalOperator, providers=[FunctionalOpProvider])
                ],
                services=[SvcConf(type=DictOperatorService, resources=[DictResContext])],
                controllers=[CtrlConf(type=DictOperatorCtrl)],
            ),
        },
    )
