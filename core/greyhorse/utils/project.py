import importlib.metadata
import inspect
from pathlib import Path


def get_project_path() -> Path:
    for frame in reversed(inspect.stack()):
        path = Path(frame.filename).absolute()

        while path.parent != path:
            path = path.parent
            pyproject_toml_path = path / 'pyproject.toml'
            if pyproject_toml_path.exists():
                return pyproject_toml_path

    raise AssertionError('Could not find pyproject.toml')


def get_version() -> str:
    from tomlkit import parse

    pyproject_toml_path = get_project_path()

    with pyproject_toml_path.open('r') as f:
        pyproject_toml = parse(string=f.read())

    project = pyproject_toml['project']
    return importlib.metadata.version(project['name'])
