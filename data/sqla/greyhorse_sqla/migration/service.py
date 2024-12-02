import os
import sys
from collections.abc import Callable
from functools import partial
from pathlib import Path

from greyhorse.app.entities.services import SyncService
from greyhorse.utils.imports import get_relative_path

from .operator import MigrationOperator

MigratorFactory = Callable[..., MigrationOperator]


class MigrationService(SyncService):
    __slots__ = ('_factory', '_metadata_name', '_metadata_package', '_name')

    def __init__(
        self,
        name: str,
        alembic_path: Path,
        metadata_package: str,
        init_path: list[str],
        metadata_name: str = 'metadata',
        dsn: str | None = None,
        factory: MigratorFactory | None = None,
    ) -> None:
        super().__init__()
        if dsn is None and factory is None:
            raise ValueError('MigrationService: dsn or factory must be not None')
        self._name = name

        alembic_path = Path(alembic_path)

        if not alembic_path.is_absolute():
            init_file_path = Path(sys.modules.get('.'.join(init_path)).__file__)
            alembic_path = Path(os.path.normpath(init_file_path.parent / alembic_path))

        self._metadata_package = get_relative_path(init_path, metadata_package)
        self._metadata_name = metadata_name

        args = {'alembic_path': alembic_path}
        if dsn is not None:
            args['dsn'] = dsn

        if factory is None:
            self._factory = partial(MigrationOperator, **args)
        else:
            self._factory = partial(factory, **args)

    @property
    def name(self) -> str:
        return self._name

    def init(self) -> None:
        migrator = self._factory()
        migrator.init(self._metadata_package, self._metadata_name)

    def new(self, name: str) -> None:
        migrator = self._factory()
        migrator.new(name)

    def upgrade(self, offline: bool = False) -> None:
        migrator = self._factory()
        migrator.upgrade(offline)

    def downgrade(self, offline: bool = False) -> None:
        migrator = self._factory()
        migrator.downgrade(offline)
