from greyhorse.app.schemas.components import ComponentConf, ModuleConf
from greyhorse.app.schemas.elements import SvcConf
from greyhorse_sqla.migration.service import MigrationService


def __init__(dsn: str) -> ModuleConf:  # noqa: N807
    return ModuleConf(
        enabled=True,
        components={
            'db': ComponentConf(
                enabled=True,
                services=[
                    SvcConf(
                        type=MigrationService,
                        name='migration',
                        args={
                            'dsn': dsn,
                            'alembic_path': './alembic',
                            'metadata_package': '..tables',
                            'metadata_name': 'metadata',
                        },
                    )
                ],
            )
        },
    )
