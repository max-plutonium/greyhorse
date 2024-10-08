from collections.abc import Callable, Iterable, Mapping
from typing import Any


def dict_values_to_str(data: dict) -> dict:
    result = {}

    for k, v in data.items():
        if isinstance(v, str):
            value = v
        elif isinstance(v, dict):
            value = dict_values_to_str(v)
        elif isinstance(v, list):
            value = [str(i) for i in v]
        else:
            value = str(v)

        result[str(k)] = value

    return result


def build_dict_from_dotted_keys(
    iterable: Iterable, key_getter: Callable[[Any], Any], value_getter: Callable[[Any], Any]
) -> Mapping[str, Any]:
    result = {}

    for obj in iterable:
        keys = key_getter(obj).split('.')
        cur_dict = result

        for key in keys[:-1]:
            if key not in cur_dict:
                cur_dict[key] = {}

            if not isinstance(cur_dict[key], dict):
                cur_dict[key] = {'.': cur_dict[key]}
            cur_dict = cur_dict[key]

        cur_dict[keys[-1]] = value_getter(obj)

    return result


def build_dotted_keys_from_dict(
    dict_: Mapping[str, Any], root_key: str | None = None
) -> Mapping[str, Any]:
    def traverse(key_stack: list[str], values: Mapping[str, Any]) -> Mapping[str, Any]:
        result = {}

        for k, v in values.items():
            if isinstance(v, dict):
                result.update(traverse([*key_stack, k], v))
            elif isinstance(v, list):
                for i in v:
                    res = traverse([*key_stack, k], i)
                    if isinstance(res, dict):
                        result |= res
            else:
                result['.'.join([*key_stack, k])] = v

        return result

    return traverse([root_key] if root_key else [], dict_)


def obj_dict_to_str_dict(data: dict, value_getter: Callable[[Any], Any]) -> Mapping[str, Any]:
    def traverse(values: Mapping[str, Any]) -> Mapping[str, Any]:
        result = {}

        for k, v in values.items():
            if isinstance(v, dict):
                result[k] = traverse(v)
            elif v is None:
                pass
            else:
                result[k] = value_getter(v)

        return result

    return traverse(data)
