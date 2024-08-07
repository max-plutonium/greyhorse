from greyhorse.app.schemas.components import ProvidersConf, ComponentConf, ModuleConf
from greyhorse.app.schemas.elements import CtrlConf, SvcConf

from ..common.functional import DictCtxOperator, DictMutCtxOperator, FunctionalOpProvider, FunctionalOperator
from ..common.resources import DictCtxProvider, DictMutCtxProvider, DictResContext, MutDictResContext
from ..components.functional import DictOperatorCtrl, DictOperatorService
from ..components.resources import DictResourceCtrl, DictProviderService


def __init__():
    return ModuleConf(
        enabled=True,
        provider_exports=[
            ProvidersConf(
                resource=FunctionalOperator,
                types=[FunctionalOpProvider],
            ),
        ],
        components=[
            ComponentConf(
                name='domain',
                enabled=True,
                provider_imports=[
                    ProvidersConf(
                        resource=DictResContext,
                        types=[DictCtxProvider],
                    ),
                    ProvidersConf(
                        resource=MutDictResContext,
                        types=[DictMutCtxProvider],
                    ),
                ],
                controllers=[
                    CtrlConf(
                        type=DictResourceCtrl,
                        operators=[],
                    )
                ],
                services=[
                    SvcConf(
                        type=DictProviderService,
                        providers=[DictCtxProvider, DictMutCtxProvider],
                    ),
                ],
            ),
            ComponentConf(
                name='app',
                enabled=True,
                provider_grants=[
                    ProvidersConf(
                        resource=DictResContext,
                        types=[DictCtxProvider],
                    ),
                    ProvidersConf(
                        resource=MutDictResContext,
                        types=[DictMutCtxProvider],
                    ),
                ],
                provider_imports=[
                    ProvidersConf(
                        resource=FunctionalOperator,
                        types=[FunctionalOpProvider],
                    ),
                ],
                controllers=[
                    CtrlConf(
                        type=DictOperatorCtrl,
                        operators=[
                            DictCtxOperator, DictMutCtxOperator,
                        ],
                    )
                ],
                services=[
                    SvcConf(
                        type=DictOperatorService,
                        providers=[FunctionalOpProvider],
                    ),
                ],
            ),
        ],
    )
