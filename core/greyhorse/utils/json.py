from typing import Any

from orjson import orjson


def dumps(content: Any, use_indent: bool = False, sort_keys: bool = False, **kwargs) -> bytes:
    option = orjson.OPT_SERIALIZE_UUID
    if use_indent:
        option |= orjson.OPT_INDENT_2
    if sort_keys:
        option |= orjson.OPT_SORT_KEYS
    return orjson.dumps(content, option=option, **kwargs)


def loads(data: bytes | bytearray | memoryview | str) -> Any:
    return orjson.loads(data)
