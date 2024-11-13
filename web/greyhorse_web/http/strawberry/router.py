from typing import override

from fastapi import HTTPException
from greyhorse.utils import json
from orjson import orjson
from strawberry.fastapi import GraphQLRouter
from strawberry.http import GraphQLHTTPResponse


class JsonGraphQLRouter(GraphQLRouter):
    use_indent: bool = False
    sort_keys: bool = False

    @override
    def parse_json(self, data: str | bytes) -> object:
        try:
            return json.loads(data)
        except orjson.JSONDecodeError as e:
            raise HTTPException(400, 'Unable to parse request body as JSON') from e

    @override
    def encode_json(self, data: GraphQLHTTPResponse) -> str:
        try:
            return json.dumps(data)
        except orjson.JSONEncodeError as e:
            raise HTTPException(400, 'Unable to encode response body as JSON') from e
