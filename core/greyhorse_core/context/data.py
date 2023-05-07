import asyncio
import contextlib
import threading
from contextvars import ContextVar
from typing import Mapping, Any


class ContextData(object):
    def __init__(self, props: Mapping[str, Any] | None = None, **kwargs):
        if props:
            for name, value in props.items():
                super().__setattr__(name, self._wrap(value))
        super().__setattr__('data', kwargs)
        self._id = None

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        else:
            return value

    def __setattr__(self, key, value):
        super().__setattr__(key, self._wrap(value))

    def __contains__(self, item):
        return item in self.__dict__

    # @property
    # def data(self):
    #     # noinspection PyUnresolvedReferences
    #     return self._data

    @property
    def raw_id(self):
        return self._id

    @property
    def session_id(self):
        if self._id:
            return self._id
        try:
            return id(asyncio.current_task())
        except RuntimeError:
            return threading.current_thread().ident

    @session_id.setter
    def session_id(self, value):
        self._id = value


_ctx: ContextVar[ContextData] = ContextVar('_ctx')


def get_context():
    if ctx := _ctx.get(None):
        return ctx
    _ctx.set(ContextData())
    return _ctx.get()


@contextlib.contextmanager
def with_context(force_new: bool = False):
    if not force_new:
        if ctx := _ctx.get(None):
            yield ctx
            return

    token = _ctx.set(ContextData())
    yield _ctx.get(None)
    _ctx.reset(token)
