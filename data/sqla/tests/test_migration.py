import pytest
from greyhorse.app.entities.application import Application
from greyhorse.app.schemas.components import ModuleComponentConf
from greyhorse_sqla.migration.visitor import MigrationVisitor

from .conf import POSTGRES_URI


@pytest.fixture
def application():
    app_conf = ModuleComponentConf(
        enabled=True, path='..migration.module', args={'dsn': POSTGRES_URI}
    )

    app = Application('TestApp')

    assert app.load(app_conf)
    assert app.setup()

    yield app

    assert app.teardown()
    assert app.unload()


def test_init(application) -> None:
    visitor = MigrationVisitor('init', only_names=['TestApp.migration'])
    assert application.run_visitor(visitor)


def test_new(application) -> None:
    visitor = MigrationVisitor('new', dict(name='initial'), only_names=['TestApp.migration'])
    assert application.run_visitor(visitor)


def test_upgrade(application) -> None:
    visitor = MigrationVisitor('upgrade', dict(offline=False), only_names=['TestApp.migration'])
    assert application.run_visitor(visitor)


def test_downgrade(application) -> None:
    visitor = MigrationVisitor(
        'downgrade', dict(offline=False), only_names=['TestApp.migration']
    )
    assert application.run_visitor(visitor)
