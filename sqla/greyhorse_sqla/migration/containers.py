from dependency_injector import containers, providers

from .app import MigrationService
from .operator import MigrationOperator


class MigrationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    migrator_factory = providers.Factory(
        MigrationOperator, dsn=config.migration_dsn,
    )

    service_factory = providers.Factory(
        MigrationService, factory=migrator_factory.provider,
    )
