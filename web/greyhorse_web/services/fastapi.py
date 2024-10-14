from fastapi import FastAPI
from greyhorse.app.abc.providers import SharedProvider
from greyhorse.app.boxes import SharedRefBox
from greyhorse.app.entities.services import AsyncService, provider

from ..factories.fastapi import create_fastapi


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
        self._instance: FastAPI = create_fastapi(title, debug, root_path, version, cors)
        self._app_box = SharedRefBox[FastAPI](lambda: self._instance, lambda v: v)

    @provider(SharedProvider[FastAPI])
    def get_fastapi(self) -> SharedProvider[FastAPI]:
        return self._app_box
