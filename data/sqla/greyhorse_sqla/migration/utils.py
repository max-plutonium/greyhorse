from typing import Literal

from alembic.autogenerate.api import AutogenContext
from sqlalchemy import (
    ARRAY,
    BLOB,
    VARBINARY,
    BindParameter,
    Enum,
    False_,
    Interval,
    LargeBinary,
    True_,
    TypeDecorator,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.sql.functions import Function
from sqlalchemy_utils import LtreeType


def render_item(
    type_: str, obj: object, autogen_context: AutogenContext
) -> str | Literal[False]:
    """Apply custom rendering for selected items."""
    sa_prefix = autogen_context.opts['sqlalchemy_module_prefix']

    match type_:
        case 'server_default':
            if isinstance(obj.arg, str):
                return f"{sa_prefix}text('{obj.arg}')"
            if isinstance(obj.arg, BindParameter):
                value = str(
                    obj.arg.compile(
                        dialect=autogen_context.dialect, compile_kwargs={'literal_binds': True}
                    )
                )
                return f'{sa_prefix}literal({value})'

            if isinstance(obj.arg, False_ | True_):
                return f'{sa_prefix}{obj.arg}()'
            if isinstance(obj.arg, Function):
                return f'{sa_prefix}func.{obj.arg}'

        case 'type':
            if isinstance(obj, ARRAY):
                autogen_context.imports.add('import sqlalchemy_utils as su')
                return (
                    f'{sa_prefix}ARRAY({sa_prefix}{obj.item_type!r}).with_variant('
                    f'su.ScalarListType({obj.item_type.python_type.__name__}), '
                    f"'sqlite')"
                )
            if isinstance(obj, LargeBinary | BLOB | VARBINARY):
                autogen_context.imports.add('import sqlalchemy.dialects.postgresql as pg')
                return f"{sa_prefix}{obj!r}.with_variant(pg.BYTEA, 'postgresql')"
            if isinstance(obj, Enum) and not hasattr(obj, 'create_type'):
                return f'{sa_prefix}{obj!r}'.replace(', metadata=MetaData()', '')
            if isinstance(obj, Interval):
                return f'{sa_prefix}{obj!r}'

            if obj.__class__.__module__.startswith('sqlalchemy_utils'):
                if isinstance(obj, LtreeType):
                    autogen_context.imports.add('import sqlalchemy_utils as su')
                    return 'su.LtreeType()'
                if isinstance(obj.impl, VARBINARY):
                    autogen_context.imports.add('import sqlalchemy.dialects.postgresql as pg')
                    return f"{sa_prefix}{obj.impl!r}.with_variant(pg.BYTEA, 'postgresql')"
                return f'{sa_prefix}{obj.impl!r}'

            if isinstance(obj, TypeDecorator):
                obj = obj.load_dialect_impl(autogen_context.dialect)

            if obj.__class__.__module__.startswith('sqlalchemy.dialects.sqlite'):
                autogen_context.imports.add('import sqlalchemy.dialects.sqlite as sq')
                return f'sq.{obj.compile(autogen_context.dialect)}'

            if obj.__class__.__module__.startswith('sqlalchemy.dialects.postgresql'):
                autogen_context.imports.add('import sqlalchemy.dialects.postgresql as pg')
                if isinstance(obj, JSONB):
                    return (
                        f"pg.{obj!r}.with_variant({sa_prefix}JSON, 'sqlite', 'mysql')".replace(
                            'astext_type=', f'astext_type={sa_prefix}'
                        )
                    )
                if isinstance(obj, INET):
                    return f"pg.{obj!r}.with_variant({sa_prefix}String, 'sqlite', 'mysql')"
                return f'pg.{obj!r}'

            if obj.__class__.__module__.startswith('sqlalchemy.dialects.mysql'):
                autogen_context.imports.add('import sqlalchemy.dialects.mysql as my')
                return f'my.{obj.compile(autogen_context.dialect)}'

            return f'{sa_prefix}{obj!r}'

    # default rendering for other objects
    return False
