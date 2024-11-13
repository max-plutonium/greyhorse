from collections.abc import Awaitable, Callable
from typing import Any, override

from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.resources import Container
from greyhorse.maybe import Nothing
from greyhorse.utils.types import (
    is_awaitable,
    is_maybe,
    is_optional,
    unwrap_maybe,
    unwrap_optional,
)
from strawberry import Info
from strawberry.extensions import FieldExtension, SchemaExtension
from strawberry.types.arguments import StrawberryArgument
from strawberry.types.base import StrawberryOptional
from strawberry.types.field import StrawberryField

from .context import Context


class ContainerExtension(SchemaExtension):
    def resolve(
        self,
        next_: Callable[..., object | Awaitable[object]],
        source: object,
        info: Info[Context],
        *args: object,
        **kwargs: dict[str, Any],
    ) -> object:
        if container := getattr(source, '__container__', None):
            if is_awaitable(next_):
                return self._wrapper(container, next_, source, info, *args, **kwargs)

            with container(lifetime=Lifetime.REQUEST()) as request_container:
                info.context.add_source_container(source, request_container)
                res = next_(source, info, *args, **kwargs)
                info.context.remove_source_container(source, request_container)
        else:
            res = next_(source, info, *args, **kwargs)
        return res

    @staticmethod
    async def _wrapper(
        container: Container,
        next_: Callable[..., Awaitable[object]],
        source: object,
        info: Info[Context],
        *args: object,
        **kwargs: dict[str, Any],
    ) -> object:
        with container(lifetime=Lifetime.REQUEST()) as request_container:
            info.context.add_source_container(source, request_container)
            res = await next_(source, info, *args, **kwargs)
            info.context.remove_source_container(source, request_container)
            return res


class Provide:
    pass


class Depends(FieldExtension):
    __slots__ = ('_args',)

    def __init__(self) -> None:
        self._args: list[StrawberryArgument] = []

    @override
    def apply(self, field: StrawberryField) -> None:
        keep_arguments = []

        for arg in field.arguments:
            if isinstance(arg.default, Provide):
                self._args.append(arg)
                continue
            keep_arguments.append(arg)

        field.arguments = keep_arguments

    @override
    def resolve(
        self,
        next_: Callable[..., Any],
        source: object,
        info: Info[Context],
        *args: object,
        **kwargs: dict[str, Any],
    ) -> Any:
        kw = self._inject_params(source, info, **kwargs)
        return next_(source, info, *args, **kw)

    @override
    async def resolve_async(
        self,
        next_: Callable[..., Any],
        source: object,
        info: Info[Context],
        *args: object,
        **kwargs: dict[str, Any],
    ) -> Any:
        kw = self._inject_params(source, info, **kwargs)
        return await next_(source, info, *args, **kw)

    def _inject_params(
        self, source: object, info: Info[Context], **kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        container = info.context.container_for(source)
        kw = {}

        for arg in self._args:
            if isinstance(arg.type, StrawberryOptional):
                arg_type = arg.type.of_type | None
            else:
                arg_type = arg.type

            if (value := container.get(unwrap_maybe(unwrap_optional(arg_type)))) or (
                value := info.context.get(unwrap_maybe(unwrap_optional(arg_type)))
            ):
                kw[arg.python_name] = value if is_maybe(arg_type) else value.unwrap()
            elif is_maybe(arg_type):
                kw[arg.python_name] = Nothing
            elif is_optional(arg_type):
                kw[arg.python_name] = None
            kw.update(kwargs)

        return kw
