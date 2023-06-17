from dependency_injector import containers, providers

from .operator import MigrationOperator


class AppContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    migration = providers.Factory(
        MigrationOperator, dsn=config.migration_dsn,
    )

    wiring_config = containers.WiringConfiguration(
        modules=['.cmd'],
    )
