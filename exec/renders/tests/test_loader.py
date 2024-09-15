from enum import Enum
from pathlib import Path
from typing import Literal, Annotated, Union

import pytest
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress

from greyhorse.app.contexts import SyncContext, AsyncContext
from greyhorse_renders.abc import SyncRenderFactory, AsyncRenderFactory
from greyhorse_renders.conf.loader import SyncDictLoader, AsyncDictLoader, SyncPydanticLoader, AsyncPydanticLoader
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


ROUTES_DICT = {
    'mapping': [
        {
            'module': 'module1',
            'model': 'model1',
            'method': 'method1',
            'map_to': {
                'type': 'legacy',
                'url': '127.0.0.1',
                'port': 50001,
            },
        },
        {
            'module': 'module2',
            'model': 'model1',
            'method': 'method1',
            'map_to': {
                'type': 'grpc',
                'path': 'tests.test1',
                'service': 'TestService',
                'method': 'ping1',
            },
        },
    ]
}


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
def test_sync_dict(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    sync_render_factory = ctrl.operator_factories.get(SyncRenderFactory)
    render_ctx = SyncContext[SyncRenderFactory](sync_render_factory)

    conf_loader = SyncDictLoader(
        root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert res.result == ROUTES_DICT

    res = conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.success
    for item in res.result:
        assert item == ROUTES_DICT

    res = conf_loader.load_toml(Path('routes.toml'))
    assert res.success
    assert res.result == ROUTES_DICT

    assert ctrl.destroy().success


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
@pytest.mark.asyncio
async def test_async_dict(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    async_render_factory = ctrl.operator_factories.get(AsyncRenderFactory)
    render_ctx = AsyncContext[AsyncRenderFactory](async_render_factory)

    conf_loader = AsyncDictLoader(
        root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = await conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert res.result == ROUTES_DICT

    res = await conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.success
    for item in res.result:
        assert item == ROUTES_DICT

    res = await conf_loader.load_toml(Path('routes.toml'))
    assert res.success
    assert res.result == ROUTES_DICT

    assert ctrl.destroy().success


@pytest.mark.parametrize(
    'param',
    ('', 'jinja'),
    ids=('Simple', 'Jinja'),
)
def test_sync_pydantic(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    sync_render_factory = ctrl.operator_factories.get(SyncRenderFactory)
    render_ctx = SyncContext[SyncRenderFactory](sync_render_factory)

    conf_loader = SyncPydanticLoader(
        doc_schema=Document, root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert isinstance(res.result, Document)

    res = conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.success
    for item in res.result:
        assert isinstance(item, Document)

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
async def test_async_pydantic(param):
    ctrl = RendersController('test')
    assert ctrl.create().success

    async_render_factory = ctrl.operator_factories.get(AsyncRenderFactory)
    render_ctx = AsyncContext[AsyncRenderFactory](async_render_factory)

    conf_loader = AsyncPydanticLoader(
        doc_schema=Document, root_dir=Path('tests/data'),
        render_ctx=render_ctx, default_render_key=param,
    )

    res = await conf_loader.load_yaml(Path('routes.yml'))
    assert res.success
    assert isinstance(res.result, Document)

    res = await conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.success
    for item in res.result:
        assert isinstance(item, Document)

    res = await conf_loader.load_toml(Path('routes.toml'))
    assert res.success
    assert isinstance(res.result, Document)

    assert ctrl.destroy().success
