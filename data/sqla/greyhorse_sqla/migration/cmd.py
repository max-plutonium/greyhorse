from typing import Annotated

import typer
from greyhorse.utils.imports import import_path

from greyhorse_sqla.migration.visitor import MigrationVisitor

app = typer.Typer(name='Greyhorse migration command line interface')


@app.callback()
def main(ctx: typer.Context, app_path: Annotated[str, typer.Argument()]) -> None:
    """
    Greyhorse migration command line interface
    """
    for extra_arg in ctx.args:
        print(f'Got extra arg: {extra_arg}')
    if app := import_path(app_path):
        ctx.app = app
    else:
        typer.echo('No application', err=True, color=True)


@app.command()
def init(ctx: typer.Context, only: list[str] | None = None) -> None:
    """
    Initialize migration directory
    """
    visitor = MigrationVisitor('init', only_names=only)
    assert ctx.parent.app.setup()
    ctx.parent.app.run_visitor(visitor)
    assert ctx.parent.app.teardown()


@app.command()
def new(
    ctx: typer.Context,
    name: str,
    only: Annotated[
        list[str] | None, typer.Option(help='Perform operation on this service path')
    ] = None,
) -> None:
    """
    Generate new revision file
    """
    visitor = MigrationVisitor('new', dict(name=name), only_names=only)
    assert ctx.parent.app.setup()
    ctx.parent.app.run_visitor(visitor)
    assert ctx.parent.app.teardown()


@app.command()
def up(
    ctx: typer.Context,
    offline: Annotated[bool, typer.Option(is_flag=True, help='Only sql output')] = False,
    only: Annotated[
        list[str] | None, typer.Option(help='Perform operation on this service path')
    ] = None,
) -> None:
    """
    Upgrade database to head
    """
    visitor = MigrationVisitor('upgrade', dict(offline=offline), only_names=only)
    assert ctx.parent.app.setup()
    ctx.parent.app.run_visitor(visitor)
    assert ctx.parent.app.teardown()


@app.command()
def down(
    ctx: typer.Context,
    offline: Annotated[bool, typer.Option(is_flag=True, help='Only sql output')] = False,
    only: Annotated[
        list[str] | None, typer.Option(help='Perform operation on this service path')
    ] = None,
) -> None:
    """
    Downgrade database for one step
    """
    visitor = MigrationVisitor('downgrade', dict(offline=offline), only_names=only)
    assert ctx.parent.app.setup()
    ctx.parent.app.run_visitor(visitor)
    assert ctx.parent.app.teardown()


if __name__ == '__main__':
    app()
