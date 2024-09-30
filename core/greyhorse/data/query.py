from abc import ABC, abstractmethod
from typing import Self


class Query(ABC):
    @abstractmethod
    def apply_filter[F](self, filter: F) -> F: ...

    @abstractmethod
    def apply_sorting[S](self, sorting: S) -> S: ...

    @abstractmethod
    def __eq__(self, other: Self): ...

    def __ne__(self, other: Self):
        return not (self == other)
