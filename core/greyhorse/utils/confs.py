import os
from collections.abc import Callable, Mapping


def default_value(type_: type) -> Callable[[object, object], object]:
    def getter(value: object, default: object) -> object:
        return type_(value) if value is not None else default

    return getter


def expandvars_dict(data: Mapping[str, str]) -> Mapping[str, str]:
    """Expands all environment variables in a dictionary."""
    return dict((k, os.path.expandvars(v)) for k, v in data.items())
