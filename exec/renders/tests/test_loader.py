from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import pytest
from greyhorse.app.resources import Container, make_container
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
def container() -> Container:
    ctrl = RendersController()
    container = make_container()

    assert ctrl.setup(container).unwrap()
    assert len(container.registry) > 0

    yield container

    assert ctrl.teardown(container).unwrap()
    assert len(container.registry) == 0


@pytest.mark.parametrize('param', ('', 'jinja'), ids=('Simple', 'Jinja'))
def test_sync_dict(param: str, container: Container) -> None:
    render_factory = container.get(SyncRenderFactory).unwrap()

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
async def test_async_dict(param: str, container: Container) -> None:
    render_factory = container.get(AsyncRenderFactory).unwrap()

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
def test_sync_pydantic(param: str, container: Container) -> None:
    render_factory = container.get(SyncRenderFactory).unwrap()

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
async def test_async_pydantic(param: str, container: Container) -> None:
    render_factory = container.get(AsyncRenderFactory).unwrap()

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
