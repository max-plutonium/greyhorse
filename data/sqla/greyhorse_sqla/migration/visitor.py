from collections.abc import Mapping
from typing import Any

from greyhorse.app.abc.services import Service
from greyhorse.app.abc.visitor import Visitor
from greyhorse.app.entities.module import Module

from .service import MigrationService


class MigrationVisitor(Visitor):
    def __init__(
        self,
        operation: str,
        args: Mapping[str, Any] | None = None,
        only_names: list[str] | None = None,
    ) -> None:
        self._operation = operation
        self._args = args or {}
        self._only_names = set(only_names) if only_names else None
        self._module_paths = list()

    def visit_service(self, instance: Service) -> None:
        if not isinstance(instance, MigrationService):
            return

        name = '.'.join([self._module_paths[-1], instance.name])

        if self._only_names is None or name in self._only_names:  # noqa: SIM102
            if method := getattr(instance, self._operation, None):
                method(**self._args)

    def start_module(self, instance: Module) -> None:
        self._module_paths.append(instance.path)

    def finish_module(self, instance: Module) -> None:
        self._module_paths.pop()
