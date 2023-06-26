import click

from greyhorse_core.app.visitors import BindVisitor
from greyhorse_core.utils.imports import import_path
from greyhorse_core.utils.invoke import invoke_sync
from .app import MigrationVisitor


@click.group('migration')
@click.argument('app_path')
@click.argument('migration_name')
@click.pass_context
def migration(ctx, app_path: str, migration_name: str):
    if app := import_path(app_path):
        invoke_sync(app.accept(BindVisitor()))
        ctx.app = app
        ctx.migration_name = migration_name
    else:
        click.echo('No application', err=True, color=True)


@migration.command()
@click.argument('metadata_package')
@click.argument('metadata_name', default='metadata')
@click.pass_context
def init(ctx, metadata_package: str, metadata_name: str):
    """
    Initialize migration directory
    """
    visitor = MigrationVisitor(
        'init', dict(metadata_package=metadata_package, metadata_name=metadata_name),
        only_names=[ctx.parent.migration_name],
    )
    visitor.visit_module(ctx.parent.app)


@migration.command()
@click.argument('name')
@click.pass_context
def new(ctx, name: str):
    """
    Generate new revision file
    """
    visitor = MigrationVisitor(
        'new', dict(name=name),
        only_names=[ctx.parent.migration_name],
    )
    visitor.visit_module(ctx.parent.app)


@migration.command()
@click.option('--offline', is_flag=True, default=False, help='Only sql output', show_default=True)
@click.pass_context
def up(ctx, offline: bool):
    """
    Upgrade database to head
    """
    visitor = MigrationVisitor(
        'upgrade', dict(offline=offline),
        only_names=[ctx.parent.migration_name],
    )
    visitor.visit_module(ctx.parent.app)


@migration.command()
@click.option('--offline', is_flag=True, default=False, help='Only sql output', show_default=True)
@click.pass_context
def down(ctx, offline: bool):
    """
    Downgrade database for one step
    """
    visitor = MigrationVisitor(
        'downgrade', dict(offline=offline),
        only_names=[ctx.parent.migration_name],
    )
    visitor.visit_module(ctx.parent.app)
