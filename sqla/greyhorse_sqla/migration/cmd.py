from pathlib import Path

import click
from dependency_injector.wiring import Provider

from .containers import AppContainer

migrator_factory = Provider[AppContainer.migration]


@click.group('migration')
@click.argument('directory', type=click.Path(exists=True))
@click.pass_context
def migration(ctx, directory: str):
    migrator = migrator_factory(directory=Path(directory))
    ctx.migrator = migrator


@migration.command()
@click.argument('metadata_package')
@click.argument('metadata_name', default='metadata')
@click.pass_context
def init(ctx, metadata_package: str, metadata_name: str):
    """
    Initialize migration directory
    """
    ctx.parent.migrator.init(metadata_package, metadata_name)


@migration.command()
@click.argument('name')
@click.pass_context
def new(ctx, name: str):
    """
    Generate new revision file
    """
    ctx.parent.migrator.new(name)


@migration.command()
@click.option('--offline', is_flag=True, default=False, help='Only sql output', show_default=True)
@click.pass_context
def up(ctx, offline: bool):
    """
    Upgrade database to head
    """
    ctx.parent.migrator.upgrade(offline)


@migration.command()
@click.option('--offline', is_flag=True, default=False, help='Only sql output', show_default=True)
@click.pass_context
def down(ctx, offline: bool):
    """
    Downgrade database for one step
    """
    ctx.parent.migrator.downgrade(offline)
