from sqlalchemy import ARRAY, BindParameter, False_, True_
from sqlalchemy.sql.functions import Function


def render_item(type_, obj, autogen_context) -> str | bool:
    """Apply custom rendering for selected items."""
    sa_prefix = autogen_context.opts['sqlalchemy_module_prefix']

    if type_ == 'server_default':
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

    elif type_ == 'type':
        if isinstance(obj, ARRAY):
            autogen_context.imports.add('import sqlalchemy_utils as su')
            return (
                f'{sa_prefix}ARRAY({sa_prefix}{obj.item_type!r}).with_variant('
                f'su.ScalarListType({obj.item_type.python_type.__name__}), '
                f"'sqlite')"
            )
        if obj.__class__.__module__.startswith('sqlalchemy_utils'):
            return f'{sa_prefix}{obj.impl!r}'

    # default rendering for other objects
    return False
