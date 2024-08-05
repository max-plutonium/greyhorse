from typing import Any

from greyhorse.app.abc.providers import SharedProvider, MutProvider
from greyhorse.app.context import SyncContext, SyncMutContext

DictResource = dict[str, Any]
DictResContext = SyncContext[DictResource]
MutDictResContext = SyncMutContext[DictResource]

DictCtxProvider = SharedProvider[DictResContext]
DictMutCtxProvider = MutProvider[MutDictResContext]
