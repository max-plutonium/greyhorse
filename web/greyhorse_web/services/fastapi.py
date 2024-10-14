from typing import Any, override

import pydantic
from fastapi import APIRouter, FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from greyhorse.app.abc.providers import ForwardProvider
from greyhorse.app.abc.selectors import NamedListSelector
from greyhorse.app.abc.services import ServiceError, ServiceState
from greyhorse.app.boxes import PermanentForwardBox
from greyhorse.app.entities.services import AsyncService, provider
from greyhorse.result import Result
from greyhorse.utils.json import dumps_raw, loads
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
    UnauthenticatedUser,
)
from starlette.middleware.authentication import AuthenticationMiddleware


class ORJsonRequest(Request):
    async def json(self) -> object:
        if not hasattr(self, '_json'):
            body = await self.body()
            self._json = loads(body)
        return self._json


class ORJsonResponse(Response):
    media_type = 'application/json'
    use_indent: bool = False
    sort_keys: bool = False

    def render(self, content: object) -> bytes:
        return dumps_raw(content, use_indent=self.use_indent, sort_keys=self.sort_keys)


class AuthBackend(AuthenticationBackend):
    async def authenticate(self, request: Request) -> tuple[AuthCredentials, BaseUser] | None:
        return AuthCredentials(), UnauthenticatedUser()


class FastAPIService(AsyncService):
    def __init__(
        self,
        title: str,
        debug: bool = False,
        root_path: str = '',
        version: str | None = None,
        cors: list[str] | None = None,
    ) -> None:
        super().__init__()

        self._app = FastAPI(
            title=title,
            version=version,
            debug=debug,
            root_path=root_path,
            default_response_class=ORJsonResponse,
        )
        self._app.add_middleware(
            CORSMiddleware,  # type: ignore
            allow_origins=[str(origin) for origin in cors] if cors else ['*'],
            allow_credentials=True,
            allow_methods=['*'],
            allow_headers=['*'],
        )
        self._app.add_middleware(
            AuthenticationMiddleware,  # type: ignore
            backend=AuthBackend(),
        )

        ORJsonResponse.use_indent = ORJsonResponse.sort_keys = debug
        Request.json = ORJsonRequest.json

        @self._app.exception_handler(RequestValidationError)
        async def validation_exception_handler(
            _: Request, exc: pydantic.ValidationError
        ) -> ORJsonResponse:
            error_dict = {}
            for e in exc.errors():  # type: dict[str, Any]
                location = '.'.join([str(loc) for loc in e['loc'] if loc != 'body'])
                if location in error_dict:
                    error_dict[location] = [
                        error_dict[location],
                        {'msg': e['msg'], 'type': e['type']},
                    ]
                else:
                    error_dict[location] = {'msg': e['msg'], 'type': e['type']}

            return ORJsonResponse(error_dict, status_code=422)

    @override
    async def setup(
        self, list_selector: NamedListSelector[type, Any]
    ) -> Result[ServiceState, ServiceError]:
        for _, _name, route in list_selector.items(lambda t, name: t is APIRouter):
            self._app.include_router(route)
        return await super().setup()

    @provider(ForwardProvider[FastAPI])
    def get_fastapi(self) -> ForwardProvider[FastAPI]:
        return PermanentForwardBox(self._app)
