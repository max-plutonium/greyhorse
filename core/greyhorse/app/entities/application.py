import asyncio
import signal
import threading
from asyncio import get_running_loop
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Collection, Optional, TYPE_CHECKING

from greyhorse.result import Result
from .controller import Controller, ControllerKey
from .module import Module, ModuleErrorsItem, ModuleProviderItem
from .service import Service, ServiceKey
from ..errors import AppNotLoadedError
from ...i18n import tr
from ...logging import logger
from ...utils.invoke import get_asyncio_loop, caller_path

if TYPE_CHECKING:
    from ..schemas.module import ModuleDesc


class Application:
    def __init__(
        self, name: str, version: str = '', debug: bool = False,
    ):
        self._name = name
        self._version = version
        self._debug = debug
        self._path = self._inspect_cwd()
        self._modules: dict[str, tuple[Module, 'ModuleDesc']] = {}
        self._services: dict[str, Service] = {}
        self._root_desc: Optional['ModuleDesc'] = None
        self._module: Module | None = None

    @staticmethod
    def _inspect_cwd():
        import inspect

        for frame in reversed(inspect.stack()):
            path = Path(frame.filename).absolute()

            while path.parent != path:
                path = path.parent
                pyproject_toml_path = path / 'pyproject.toml'
                if pyproject_toml_path.exists():
                    return path

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    @property
    def debug(self) -> bool:
        return self._debug

    def get_cwd(self) -> Path:
        return self._path.absolute()

    def register_module(self, name: str, instance: Module, desc: 'ModuleDesc'):
        self._modules[name] = (instance, desc)

    def unregister_module(self, name: str):
        self._modules.pop(name, None)

    def register_service(self, name: str, instance: Service):
        self._services[name] = instance

    def unregister_service(self, name: str):
        self._services.pop(name, None)

    def get_module(self, name: str) -> Module | None:
        if value := self._modules.get(name):
            return value[0]
        return None

    def get_controller(self, key: ControllerKey, name: str | None = None) -> Controller | None:
        if self._module:
            return self._module.get_controller(key, name=name)
        return None

    def get_service(self, key: ServiceKey, name: str | None = None) -> Service | None:
        if self._module:
            return self._module.get_service(key, name=name)
        return None

    def satisfy_provider_claims(self, items: list[ModuleProviderItem]) -> list[ModuleErrorsItem]:
        if self._module:
            return self._module.satisfy_provider_claims(items)
        raise AppNotLoadedError()

    def create(self) -> list[ModuleErrorsItem]:
        if self._module:
            return self._module.create()
        raise AppNotLoadedError()

    def destroy(self) -> list[ModuleErrorsItem]:
        if self._module:
            return self._module.destroy()
        raise AppNotLoadedError()

    def start(self):
        if self._module:
            return self._module.start()
        raise AppNotLoadedError()

    def stop(self):
        if self._module:
            return self._module.stop()
        raise AppNotLoadedError()

    def load(self, module_path: str, args: dict[str, Any] | None = None) -> Result:
        from ..builders.module import ModuleBuilder
        from ..schemas.module import ModuleDesc

        logger.info(tr('app.application.try-load').format(module_path=module_path))

        root_desc = ModuleDesc(path=module_path, args=args or {})
        root_desc._initpath = caller_path(2)
        builder = ModuleBuilder(self, root_desc)

        res = builder.load_pass()
        if not res.success:
            return res

        self._root_desc = root_desc

        res = builder.create_module_pass()
        if not res.success:
            return res

        self._module = res.result

        logger.info(tr('app.application.load-success').format(module_path=module_path))
        return Result.from_ok()

    def unload(self) -> Result:
        from ..builders.module import ModuleTerminator

        logger.info(tr('app.application.try-unload').format(module_path=self._root_desc.path))

        terminator = ModuleTerminator(self, self._root_desc)

        res = terminator.destroy_module_pass()
        if not res.success:
            return res

        self._module = None

        res = terminator.unload_pass()
        if not res.success:
            return res

        logger.info(tr('app.application.unload-success').format(module_path=self._root_desc.path))
        self._root_desc = None
        return Result.from_ok()

    def run_sync(self, callback: Callable[[], None] | None = None):
        sync_events: list[threading.Event] = []
        async_events: list[asyncio.Event] = []

        for name, srv in self._services.items():
            match srv.wait():
                case threading.Event() as event:
                    sync_events.append(event)
                case asyncio.Event() as event:
                    async_events.append(event)

        all_events = sync_events + async_events

        async def waiter():
            async with asyncio.TaskGroup() as tg:
                for e in async_events:
                    tg.create_task(e.wait())

        logger.info(tr('app.application.run-sync-start').format(name=self.name))

        while not all([e.is_set() for e in all_events]):
            if async_events:
                loop = get_running_loop()
                loop.run_until_complete(waiter())

            sync_events_bools = [e.wait(0.1) for e in sync_events]

            if callback and not all(sync_events_bools):
                callback()

        logger.info(tr('app.application.run-sync-stop').format(name=self.name))

    async def run_async(self):
        sync_events: list[threading.Event] = []
        async_events: list[asyncio.Event] = []

        for name, srv in self._services.items():
            match srv.wait():
                case threading.Event() as event:
                    sync_events.append(event)
                case asyncio.Event() as event:
                    async_events.append(event)

        all_events = sync_events + async_events

        logger.info(tr('app.application.run-async-start').format(name=self.name))

        while not all([e.is_set() for e in all_events]):
            async with asyncio.TaskGroup() as tg:
                for e in sync_events:
                    tg.create_task(asyncio.to_thread(e.wait, 0.1))
                for e in async_events:
                    tg.create_task(e.wait())

        logger.info(tr('app.application.run-async-stop').format(name=self.name))

    @contextmanager
    def graceful_exit(self, signals: Collection[int] = (signal.SIGINT, signal.SIGTERM)):
        signals = set(signals)
        flag: list[bool] = []

        if loop := get_asyncio_loop():
            for sig_num in signals:
                loop.add_signal_handler(sig_num, self._exit_handler, sig_num, flag)
            try:
                yield
            finally:
                for sig_num in signals:
                    loop.remove_signal_handler(sig_num)
        else:
            original_handlers = []

            for sig_num in signals:
                original_handlers.append(signal.getsignal(sig_num))
                signal.signal(sig_num, self._exit_handler)
            try:
                yield
            finally:
                for sig_num, handler in zip(signals, original_handlers):
                    signal.signal(sig_num, handler)

    def _exit_handler(self, sig_num: 'signal.Signals', flag: list[bool], *_) -> None:
        if flag:
            self._second_exit_stage(sig_num)
        else:
            self._first_exit_stage(sig_num)
            flag.append(True)

    def _first_exit_stage(self, sig_num: 'signal.Signals'):
        fail = False

        try:
            self.stop()
        except RuntimeError:
            fail = True

        if fail:
            self._second_exit_stage(sig_num)

    def _second_exit_stage(self, sig_num: 'signal.Signals'):
        raise SystemExit(128 + sig_num)
