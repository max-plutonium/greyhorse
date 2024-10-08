import inspect
from collections.abc import Callable, Mapping
from typing import Any

from greyhorse.maybe import Maybe

TypeProviderFactory = Callable[[str, ...], Any]


class ParamsInjector:
    def __init__(self, type_providers: TypeProviderFactory | None = None) -> None:
        self._types_providers: dict[type, TypeProviderFactory | Any] = type_providers or {}

    def get_type_provider(self, t: type) -> Maybe[TypeProviderFactory | object]:
        return Maybe(self._types_providers.get(t))

    def add_type_provider(self, t: type, p: TypeProviderFactory | object) -> None:
        self._types_providers[t] = p

    def remove_type_provider(self, t: type) -> None:
        self._types_providers.pop(t, None)

    def __call__(
        self,
        func: Callable[[...], ...],
        values: Mapping[str, Any] | None = None,
        types: Mapping[type, Any] | None = None,
    ) -> inspect.BoundArguments:
        values = values or {}
        types = types or {}

        sig = inspect.signature(func, eval_str=True)
        args = {}

        for k, v in sig.parameters.items():
            if k == 'values':
                args[k] = values
            elif v.annotation in types:
                args[k] = types[v.annotation]
            elif k in values:
                args[k] = values[k]
            elif v.annotation in self._types_providers:
                args[k] = self._types_providers[v.annotation]

        args = sig.bind_partial(**args)
        args.apply_defaults()
        return args
