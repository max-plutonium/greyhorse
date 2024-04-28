from pathlib import Path
from typing import Any, Mapping

import pydantic
from pydantic.utils import deep_update

from greyhorse.app.context import AsyncContext, SyncContext
from greyhorse.result import Result
from .parser import ConfParser
from ..abc import SyncRenderFactory, AsyncRenderFactory


class SyncConfLoader[DocumentModel: pydantic.BaseModel]:
    def __init__(
        self, doc_schema: type[DocumentModel], root_dir: Path,
        render_ctx: SyncContext[SyncRenderFactory],
        global_values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        self._parser = ConfParser[DocumentModel](doc_schema)
        self._root_dir = root_dir
        self._render_ctx = render_ctx
        self._globals = global_values or {}
        self._default_render_key = default_render_key

    def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        render_key = render_key or self._default_render_key

        with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._globals)
            res = render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml(content)

    def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        render_key = render_key or self._default_render_key

        with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._globals)
            res = render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_toml(content)


class AsyncConfLoader[DocumentModel: pydantic.BaseModel]:
    def __init__(
        self, doc_schema: type[DocumentModel], root_dir: Path,
        render_ctx: AsyncContext[AsyncRenderFactory],
        global_values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        self._parser = ConfParser[DocumentModel](doc_schema)
        self._root_dir = root_dir
        self._render_ctx = render_ctx
        self._globals = global_values or {}
        self._default_render_key = default_render_key

    async def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        render_key = render_key or self._default_render_key

        async with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._globals)
            res = await render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml(content)

    async def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        render_key = render_key or self._default_render_key

        async with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._globals)
            res = await render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_toml(content)
