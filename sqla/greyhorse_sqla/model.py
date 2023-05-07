from functools import partial
from typing import Mapping, Any, Sequence, Tuple, Self

from sqlalchemy import ColumnCollection, inspect, select, update, delete, tuple_, func, literal_column, exists, Column
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.orm import DeclarativeBase, joinedload, selectinload, RelationshipProperty, DeclarativeMeta
from sqlalchemy.orm.decl_api import DeclarativeAttributeIntercept
from sqlalchemy.sql.base import ReadOnlyColumnCollection

from greyhorse_core.data.models.base import IdType
from greyhorse_core.data.models.filterable import FilterableModel
from greyhorse_core.utils.hashes import calculate_digest
from greyhorse_sqla.query import SqlaFiltersQuery, SqlaSortingQuery


class SqlaModelMeta(type(FilterableModel), DeclarativeAttributeIntercept):
    pass


class SqlaModel(
    DeclarativeBase,
    FilterableModel[IdType, SqlaFiltersQuery, SqlaSortingQuery],
    metaclass=SqlaModelMeta,
):
    __abstract__ = True

    class Meta(FilterableModel.Meta):
        single_loader = joinedload
        list_loader = selectinload
        _column_names_map = dict()
        _query_opts_cache: dict[str, list] = dict()

    # noinspection PyUnresolvedReferences
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        meta_dict = dict()
        for t in reversed(cls.Meta.__mro__):
            meta_dict.update({k: v for k, v in vars(t).items() if not k.startswith('__')})
        cls.Meta = type('Meta', (FilterableModel.Meta,), meta_dict)

        cls.Meta.private_fields.update({'metadata', 'registry'})
        cls.Meta.non_serializable_fields.update({'metadata', 'registry'})
        cls.Meta._query_opts_cache = dict()

        try:
            column_names_map = inspect(cls).c
        except NoInspectionAvailable:
            pass
        else:
            column_names_map = zip([column.name for column in column_names_map], column_names_map.keys())
            cls.Meta._column_names_map = dict(column_names_map)

    def __init__(self, **kwargs):
        super().__init__()

        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_id_value(self) -> IdType:
        return self._get_column_values(self._get_id_columns())

    @classmethod
    def get_columns(cls) -> ReadOnlyColumnCollection:
        return cls.__table__.columns()

    @classmethod
    def get_relationships(cls) -> Mapping[str, Any]:
        return cls.__mapper__.relationships.items()

    # noinspection PyProtectedMember
    @classmethod
    def query_options(cls, include: set[str] | None = None, exclude: set[str] | None = None):
        args_digest = calculate_digest((include, exclude))

        if args_digest in cls.Meta._query_opts_cache:
            return cls.Meta._query_opts_cache[args_digest]

        result = list()
        suboptions = dict()
        suboptions_functions = dict()

        for rela_name, rela in cls.get_relationships():  # type: str, RelationshipProperty
            include_rela = True
            include_subkeys = {
                key.replace(f'{rela_name}.', '') for key in include if key.startswith(f'{rela_name}.')
            } if isinstance(include, set) else set()
            exclude_subkeys = {
                key.replace(f'{rela_name}.', '') for key in exclude if key.startswith(f'{rela_name}.')
            } if isinstance(exclude, set) else set()

            if include:
                include_rela &= include == '*' or rela_name in include or bool(include_subkeys)
            if include_rela and exclude:
                include_rela &= not (exclude == '*' or (not exclude_subkeys and rela_name in exclude))
            if include_rela:
                options = cls.Meta.list_loader(rela.class_attribute) if rela.uselist \
                    else cls.Meta.single_loader(rela.class_attribute)

                suboptions[rela_name] = options
                new_include, new_exclude = include_subkeys or None, exclude_subkeys or None
                suboptions_function = partial(rela.entity.class_.query_options, new_include, new_exclude)
                suboptions_functions[rela_name] = suboptions_function
                result.append(options)

        cls.Meta._query_opts_cache[args_digest] = result

        for rela_name, sub_rela in suboptions.items():
            subopts = suboptions_functions[rela_name]()
            suboptions[rela_name] = sub_rela.options(*subopts)

        return result

    @classmethod
    def query_for_select(cls, include_rela: set[str] | None = None,
                         exclude_rela: set[str] | None = None, **kwargs):
        return select(cls).options(*cls.query_options(include_rela, exclude_rela))

    @classmethod
    def query_for_update(cls, **kwargs):
        return update(cls)

    @classmethod
    def query_for_delete(cls, **kwargs):
        return delete(cls)

    #
    # Query operations
    #

    @classmethod
    def query_get(cls, id_value: IdType, query=None, **kwargs):
        cls._check_abstract()
        if not isinstance(id_value, (list, tuple, dict)):
            ident_ = [id_value]
        else:
            ident_ = id_value
        columns = cls._get_id_columns()
        if len(ident_) != len(columns):
            raise ValueError(
                f'Incorrect number of values as primary key: expected {len(columns)}, got {len(ident_)}.')

        clause = query if query is not None else cls.query_for_select(**kwargs)
        for i, c in enumerate(columns):
            try:
                val = ident_[i]
            except KeyError:
                val = ident_[cls._get_field_by_column(c)]
            clause = clause.where(c == val)
        return clause

    @classmethod
    def query_any(cls, indices: Sequence[IdType], query=None, **kwargs):
        cls._check_abstract()
        columns = cls._get_id_columns()
        clause = query if query is not None else cls.query_for_select(**kwargs)
        vals_clause = []

        for ident in indices:
            if not isinstance(ident, (list, tuple, dict)):
                ident_ = [ident]
            else:
                ident_ = ident

            if len(ident_) != len(columns):
                raise ValueError(
                    f'Incorrect number of values as primary key: expected {len(columns)}, got {len(ident_)}.')

            vals = []
            for i, c in enumerate(columns):
                try:
                    val = ident_[i]
                except KeyError:
                    val = ident_[cls._get_field_by_column(c)]
                vals.append(val)

            if len(vals) == 1:
                vals_clause.append(vals[0])
            elif len(vals) > 1:
                vals_clause.append((*vals,))

        if len(columns) == 1:
            clause = clause.where(columns[columns.keys()[0]].in_(vals_clause))
        elif len(columns) > 1:
            clause = clause.where(tuple_(*columns).in_(vals_clause))
        return clause

    @classmethod
    def query_list(
        cls, filters: SqlaFiltersQuery | None = None,
        sorting: SqlaSortingQuery | None = None,
        skip: int = 0, limit: int = 0, **kwargs,
    ):
        query = cls.query_for_select(**kwargs).offset(skip if skip >= 0 else 0)
        if limit > 0:
            query = query.limit(limit)
        if filters:
            query = filters.apply(query)
        if sorting:
            query = sorting.apply(query)
        return query

    @classmethod
    def query_count(cls, filters: SqlaFiltersQuery | None = None, **kwargs):
        if filters:
            query = filters.apply(cls.query_for_select())
        else:
            query = cls.__table__

        return select(func.count(literal_column('1'))).select_from(query.alias())

    @classmethod
    def query_exists(cls, id_value: IdType, **kwargs):
        return cls.query_get(id_value, query=exists(), **kwargs).select()

    @classmethod
    def query_exists_by(cls, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(exists(cls)).select()

    @classmethod
    def query_update(cls, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(cls.query_for_update(**kwargs))

    @classmethod
    def query_delete(cls, filters: SqlaFiltersQuery, **kwargs):
        return filters.apply(cls.query_for_delete(**kwargs))

    #
    # Private
    #

    # noinspection PyUnresolvedReferences
    @classmethod
    def _check_abstract(cls):
        if cls.__table__ is None:
            raise TypeError(f'Model {cls.__name__} is abstract, no table is defined!')

    def __eq__(self, other: Self):
        self._check_abstract()
        return type(self) == type(other) and self.get_id_value() == other.get_id_value()

    def __hash__(self):
        self._check_abstract()
        return self.get_id_value().__hash__()

    @classmethod
    def _get_id_columns(cls) -> ColumnCollection:
        return cls.__table__.primary_key.columns

    # noinspection PyProtectedMember
    @classmethod
    def _get_field_by_column(cls, c: Column) -> str:
        return cls.Meta._column_names_map.get(c.name)

    def _get_column_values(
            self, columns: ColumnCollection, force_tuple: bool = False) -> Any | Tuple[Any]:
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
