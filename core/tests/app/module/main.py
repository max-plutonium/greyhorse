from greyhorse.app.schemas.components import ComponentConf, ModuleConf
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


def __init__() -> ModuleConf:  # noqa: N807
    return ModuleConf(
        enabled=True,
        can_provide=[FunctionalOperator],
        components={
            'domain': ComponentConf(
                enabled=True,
                providers=[DictCtxProvider, DictMutCtxProvider],
                services=[SvcConf(type=DictProviderService)],
            ),
            'app': ComponentConf(
                enabled=True,
                providers=[FunctionalOpProvider],
                operator_imports=[DictResContext, MutDictResContext],
                services=[
                    SvcConf(
                        type=DictOperatorService, resources=[DictResContext, MutDictResContext]
                    )
                ],
                controllers=[CtrlConf(type=DictOperatorCtrl)],
            ),
        },
    )
