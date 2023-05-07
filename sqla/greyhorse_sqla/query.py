from functools import reduce
from typing import Mapping, Any, Self

from sqlalchemy import Select, SQLColumnExpression, UnaryExpression, ClauseElement, Exists, Update, Delete, TextClause


class SqlaFiltersQuery:
    def __init__(
        self, expr: list[SQLColumnExpression | TextClause],
        params: Mapping[str, Any] | None = None,
    ):
        self._expr = expr
        self._params = params

    def apply(self, query: Select[Any] | Exists | Update | Delete):
        for item in self._expr:
            query = query.where(item)
        if self._params:
            query = query.params(**self._params)
        return query

    def __eq__(self, other: Self):
        return (self._expr, self._params) == (other._expr, other._params)


class SqlaSortingQuery:
    def __init__(self, expr: list[UnaryExpression]):
        self._expr = expr

    def apply(self, query: Select[Any]):
        for item in self._expr:
            query = query.order_by(item)
        return query


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
