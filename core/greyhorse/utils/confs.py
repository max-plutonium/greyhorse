import os
from typing import Any, Mapping


def default_value(type_: type):
    def getter(value: Any, default: Any):
        return type_(value) if value is not None else default
    return getter


def expandvars_dict(data: Mapping[str, str]) -> Mapping[str, str]:
    """Expands all environment variables in a dictionary."""
    return dict((k, os.path.expandvars(v)) for k, v in data.items())
