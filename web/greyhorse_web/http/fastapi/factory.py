import asyncio
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial

import pydantic
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from greyhorse.app.entities.application import Application
from greyhorse.app.runtime import Runtime
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
    async def authenticate(self, _: Request) -> tuple[AuthCredentials, BaseUser] | None:
        return AuthCredentials(), UnauthenticatedUser()


@asynccontextmanager
async def fastapi_lifespan(_: FastAPI, app: Application) -> AbstractAsyncContextManager:
    runtime = Runtime()
    asyncio.set_event_loop(runtime.loop)

    with runtime:
        app.setup().unwrap()
        app.start()

        yield

        app.stop()
        app.teardown().unwrap()
        app.unload().unwrap()


def create_fastapi(
    title: str,
    debug: bool = False,
    root_path: str = '',
    version: str | None = None,
    cors: list[str] | None = None,
    application: Application | None = None,
) -> FastAPI:
    app = FastAPI(
        title=title,
        version=version,
        debug=debug,
        root_path=root_path,
        lifespan=partial(fastapi_lifespan, app=application) if application else None,
        default_response_class=ORJsonResponse,
    )

    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=[str(origin) for origin in cors] if cors else ['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    app.add_middleware(
        AuthenticationMiddleware,  # type: ignore
        backend=AuthBackend(),
    )

    ORJsonResponse.use_indent = ORJsonResponse.sort_keys = debug
    Request.json = ORJsonRequest.json

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: pydantic.ValidationError
    ) -> ORJsonResponse:
        error_dict = {}
        for e in exc.errors():  # type: dict[str, str]
            location = '.'.join([str(loc) for loc in e['loc'] if loc != 'body'])
            if location in error_dict:
                error_dict[location] = [
                    error_dict[location],
                    {'msg': e['msg'], 'type': e['type']},
                ]
            else:
                error_dict[location] = {'msg': e['msg'], 'type': e['type']}

        return ORJsonResponse(error_dict, status_code=422)

    return app
