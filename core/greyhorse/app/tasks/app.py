from typing import Any

from greyhorse.logging import logger
from greyhorse.utils.imports import import_path
from greyhorse.utils.injectors import ParamsInjector
from greyhorse.utils.invoke import invoke_sync
from greyhorse.utils.project import get_project_path

from ..entities.application import Application


def load_packages(app: Application, key: str, **kwargs: dict[str, Any]) -> None:
    from tomlkit import parse

    packages = {}
    injector = ParamsInjector()
    pyproject_toml_path = get_project_path()
    pyproject_toml = parse(string=pyproject_toml_path.read_text())

    if project := pyproject_toml.get('project'):
        if key:
            if section := project.get(key):
                packages = section.get('packages', dict())
        else:
            packages = project.get('packages', dict())

    key = key or 'package'

    for name, dotted_path in packages.items():
        logger.info(f'Import package: "{name}"')
        dotted_path = dotted_path if ':' in dotted_path else f'{dotted_path}:{key}_init'

        if entrypoint := import_path(dotted_path):
            if not callable(entrypoint):
                continue
            logger.info(f'Application "{app.name}": load package "{name}"')
            injected_args = injector(entrypoint, values={'app': app, **kwargs})
            invoke_sync(entrypoint, *injected_args.args, **injected_args.kwargs)
