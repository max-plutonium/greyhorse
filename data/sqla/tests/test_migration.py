import pytest
from greyhorse.app.entities.application import Application
from greyhorse.app.schemas.components import ModuleComponentConf, ModuleConf
from greyhorse_sqla.migration.visitor import MigrationVisitor

from .conf import POSTGRES_URI


@pytest.fixture
def application() -> Application:
    app_conf = ModuleConf(
        enabled=True,
        components={
            'submodule': ModuleComponentConf(
                enabled=True, path='..migration.module', args={'dsn': POSTGRES_URI}
            )
        },
    )

    app = Application('TestApp')

    assert app.load(app_conf)
    assert app.setup()

    yield app

    assert app.teardown()
    assert app.unload()


def test_init(application: Application) -> None:
    visitor = MigrationVisitor('init', only_names=['TestApp.submodule.migration'])
    assert application.run_visitor(visitor)


def test_new(application: Application) -> None:
    visitor = MigrationVisitor(
        'new', dict(name='initial'), only_names=['TestApp.submodule.migration']
    )
    assert application.run_visitor(visitor)


def test_upgrade(application: Application) -> None:
    visitor = MigrationVisitor(
        'upgrade', dict(offline=False), only_names=['TestApp.submodule.migration']
    )
    assert application.run_visitor(visitor)


def test_downgrade(application: Application) -> None:
    visitor = MigrationVisitor(
        'downgrade', dict(offline=False), only_names=['TestApp.submodule.migration']
    )
    assert application.run_visitor(visitor)
