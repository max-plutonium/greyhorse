from functools import partial
from importlib import import_module


def import_path(dotted_path: str):
    if ':' in dotted_path:
        module_path, attr_path = dotted_path.rsplit(':', maxsplit=1)
    else:
        module_path, attr_path = dotted_path.rsplit('.', maxsplit=1)

    module = import_module(module_path)

    if ':' in dotted_path:
        result = module
        for attr_name in attr_path.rsplit('.'):
            result = getattr(result, attr_name)
        return result

    return getattr(module, attr_path)


def lazy_import(dotted_path: str, callable: bool = False, as_partial: bool = False):
    if callable:
        def inner(*args, **kwargs):
            if as_partial:
                return partial(import_path(dotted_path), *args, **kwargs)
            return import_path(dotted_path)(*args, **kwargs)
    else:
        def inner():
            return import_path(dotted_path)
    return inner
