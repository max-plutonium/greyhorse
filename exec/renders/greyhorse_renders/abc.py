from abc import ABC, abstractmethod
from pathlib import Path

from greyhorse.result import Result


class SyncRender(ABC):
    def __init__(self, templates_dirs: list[Path]):
        self.templates_dirs = templates_dirs

    @abstractmethod
    def __call__(self, template: str | Path, **kwargs) -> Result[str]:
        ...

    def eval_string(self, source: str, **kwargs) -> Result[str]:
        return Result.from_ok(source)


class AsyncRender(ABC):
    def __init__(self, templates_dirs: list[Path]):
        self.templates_dirs = templates_dirs

    @abstractmethod
    async def __call__(self, template: str | Path, **kwargs) -> Result[str]:
        ...

    async def eval_string(self, source: str, **kwargs) -> Result[str]:
        return Result.from_ok(source)


class SyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> SyncRender:
        ...


class AsyncRenderFactory(ABC):
    @abstractmethod
    def __call__(self, name: str, templates_dirs: list[Path]) -> AsyncRender:
        ...
