from pathlib import Path
from typing import Callable, Mapping, Any

from greyhorse_core.app import base
from greyhorse_core.app.service import Service
from .operator import MigrationOperator

MigratorFactory = Callable[..., MigrationOperator]


class MigrationVisitor(base.Visitor):
    def __init__(
        self, operation: str, args: Mapping[str, Any],
        only_names: list[str] = None,
    ):
        self._operation = operation
        self._args = args
        self._only_names = set(only_names)
        self._dotted_path = list()

    def visit_service(self, instance: Service):
        if not isinstance(instance, MigrationService):
            return

        name = '.'.join(self._dotted_path + [instance.name])

        if self._only_names is None or name in self._only_names:
            if method := getattr(instance, self._operation, None):
                method(**self._args)

    def visit_module(self, instance: base.Module):
        self._dotted_path.append(instance.name)

        for s in instance.services:
            s.accept(self)

        for m in instance.modules:
            self._dotted_path.append(m.name)
            m.accept(self)
            self._dotted_path.pop()

        self._dotted_path.pop()


class MigrationService(Service):
    def __init__(self, name: str, alembic_path: Path, factory: MigratorFactory):
        super().__init__()
        self._name = name
        self._alembic_path = alembic_path.resolve()
        self._factory = factory

    @property
    def name(self) -> str:
        return self._name

    def start(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass

    def init(self, metadata_package: str, metadata_name: str = 'metadata'):
        migrator = self._factory(alembic_path=self._alembic_path)
        migrator.init(metadata_package, metadata_name)

    def new(self, name: str):
        migrator = self._factory(alembic_path=self._alembic_path)
        migrator.new(name)

    def upgrade(self, offline: bool = False):
        migrator = self._factory(alembic_path=self._alembic_path)
        migrator.upgrade(offline)

    def downgrade(self, offline: bool = False):
        migrator = self._factory(alembic_path=self._alembic_path)
        migrator.downgrade(offline)
