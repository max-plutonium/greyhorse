from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast, override

import pydantic
from greyhorse.enum import Enum, Struct
from greyhorse.result import Result
from pydantic.utils import deep_update

from ..abc import AsyncRenderFactory, RenderError, SyncRenderFactory
from .parser import DictParser, ParserError, PydanticParser


class LoaderError(Enum):
    Parser = Struct(value=ParserError)
    Render = Struct(value=RenderError)


class SyncDictLoader:
    def __init__(
        self,
        root_dir: Path,
        render_factory: SyncRenderFactory,
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ) -> None:
        self._root_dir = root_dir
        self._render_factory = render_factory
        self._values = values or {}
        self._default_render_key = default_render_key
        self._parser = DictParser()

    def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[dict[str, Any], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            render(conf_path.name, **values)
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_yaml(content).map_err(LoaderError.Parser)  # type: ignore
            )
        )

    def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[list[dict[str, Any]], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            render(conf_path.name, **values)
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_yaml_list(content).map_err(
                    LoaderError.Parser  # type: ignore
                )
            )
        )

    def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[dict[str, Any], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            render(conf_path.name, **values)
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_toml(content).map_err(LoaderError.Parser)  # type: ignore
            )
        )


class SyncPydanticLoader[DocumentModel: pydantic.BaseModel](SyncDictLoader):
    def __init__(
        self,
        doc_schema: type[DocumentModel],
        root_dir: Path,
        render_factory: SyncRenderFactory,
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ) -> None:
        super().__init__(root_dir, render_factory, values, default_render_key)
        self._parser = PydanticParser[DocumentModel](doc_schema)

    @override
    def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[DocumentModel, LoaderError]:
        return cast(
            Result[DocumentModel, LoaderError],
            super().load_yaml(conf_path, render_key, **kwargs),
        )

    @override
    def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[list[DocumentModel], LoaderError]:
        return cast(
            Result[list[DocumentModel], LoaderError],
            super().load_yaml_list(conf_path, render_key, **kwargs),
        )

    @override
    def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[DocumentModel, LoaderError]:
        return cast(
            Result[DocumentModel, LoaderError],
            super().load_toml(conf_path, render_key, **kwargs),
        )


class AsyncDictLoader:
    def __init__(
        self,
        root_dir: Path,
        render_factory: AsyncRenderFactory,
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ) -> None:
        self._root_dir = root_dir
        self._render_factory = render_factory
        self._values = values or {}
        self._default_render_key = default_render_key
        self._parser = DictParser()

    async def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[dict[str, Any], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            (await render(conf_path.name, **values))
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_yaml(content).map_err(LoaderError.Parser)  # type: ignore
            )
        )

    async def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[list[dict[str, Any]], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            (await render(conf_path.name, **values))
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_yaml_list(content).map_err(
                    LoaderError.Parser  # type: ignore
                )
            )
        )

    async def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[dict[str, Any], LoaderError]:
        render_key = render_key or self._default_render_key

        render = self._render_factory(render_key, [conf_path.parent, self._root_dir])
        values = deep_update(kwargs, self._values)

        return (
            (await render(conf_path.name, **values))
            .map_err(LoaderError.Render)  # type: ignore
            .and_then(
                lambda content: self._parser.parse_toml(content).map_err(LoaderError.Parser)  # type: ignore
            )
        )


class AsyncPydanticLoader[DocumentModel: pydantic.BaseModel](AsyncDictLoader):
    def __init__(
        self,
        doc_schema: type[DocumentModel],
        root_dir: Path,
        render_factory: AsyncRenderFactory,
        values: Mapping[str, Any] | None = None,
        default_render_key: str = '',
    ) -> None:
        super().__init__(root_dir, render_factory, values, default_render_key)
        self._parser = PydanticParser[DocumentModel](doc_schema)

    @override
    async def load_yaml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[DocumentModel, LoaderError]:
        return cast(
            Result[DocumentModel, LoaderError],
            await super().load_yaml(conf_path, render_key, **kwargs),
        )

    @override
    async def load_yaml_list(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[list[DocumentModel], LoaderError]:
        return cast(
            Result[list[DocumentModel], LoaderError],
            await super().load_yaml_list(conf_path, render_key, **kwargs),
        )

    @override
    async def load_toml(
        self, conf_path: Path, render_key: str | None = None, **kwargs: dict[str, Any]
    ) -> Result[DocumentModel, LoaderError]:
        return cast(
            Result[DocumentModel, LoaderError],
            await super().load_toml(conf_path, render_key, **kwargs),
        )
