from typing import Any, Mapping, Self, TYPE_CHECKING, Tuple

from sqlalchemy import Column, ColumnCollection
from sqlalchemy.orm import DeclarativeBase, joinedload, selectinload
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from sqlalchemy.sql.base import ReadOnlyColumnCollection

from greyhorse_core.data.models.base import IdType
from greyhorse_core.data.models.filterable import FilterableModel
from greyhorse_sqla.query import SqlaFiltersQuery, SqlaSortingQuery

if TYPE_CHECKING:
    from .repository import SqlaModelRepository


class SqlaModelMeta(type(FilterableModel), DeclarativeAttributeIntercept):
    pass


class SqlaModel(
    DeclarativeBase,
    FilterableModel[IdType, SqlaFiltersQuery, SqlaSortingQuery],
    metaclass=SqlaModelMeta,
):
    __abstract__ = True
    _repo: 'SqlaModelRepository[IdType, Self, SqlaFiltersQuery, SqlaSortingQuery]'

    class Meta(FilterableModel.Meta):
        single_loader = joinedload
        list_loader = selectinload
        _column_names_map = dict()

    # noinspection PyUnresolvedReferences
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        meta_dict = dict()
        for t in reversed(cls.Meta.__mro__):
            meta_dict.update({k: v for k, v in vars(t).items() if not k.startswith('__')})
        cls.Meta = type('Meta', (FilterableModel.Meta,), meta_dict)

        cls.Meta.private_fields.update({'metadata', 'registry'})
        cls.Meta.non_serializable_fields.update({'metadata', 'registry'})

    def __init__(self, **kwargs):
        super().__init__()

        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def bind(cls, repository: 'SqlaModelRepository[IdType, Self, SqlaFiltersQuery, SqlaSortingQuery]'):
        cls._repo = repository

    def get_id_value(self) -> IdType:
        # noinspection PyProtectedMember
        return self._get_column_values(self.__table__.primary_key.columns)

    @classmethod
    def get_columns(cls) -> ReadOnlyColumnCollection:
        return cls.__table__.columns()

    @classmethod
    def get_relationships(cls) -> Mapping[str, Any]:
        return cls.__mapper__.relationships.items()

    #
    # Private
    #

    def __eq__(self, other: Self):
        return type(self) == type(other) and self.get_id_value() == other.get_id_value()

    def __hash__(self):
        return self.get_id_value().__hash__()

    @classmethod
    def _get_field_by_column(cls, c: Column) -> str:
        # noinspection PyProtectedMember
        return cls._repo._column_names_map.get(c.name)

    def _get_column_values(
        self, columns: ColumnCollection, force_tuple: bool = False,
    ) -> Any | Tuple[Any]:
        rv = []
        for c in columns:
            rv.append(getattr(self, self._get_field_by_column(c)))
        return rv[0] if len(rv) == 1 and not force_tuple else tuple(rv)

    @classmethod
    def _get_fk_columns(cls, model) -> ColumnCollection:
        for fk in cls.__table__.foreign_keys:
            if model.__table__ == fk.constraint.referred_table:
                return fk.constraint.columns
        return ColumnCollection()
