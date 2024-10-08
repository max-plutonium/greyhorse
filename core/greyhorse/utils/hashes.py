import hashlib

from orjson import orjson

from greyhorse.utils.dicts import dict_values_to_str


def calculate_digest(data: object, size: int = 0) -> str:
    if isinstance(data, dict):
        dumped = orjson.dumps(dict_values_to_str(data))
    else:
        dumped = str(data).encode('utf-8')

    size = size if 0 < size <= hashlib.blake2b.MAX_DIGEST_SIZE else 4 + int(len(dumped) / 32)
    digest_size = min(hashlib.blake2b.MAX_DIGEST_SIZE, size)
    hash_sum = hashlib.blake2b(dumped, digest_size=digest_size)
    return hash_sum.hexdigest()
