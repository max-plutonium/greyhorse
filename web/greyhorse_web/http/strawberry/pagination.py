import base64
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, NewType

import strawberry
from greyhorse.data.query import Query
from greyhorse.data.repositories import AsyncFilterable
from pydantic import BaseModel, Field, model_validator
from strawberry import scalar
from strawberry.types import Info
from strawberry.types.nodes import Selection

from .context import Context
from .mixins import FromEntityMixin

Encoded = scalar(
    NewType('Encoded', bytes),
    description=('Represents encoded cursor data'),
    serialize=lambda v: base64.b85encode(v).decode('latin1'),
    parse_value=lambda v: base64.b85decode(v.encode('latin1')),
)


@strawberry.type
class PageInfo:
    has_next: bool
    has_prev: bool
    count: int
    total: int
    page: int
    page_size: int
    total_pages: int
    start_cursor: Encoded | None
    end_cursor: Encoded | None


@strawberry.type
class Edge[T]:
    node: T
    cursor: Encoded


@strawberry.type
class Connection[T]:
    page_info: PageInfo
    edges: list[Edge[T]]
    nodes: list[T]


DEFAULT_LIMIT_VALUE = 10
MAX_LIMIT_VALUE = 1000


def cursor_encode(ident: object) -> str:
    return base64.b85encode(str(ident).encode('latin1')).decode('latin1')


def cursor_decode(code: str) -> str:
    return base64.b85decode(code.encode('latin1')).decode('latin1')


@dataclass(slots=True, frozen=True)
class NeedFieldData:
    need_has_next: bool
    need_has_prev: bool
    need_total: bool
    need_page: bool


class RelayCursorInfo(BaseModel, frozen=True):
    count: int | None = Field(gt=0, le=MAX_LIMIT_VALUE, default=DEFAULT_LIMIT_VALUE)
    after: bytes | None = None
    before: bytes | None = None

    @model_validator(mode='before')
    @classmethod
    def check(cls, values: dict[str, Any]) -> dict[str, Any]:
        if 'after' in values and 'before' in values:
            raise ValueError('You can specify only "after" or "before"')
        return values

    @classmethod
    def get(
        cls,
        count: int | None = None,
        after: Encoded | None = None,
        before: Encoded | None = None,
    ) -> 'RelayCursorInfo':
        data = {}
        if count is not None:
            data['count'] = count
        if after is not None:
            data['after'] = after
        if before is not None:
            data['before'] = before
        return cls(**data)

    def decoded_after(
        self, as_: Callable[[str], Any] | None = None, default: object | None = None
    ) -> object | None:
        if self.after is None:
            return default
        res = self.after.decode('latin1')
        if as_:
            return as_(res)
        return res

    def decoded_before(
        self, as_: Callable[[str], Any] | None = None, default: object | None = None
    ) -> object | None:
        if self.before is None:
            return default
        res = self.before.decode('latin1')
        if as_:
            return as_(res)
        return res

    @staticmethod
    def encode_cursor(value: object) -> bytes:
        return str(value).encode('latin1')

    @staticmethod
    def need_has_fields(info: Info[Context]) -> NeedFieldData:
        need_has_next = need_has_prev = need_total = need_page = False

        def traverse(selection: Selection) -> bool:
            nonlocal need_has_next, need_has_prev, need_total, need_page

            if selection.name == 'pageInfo':
                for subfield in selection.selections:
                    if subfield.name == 'hasNext':
                        need_has_next = True
                    elif subfield.name == 'hasPrev':
                        need_has_prev = True
                    elif subfield.name == 'total':
                        need_total = True
                    elif subfield.name == 'page':
                        need_page = True
                return True

            return any(traverse(subfield) for subfield in selection.selections)

        for field in info.selected_fields:
            if traverse(field):
                break

        return NeedFieldData(
            need_has_next=need_has_next,
            need_has_prev=need_has_prev,
            need_total=need_total,
            need_page=need_page,
        )


class AsyncPaginator[E, ID]:
    def __init__(
        self,
        out_model: type[FromEntityMixin],
        after_filter: Callable[[ID], Any],
        before_filter: Callable[[ID], Any],
        asc_sorting: Callable[[], Any],
        desc_sorting: Callable[[], Any],
        id_getter: Callable[[E], ID],
        data_sorting: Callable[[E], Any] | None = None,
        str_to_id: Callable[[str], ID] = int,
    ) -> None:
        self._out_model = out_model
        self._after_filter = after_filter
        self._before_filter = before_filter
        self._asc_sorting = asc_sorting
        self._desc_sorting = desc_sorting
        self._id_getter = id_getter
        self._data_sorting = data_sorting
        self._str_to_id = str_to_id

    async def __call__(
        self,
        repo: AsyncFilterable[E, ID],
        info: Info[Context],
        query: Query,
        count: int | None = None,
        after: Encoded | None = None,
        before: Encoded | None = None,
        field: object | None = None,
        **query_options: dict[str, Any],
    ) -> Connection:
        cur_info = RelayCursorInfo.get(count, after, before)

        need_data = RelayCursorInfo.need_has_fields(info)
        total = await repo.count(query) if need_data.need_total else 0

        if after:
            after_id = cur_info.decoded_after(as_=self._str_to_id)
            list_query = query.add_filter(self._after_filter(after_id)).add_sorting(
                self._asc_sorting
            )
        elif before:
            before_id = cur_info.decoded_before(as_=self._str_to_id)
            list_query = query.add_filter(self._before_filter(before_id)).add_sorting(
                self._desc_sorting
            )
        else:
            list_query = query.clone()

        if field is None:
            objects = [obj async for obj in repo.list(list_query, limit=cur_info.count)]
        else:
            objects = [
                obj
                async for obj in repo.sublist(
                    field, list_query, limit=cur_info.count, **query_options
                )
            ]

        has_prev = has_next = False
        count_prev = 0

        objects = sorted(
            objects, key=self._id_getter if self._data_sorting is None else self._data_sorting
        )

        if objects:
            if need_data.need_has_next:
                last_obj_id = self._id_getter(objects[-1])
                has_next = await repo.exists_by(
                    query.add_filter(self._after_filter(last_obj_id))
                )

            if need_data.need_page:
                first_obj_id = self._id_getter(objects[0])
                count_prev = await repo.count(
                    query.add_filter(self._before_filter(first_obj_id))
                )
                has_prev = count_prev > 0
            elif need_data.need_has_prev:
                first_obj_id = self._id_getter(objects[0])
                has_prev = await repo.exists_by(
                    query.add_filter(self._before_filter(first_obj_id))
                )
        edges = [
            Edge(
                cursor=RelayCursorInfo.encode_cursor(self._id_getter(instance)),
                node=self._out_model.from_entity(instance),
            )
            for instance in objects
        ]

        return Connection(
            page_info=PageInfo(
                has_next=has_next,
                has_prev=has_prev,
                count=len(edges),
                total=total,
                page=math.ceil((count_prev + 1) / cur_info.count),
                page_size=cur_info.count,
                total_pages=math.ceil(total / cur_info.count),
                start_cursor=edges[0].cursor if edges else None,
                end_cursor=edges[-1].cursor if edges else None,
            ),
            edges=edges,
            nodes=[edge.node for edge in edges],
        )
