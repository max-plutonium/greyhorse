from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

import pytest
from greyhorse.app.registries import MutDictRegistry
from greyhorse_renders.abc import AsyncRenderFactory, SyncRenderFactory
from greyhorse_renders.conf.loader import (
    AsyncDictLoader,
    AsyncPydanticLoader,
    SyncDictLoader,
    SyncPydanticLoader,
)
from greyhorse_renders.controller import RendersController
from pydantic import AnyHttpUrl, BaseModel, Field, IPvAnyAddress


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

    map_to: Annotated[LegacyBackendItem | GRPCBackendItem, Field(discriminator='type')]


class Document(BaseModel):
    mapping: list[EntryItem]


ROUTES_DICT = {
    'mapping': [
        {
            'module': 'module1',
            'model': 'model1',
            'method': 'method1',
            'map_to': {'type': 'legacy', 'url': '127.0.0.1', 'port': 50001},
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


@pytest.fixture
def registry():
    ctrl = RendersController()

    registry = MutDictRegistry[type, Any]()
    assert ctrl.setup(registry).unwrap()
    assert len(registry) > 0

    yield registry

    assert ctrl.teardown(registry).unwrap()
    assert len(registry) == 0


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
def test_sync_dict(param, registry) -> None:
    render_factory = registry.get(SyncRenderFactory).unwrap()

    conf_loader = SyncDictLoader(
        root_dir=Path('tests/data'), render_factory=render_factory, default_render_key=param
    )

    res = conf_loader.load_yaml(Path('routes.yml'))
    assert res.is_ok()
    assert res.unwrap() == ROUTES_DICT

    res = conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.is_ok()
    for item in res.unwrap():
        assert item == ROUTES_DICT

    res = conf_loader.load_toml(Path('routes.toml'))
    assert res.is_ok()
    assert res.unwrap() == ROUTES_DICT


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
@pytest.mark.asyncio
async def test_async_dict(param, registry) -> None:
    render_factory = registry.get(AsyncRenderFactory).unwrap()

    conf_loader = AsyncDictLoader(
        root_dir=Path('tests/data'), render_factory=render_factory, default_render_key=param
    )

    res = await conf_loader.load_yaml(Path('routes.yml'))
    assert res.is_ok()
    assert res.unwrap() == ROUTES_DICT

    res = await conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.is_ok()
    for item in res.unwrap():
        assert item == ROUTES_DICT

    res = await conf_loader.load_toml(Path('routes.toml'))
    assert res.is_ok()
    assert res.unwrap() == ROUTES_DICT


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
def test_sync_pydantic(param, registry) -> None:
    render_factory = registry.get(SyncRenderFactory).unwrap()

    conf_loader = SyncPydanticLoader(
        doc_schema=Document,
        root_dir=Path('tests/data'),
        render_factory=render_factory,
        default_render_key=param,
    )

    res = conf_loader.load_yaml(Path('routes.yml'))
    assert res.is_ok()
    assert isinstance(res.unwrap(), Document)

    res = conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.is_ok()
    for item in res.unwrap():
        assert isinstance(item, Document)

    res = conf_loader.load_toml(Path('routes.toml'))
    assert res.is_ok()
    assert isinstance(res.unwrap(), Document)


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
@pytest.mark.asyncio
async def test_async_pydantic(param, registry) -> None:
    render_factory = registry.get(AsyncRenderFactory).unwrap()

    conf_loader = AsyncPydanticLoader(
        doc_schema=Document,
        root_dir=Path('tests/data'),
        render_factory=render_factory,
        default_render_key=param,
    )

    res = await conf_loader.load_yaml(Path('routes.yml'))
    assert res.is_ok()
    assert isinstance(res.unwrap(), Document)

    res = await conf_loader.load_yaml_list(Path('routes_list.yml'))
    assert res.is_ok()
    for item in res.unwrap():
        assert isinstance(item, Document)

    res = await conf_loader.load_toml(Path('routes.toml'))
    assert res.is_ok()
    assert isinstance(res.unwrap(), Document)
