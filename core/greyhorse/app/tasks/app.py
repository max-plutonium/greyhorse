from ...logging import logger
from ...utils.imports import import_path
from ...utils.injectors import ParamsInjector
from ...utils.invoke import invoke_sync
from ..entities.application import Application


def load_packages(app: Application, key: str, **kwargs) -> None:
    from tomlkit import parse

    packages = {}
    injector = ParamsInjector()
    pyproject_toml_path = app.get_cwd() / 'pyproject.toml'

    if pyproject_toml_path.exists():
        with open(str(pyproject_toml_path)) as f:
            pyproject_toml = parse(string=f.read())

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
            logger.info(f'Application "{app.name}": load package "{name}"')
            injected_args = injector(entrypoint, values={'app': app, **kwargs})
            invoke_sync(entrypoint, *injected_args.args, **injected_args.kwargs)
