import decimal
from collections.abc import Callable
from typing import Any

from orjson import orjson


def stringify(obj: object) -> str:
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    raise TypeError


def dumps_raw(
    content: object,
    use_indent: bool = False,
    sort_keys: bool = False,
    stringify_fn: Callable[[Any], str] | None = None,
    **kwargs: dict[str, Any],
) -> bytes:
    option = orjson.OPT_SERIALIZE_UUID
    if use_indent:
        option |= orjson.OPT_INDENT_2
    if sort_keys:
        option |= orjson.OPT_SORT_KEYS
    return orjson.dumps(content, option=option, default=stringify_fn or stringify, **kwargs)


def dumps(
    content: object,
    use_indent: bool = False,
    sort_keys: bool = False,
    stringify_fn: Callable[[Any], str] | None = None,
    **kwargs: dict[str, Any],
) -> str:
    return dumps_raw(content, use_indent, sort_keys, stringify_fn, **kwargs).decode('utf-8')


def loads(data: bytes | bytearray | memoryview | str) -> object:
    return orjson.loads(data)
