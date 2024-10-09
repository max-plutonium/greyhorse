import asyncio
import signal
import threading
from asyncio import get_running_loop
from collections.abc import Callable, Collection, Generator
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, NoReturn

from greyhorse.app.abc.controllers import Controller
from greyhorse.app.abc.providers import Provider
from greyhorse.app.abc.services import Service, ServiceWaiter
from greyhorse.app.abc.visitor import Visitor
from greyhorse.app.builders.module import load_module, unload_module
from greyhorse.app.entities.components import ModuleComponent
from greyhorse.app.schemas.components import ModuleComponentConf
from greyhorse.error import Error, ErrorCase
from greyhorse.logging import logger
from greyhorse.maybe import Just, Maybe, Nothing
from greyhorse.result import Ok, Result
from greyhorse.utils.invoke import get_asyncio_loop, invoke_sync
from greyhorse.utils.project import get_project_path, get_version


class ApplicationError(Error):
    namespace = 'greyhorse.app.application'

    AlreadyLoaded = ErrorCase(msg='Application already loaded')
    NotLoaded = ErrorCase(msg='Application not loaded')
    Load = ErrorCase(msg='Load error occurred: "{details}"', details=str)
    Unload = ErrorCase(msg='Unload error occurred: "{details}"', details=str)
    Component = ErrorCase(
        msg='Component error in application, details: "{details}"', details=str
    )


class _ElementsVisitor(Visitor):
    def __init__(self, controllers: list[Controller], services: list[Service]) -> None:
        self._controllers: list[Controller] = controllers
        self._services: list[Service] = services

    def visit_controller(self, controller: Controller) -> None:
        self._controllers.append(controller)

    def visit_service(self, service: Service) -> None:
        self._services.append(service)


class Application:
    def __init__(self, name: str, version: str | None = None, debug: bool = False) -> None:
        self._name = name
        self._debug = debug
        self._path = get_project_path().parent
        self._version = version or get_version()
        self._controllers: list[Controller] = []
        self._services: list[Service] = []
        self._root: Maybe[ModuleComponent] = Nothing
        self._conf: Maybe[ModuleComponentConf] = Nothing

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

    def add_resource(self, res_type: type, resource: Any, name: str | None = None) -> bool:
        return self._root.map_or(
            False, lambda root: root.add_resource(res_type, resource, name)
        )

    def remove_resource(self, res_type: type, name: str | None = None) -> bool:
        return self._root.map_or(False, lambda root: root.remove_resource(res_type, name=name))

    def get_provider[P: Provider](self, prov_type: type[P]) -> Maybe[P]:
        return self._root.and_then(lambda root: root.get_provider(prov_type))

    def load(self, conf: ModuleComponentConf) -> Result[None, ApplicationError]:
        if self._root:
            return ApplicationError.AlreadyLoaded().to_result()

        logger.info('{name}: Application load'.format(name=self.name))

        if not (
            res := load_module(self._name, conf).map_err(
                lambda err: ApplicationError.Load(details=err.message)
            )
        ):
            return res  # type: ignore

        module = res.unwrap()

        try:
            instance = ModuleComponent(
                name=self._name, path=self._name, conf=conf, module=module
            )

        except Exception as e:
            error = ApplicationError.Component(details=str(e))
            logger.error(error.message)
            return error.to_result()

        self._root = Just(instance)
        self._conf = Just(conf)

        logger.info('{name}: Application loaded successfully'.format(name=self.name))
        return Ok()

    def unload(self) -> Result[None, ApplicationError]:
        if not self._root:
            return Ok()

        logger.info('{name}: Application unload'.format(name=self.name))

        conf, self._conf = self._conf.unwrap(), Nothing

        if not (
            res := unload_module(self._name, conf).map_err(
                lambda e: ApplicationError.Unload(details=e.message)
            )
        ):
            return res

        del conf

        logger.info('{name}: Application unloaded successfully'.format(name=self.name))
        return Ok()

    def setup(self) -> Result[None, ApplicationError]:
        return (
            self._root.map(
                lambda root: root.create()
                .and_then(lambda _: root.setup())
                .map_err(lambda e: ApplicationError.Component(details=e.message))
                .map(lambda _: root)
            )
            .unwrap_or_else(lambda: ApplicationError.NotLoaded().to_result())
            .map(self._collect_elements)
        )

    def teardown(self) -> Result[None, ApplicationError]:
        self._controllers = []
        self._services = []

        return self._root.map(
            lambda root: root.teardown()
            .and_then(lambda _: root.destroy())
            .map_err(lambda e: ApplicationError.Component(details=e.message))
        ).unwrap_or_else(lambda: ApplicationError.NotLoaded().to_result())

    def start(self) -> bool:
        if not self._root:
            return False

        for svc in self._services:
            if hasattr(svc, 'start'):
                invoke_sync(svc.start)

        for ctrl in self._controllers:
            if hasattr(ctrl, 'start'):
                invoke_sync(ctrl.start)

        return True

    def stop(self) -> bool:
        if not self._root:
            return False

        for ctrl in self._controllers:
            if hasattr(ctrl, 'stop'):
                invoke_sync(ctrl.stop)

        for svc in self._services:
            if hasattr(svc, 'stop'):
                invoke_sync(svc.stop)

        return True

    def run_visitor(self, visitor: Visitor) -> bool:
        return self._root.map(lambda root: root.accept_visitor(visitor)).map_or(
            False, lambda _: True
        )

    def run_sync(self, callback: Callable[[], None] | None = None) -> None:
        sync_events: list[threading.Event] = []
        async_events: list[asyncio.Event] = []

        for svc in self._services:
            match svc.waiter:
                case ServiceWaiter.Sync() as event:
                    sync_events.append(event._0)  # noqa
                case ServiceWaiter.Async() as event:
                    async_events.append(event._0)  # noqa

        all_events = sync_events + async_events

        async def waiter() -> None:
            async with asyncio.TaskGroup() as tg:
                for e in async_events:
                    tg.create_task(e.wait())

        logger.info('{name}: Application start sync'.format(name=self._name))

        while not all([e.is_set() for e in all_events]):
            if async_events:
                get_running_loop().run_until_complete(waiter())

            sync_events_bools = [e.wait(0.1) for e in sync_events]

            if callback and not all(sync_events_bools):
                callback()

        logger.info('{name}: Application running sync STOPPED'.format(name=self._name))

    async def run_async(self) -> None:
        sync_events: list[threading.Event] = []
        async_events: list[asyncio.Event] = []

        for svc in self._services:
            match svc.waiter:
                case ServiceWaiter.Sync() as event:
                    sync_events.append(event._0)  # noqa
                case ServiceWaiter.Async() as event:
                    async_events.append(event._0)  # noqa

        all_events = sync_events + async_events

        logger.info('{name}: Application start async'.format(name=self._name))

        while not all([e.is_set() for e in all_events]):
            async with asyncio.TaskGroup() as tg:
                for se in sync_events:
                    tg.create_task(asyncio.to_thread(se.wait, 0.1))
                for ae in async_events:
                    tg.create_task(ae.wait())

        logger.info('{name}: Application running async STOPPED'.format(name=self._name))

    @contextmanager
    def graceful_exit(
        self, signals: Collection[int] = (signal.SIGINT, signal.SIGTERM)
    ) -> Generator:
        signals = set(signals)
        flag: list[bool] = []

        if loop := get_asyncio_loop():
            for sig_num in signals:
                loop.add_signal_handler(sig_num, self._exit_handler, sig_num, None, flag)
            try:
                yield
            finally:
                for sig_num in signals:
                    loop.remove_signal_handler(sig_num)
        else:
            original_handlers = []

            for sig_num in signals:
                original_handlers.append(signal.getsignal(sig_num))
                signal.signal(sig_num, partial(self._exit_handler, flag=flag))
            try:
                yield
            finally:
                for sig_num, handler in zip(signals, original_handlers, strict=False):
                    signal.signal(sig_num, handler)

    def _collect_elements(self, root: ModuleComponent) -> None:
        visitor = _ElementsVisitor(self._controllers, self._services)
        root.accept_visitor(visitor)

    def _exit_handler(self, sig_num: 'signal.Signals', _, flag: list[bool]) -> None:
        if flag:
            self._second_exit_stage(sig_num)
        else:
            self._first_exit_stage(sig_num)
            flag.append(True)

    def _first_exit_stage(self, sig_num: 'signal.Signals') -> None:
        fail = False

        try:
            self.stop()
        except RuntimeError:
            fail = True

        if fail:
            self._second_exit_stage(sig_num)

    def _second_exit_stage(self, sig_num: 'signal.Signals') -> NoReturn:
        raise SystemExit(128 + sig_num)
