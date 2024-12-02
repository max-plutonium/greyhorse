from abc import ABC, abstractmethod
from typing import Any, Self


class Query(ABC):
    __slots__ = ('_filter_exprs', '_filter_params', '_sorting_exprs')

    def __init__(
        self,
        filter_exprs: list[Any] | None = None,
        sorting_exprs: list[Any] | None = None,
        **filter_params: dict[str, Any],
    ) -> None:
        self._filter_exprs = filter_exprs or []
        self._filter_params = filter_params
        self._sorting_exprs = sorting_exprs or []

    def add_filter[F](self, filter: F) -> 'Query':
        filter_exprs = [*self._filter_exprs, filter]
        return type(self)(filter_exprs, self._sorting_exprs, **self._filter_params)

    def add_sorting[S](self, sorting: S) -> 'Query':
        sorting_exprs = [*self._sorting_exprs, sorting]
        return type(self)(self._filter_exprs, sorting_exprs, **self._filter_params)

    def clone(self) -> 'Query':
        return type(self)(self._filter_exprs[:], self._sorting_exprs[:], **self._filter_params)

    @abstractmethod
    def apply_filter[F](self, filter: F) -> F: ...

    @abstractmethod
    def apply_sorting[S](self, sorting: S) -> S: ...

    def __eq__(self, other: Self) -> bool:
        return (self._filter_exprs, self._filter_params, self._sorting_exprs) == (
            other._filter_exprs,
            other._filter_params,
            other._sorting_exprs,
        )

    def __ne__(self, other: Self) -> bool:
        return not (self == other)
