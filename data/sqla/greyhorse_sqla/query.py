from collections.abc import Iterable
from typing import Any, override

from greyhorse.data.query import Query
from sqlalchemy import (
    ClauseElement,
    Delete,
    Exists,
    Select,
    SQLColumnExpression,
    TextClause,
    UnaryExpression,
    Update,
)


class SqlaQuery(Query):
    def __init__(
        self,
        filter_exprs: Iterable[SQLColumnExpression | TextClause] | None = None,
        sorting_exprs: list[UnaryExpression] | None = None,
        **filter_params: dict[str, Any],
    ) -> None:
        super().__init__(filter_exprs, sorting_exprs, **filter_params)

    @override
    def apply_filter(
        self, filter: Select[Any] | Exists | Update | Delete
    ) -> Select[Any] | Exists | Update | Delete:
        for item in self._filter_exprs:
            filter = filter.where(item)
        if self._filter_params:
            filter = filter.params(**self._filter_params)
        return filter

    @override
    def apply_sorting(self, sorting: Select[Any]) -> Select[Any]:
        for item in self._sorting_exprs:
            sorting = sorting.order_by(item)
        return sorting


def clause2string(clause: ClauseElement, params: dict[str, Any] | None = None) -> str:
    if params:
        clause = clause.params(params)

    compiled = clause.compile(compile_kwargs={'render_postcompile': True})
    res = [compiled.string]

    for k, v in compiled.params.items():
        if params and k in params:
            res.append(str(params[k]))
        else:
            res.append(str(v))

    return '$'.join(res)
