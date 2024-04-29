from pathlib import Path
from typing import Any, Mapping, cast, override

import pydantic
from pydantic.utils import deep_update

from greyhorse.app.context import AsyncContext, SyncContext
from greyhorse.result import Result
from .parser import DictParser, PydanticParser
from ..abc import SyncRenderFactory, AsyncRenderFactory


class SyncDictLoader:
    def __init__(
        self, root_dir: Path,
        render_ctx: SyncContext[SyncRenderFactory],
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        self._root_dir = root_dir
        self._render_ctx = render_ctx
        self._values = values or {}
        self._default_render_key = default_render_key
        self._parser = DictParser()

    def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[dict]:
        render_key = render_key or self._default_render_key

        with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml(content)

    def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[list[dict]]:
        render_key = render_key or self._default_render_key

        with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml_list(content)

    def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[dict]:
        render_key = render_key or self._default_render_key

        with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_toml(content)


class SyncPydanticLoader[DocumentModel: pydantic.BaseModel](SyncDictLoader):
    def __init__(
        self, doc_schema: type[DocumentModel], root_dir: Path,
        render_ctx: SyncContext[SyncRenderFactory],
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        super().__init__(root_dir, render_ctx, values, default_render_key)
        self._parser = PydanticParser[DocumentModel](doc_schema)

    @override
    def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        return cast(
            Result[DocumentModel],
            super().load_yaml(conf_path, render_key, **kwargs),
        )

    @override
    def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[list[DocumentModel]]:
        return cast(
            Result[list[DocumentModel]],
            super().load_yaml_list(conf_path, render_key, **kwargs),
        )

    @override
    def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        return cast(
            Result[DocumentModel],
            super().load_toml(conf_path, render_key, **kwargs),
        )


class AsyncDictLoader:
    def __init__(
        self, root_dir: Path,
        render_ctx: AsyncContext[AsyncRenderFactory],
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        self._root_dir = root_dir
        self._render_ctx = render_ctx
        self._values = values or {}
        self._default_render_key = default_render_key
        self._parser = DictParser()

    async def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[dict]:
        render_key = render_key or self._default_render_key

        async with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = await render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml(content)

    async def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[list[dict]]:
        render_key = render_key or self._default_render_key

        async with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = await render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_yaml_list(content)

    async def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[dict]:
        render_key = render_key or self._default_render_key

        async with self._render_ctx as factory:
            render = factory(render_key, [conf_path.parent, self._root_dir])
            values = deep_update(kwargs, self._values)
            res = await render(conf_path.name, **values)

        if not res.success:
            return Result.from_errors(res.errors)

        content = res.result
        return self._parser.parse_toml(content)


class AsyncPydanticLoader[DocumentModel: pydantic.BaseModel](AsyncDictLoader):
    def __init__(
        self, doc_schema: type[DocumentModel], root_dir: Path,
        render_ctx: AsyncContext[AsyncRenderFactory],
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ):
        super().__init__(root_dir, render_ctx, values, default_render_key)
        self._parser = PydanticParser[DocumentModel](doc_schema)

    @override
    async def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        return cast(
            Result[DocumentModel],
            await super().load_yaml(conf_path, render_key, **kwargs),
        )

    @override
    async def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[list[DocumentModel]]:
        return cast(
            Result[list[DocumentModel]],
            await super().load_yaml_list(conf_path, render_key, **kwargs),
        )

    @override
    async def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs,
    ) -> Result[DocumentModel]:
        return cast(
            Result[DocumentModel],
            await super().load_toml(conf_path, render_key, **kwargs),
        )
