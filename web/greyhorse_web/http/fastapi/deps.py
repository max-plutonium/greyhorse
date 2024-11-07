from collections.abc import AsyncGenerator

from fastapi import Request, WebSocket, params
from greyhorse.app.abc.resources import Lifetime
from greyhorse.app.resources import Container
from greyhorse.maybe import Maybe

from greyhorse_web.schemas import ClientInfo

from .utils import get_client_info


class Provide[T](params.Depends):
    def __init__(self, hint: type[T], optional: bool = False) -> None:
        super().__init__(dependency=self.__call__, use_cache=True)
        self._hint = hint
        self._optional = optional

    async def __call__(self, request: Request) -> Maybe[T] | T:
        value = request.state.container.get(self._hint)
        return value if self._optional else value.expect(f'Cannot unwrap "{self._hint}"')


async def request_container(
    container: Container, request: Request
) -> AsyncGenerator[None, None]:
    context = {Request: request, ClientInfo: get_client_info(request)}
    lifetime = Lifetime.REQUEST()

    with container(context, lifetime) as request_container:
        request.state.container = request_container
        yield


async def websocket_container(
    container: Container, request: WebSocket
) -> AsyncGenerator[None, None]:
    context = {WebSocket: request, ClientInfo: get_client_info(request)}
    lifetime = Lifetime.SESSION()

    with container(context, lifetime) as request_container:
        request.state.container = request_container
        yield
