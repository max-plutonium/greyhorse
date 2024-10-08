from collections.abc import Callable
from functools import partial
from importlib import import_module


def import_path(dotted_path: str, package: str | None = None) -> object:
    if ':' in dotted_path:
        module_path, attr_path = dotted_path.rsplit(':', maxsplit=1)
    else:
        module_path, attr_path = dotted_path.rsplit('.', maxsplit=1)

    module = import_module(module_path, package)

    if ':' in dotted_path:
        result = module
        for attr_name in attr_path.rsplit('.'):
            result = getattr(result, attr_name)
        return result

    return getattr(module, attr_path)


def lazy_import(
    dotted_path: str, callable: bool = False, as_partial: bool = False
) -> Callable[[], object]:
    if callable:

        def inner(*args, **kwargs) -> object:  # noqa: ANN002,ANN003
            obj = import_path(dotted_path)
            if as_partial:
                return partial(obj, *args, **kwargs)
            return obj(*args, **kwargs)

    else:

        def inner() -> object:
            return import_path(dotted_path)

    return inner
