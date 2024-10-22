from abc import ABC, abstractmethod
from collections.abc import Awaitable
from pathlib import Path
from typing import Any

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Ok, Result


class RenderError(Error):
    namespace = 'greyhorse_renders.render'

    TemplateFileNotFound = ErrorCase(msg='Template not found: "{file}"', file=str)
    TemplateSyntaxError = ErrorCase(
        msg='Template syntax error at "{filename}" line {lineno}: "{details}"',
        filename=str,
        lineno=int,
        details=str,
    )


class Render(ABC):
    def __init__(self, templates_dirs: list[Path]) -> None:
        self.templates_dirs = templates_dirs

    @abstractmethod
    def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError] | Awaitable[Result[str, RenderError]]: ...

    def eval_string(
        self, source: str, **kwargs: dict[str, Any]
    ) -> Result[Any, RenderError] | Awaitable[Result[Any, RenderError]]:
        return Ok(None)


class SyncRender(Render):
    @abstractmethod
    def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]: ...

    def eval_string(self, source: str, **kwargs: dict[str, Any]) -> Result[Any, RenderError]:
        return Ok(None)


class AsyncRender(Render):
    @abstractmethod
    async def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]: ...

    async def eval_string(
        self, source: str, **kwargs: dict[str, Any]
    ) -> Result[Any, RenderError]:
        return Ok(None)


class SyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> SyncRender: ...


class AsyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> AsyncRender: ...
