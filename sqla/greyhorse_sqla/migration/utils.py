from sqlalchemy import ARRAY, BindParameter, False_, True_
from sqlalchemy.sql.functions import Function


def render_item(type_, obj, autogen_context):
    """Apply custom rendering for selected items."""
    from sqlalchemy_utils import ChoiceType
    sa_prefix = autogen_context.opts['sqlalchemy_module_prefix']

    if type_ == 'server_default':
        if isinstance(obj.arg, str):
            return f'{sa_prefix}text(\'{obj.arg}\')'
        elif isinstance(obj.arg, BindParameter):
            value = str(obj.arg.compile(
                dialect=autogen_context.dialect,
                compile_kwargs={'literal_binds': True})
            )
            return f'{sa_prefix}literal({value})'

        elif isinstance(obj.arg, False_ | True_):
            return f'{sa_prefix}{obj.arg}()'
        elif isinstance(obj.arg, Function):
            return f'{sa_prefix}func.{obj.arg}'

    elif type_ == 'type':
        if isinstance(obj, ChoiceType):
            return f'{sa_prefix}{repr(obj.impl)}'
        elif isinstance(obj, ARRAY):
            autogen_context.imports.add('import sqlalchemy_utils as su')
            return f'{sa_prefix}ARRAY({sa_prefix}{repr(obj.item_type)}).with_variant(' \
                   f'su.ScalarListType({obj.item_type.python_type.__name__}), ' \
                   f'\'sqlite\')'
        elif obj.__class__.__module__.startswith('sqlalchemy_utils'):
            autogen_context.imports.add('import sqlalchemy_utils as su')
            return f'su.{repr(obj)}'

    # default rendering for other objects
    return False
