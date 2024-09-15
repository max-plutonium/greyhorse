from abc import ABC, abstractmethod
from pathlib import Path
from typing import Awaitable

from greyhorse.error import Error, ErrorCase
from greyhorse.result import Result, Ok


class RenderError(Error):
    namespace = 'greyhorse_renders'

    TemplateFileNotFound = ErrorCase(msg='Template not found: "{file}"', file=str)
    TemplateSyntaxError = ErrorCase(
        msg='Template syntax error at "{filename}" line {lineno}: "{details}"',
        filename=str, lineno=int, details=str,
    )


class Render(ABC):
    def __init__(self, templates_dirs: list[Path]):
        self.templates_dirs = templates_dirs

    @abstractmethod
    def __call__(
        self, template: str | Path, **kwargs,
    ) -> Result[str, RenderError] | Awaitable[Result[str, RenderError]]:
        ...

    def eval_string(
        self, source: str, **kwargs,
    ) -> Result[str, RenderError] | Awaitable[Result[str, RenderError]]:
        return Ok(source)


class SyncRender(Render):
    @abstractmethod
    def __call__(self, template: str | Path, **kwargs) -> Result[str, RenderError]:
        ...

    def eval_string(self, source: str, **kwargs) -> Result[str, RenderError]:
        return Ok(source)


class AsyncRender(Render):
    @abstractmethod
    async def __call__(self, template: str | Path, **kwargs) -> Result[str, RenderError]:
        ...

    async def eval_string(self, source: str, **kwargs) -> Result[str, RenderError]:
        return Ok(source)


class SyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> SyncRender:
        ...


class AsyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> AsyncRender:
        ...
