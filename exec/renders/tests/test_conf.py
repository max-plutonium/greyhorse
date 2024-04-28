from enum import Enum
from pathlib import Path
from typing import Literal, Annotated, Union

import pytest
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress

from greyhorse.app.context import SyncContext, AsyncContext
from greyhorse_renders.abc import SyncRenderFactory, AsyncRenderFactory
from greyhorse_renders.conf.loader import SyncConfLoader, AsyncConfLoader
from greyhorse_renders.controller import RendersController


class EntryType(str, Enum):
    legacy = 'legacy'
    grpc = 'grpc'


class BackendItem(BaseModel):
    type: EntryType


class LegacyBackendItem(BackendItem):
    type: Literal['legacy']
    url: AnyHttpUrl | IPvAnyAddress
    port: int = Field(gte=0, lt=65536)


class GRPCBackendItem(BackendItem):
    type: Literal['grpc']
    path: str
    service: str
    method: str


class EntryItem(BaseModel):
    module: str
    model: str = ''
    method: str = ''

    map_to: Annotated[
        Union[LegacyBackendItem, GRPCBackendItem],
        Field(discriminator='type'),
    ]


class Document(BaseModel):
    mapping: list[EntryItem]


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
def test_sync_conf(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    sync_render_factory = ctrl.operator_factories.get(SyncRenderFactory)
    render_ctx = SyncContext[SyncRenderFactory](sync_render_factory)

    conf_loader = SyncConfLoader(
        doc_schema=Document, root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert isinstance(res.result, Document)

    res = conf_loader.load_toml(Path('routes.toml'))
    assert res.success
    assert isinstance(res.result, Document)

    assert ctrl.destroy().success


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
@pytest.mark.asyncio
async def test_async_conf(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    async_render_factory = ctrl.operator_factories.get(AsyncRenderFactory)
    render_ctx = AsyncContext[AsyncRenderFactory](async_render_factory)

    conf_loader = AsyncConfLoader(
        doc_schema=Document, root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = await conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert isinstance(res.result, Document)

    res = await conf_loader.load_toml(Path('routes.toml'))
    assert res.success
    assert isinstance(res.result, Document)

    assert ctrl.destroy().success
