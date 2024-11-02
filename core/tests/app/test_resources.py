from collections.abc import AsyncGenerator, Generator
from decimal import Decimal

from greyhorse.app.resources.container import make_container, root
from greyhorse.app.resources.injection import inject


def sync_ctx_manager() -> Generator[str, str, None]:
    res = '123'
    yield res
    assert res == '123'


async def async_ctx_manager() -> AsyncGenerator[Decimal, Decimal]:
    res = Decimal(789)
    yield res
    assert res == Decimal(789)


def test_container() -> None:
    container = make_container()

    assert container.registry.add_factory(int, lambda _: 123)
    assert container.registry.add_factory(str, sync_ctx_manager)
    assert container.registry.add_factory(Decimal, async_ctx_manager)

    assert container.get(int).unwrap() == 123

    with container.context:
        with container() as c1:
            assert c1.registry.add_factory(int, lambda _: 456)
            assert c1.get(int).unwrap() == 456
            assert c1.get(str).unwrap() == '123'
            assert Decimal(789) == c1.get(Decimal).unwrap()

        assert container.get(int).unwrap() == 123


class A:
    pass


class B:
    @inject
    def __init__(self, a: A) -> None:
        self.a = a


class C:
    @inject
    def __init__(self, conf: str) -> None:
        self._conf = conf

    def get_data(self) -> str:
        return self._conf


@inject
def make_c(deps: C | None) -> C | None:
    return deps


class SomeClass:
    @inject
    def __init__(self, a: A, b: B, c: C | None) -> None:
        self.a = a
        self.b = b
        self.c = c
        c1 = make_c()
        assert c is c1


def test_injection() -> None:
    conf_str = 'test'
    a = A()

    def factory(t: type) -> object:
        match t.__name__:
            case 'A':
                return a
            case 'B':
                return B()
            case 'C':
                return C()
            case _:
                return None

    assert root.registry.add_default_factory('', factory, cache=True)
    assert root.registry.add_factory(str, conf_str)

    instance = SomeClass()

    assert isinstance(instance.a, A)
    assert isinstance(instance.b, B)
    assert isinstance(instance.c, C)

    assert instance.a is a
    assert instance.b.a is a
    assert instance.c.get_data() is conf_str
