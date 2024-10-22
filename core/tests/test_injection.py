from greyhorse.injection import inject, storage
from greyhorse.maybe import Just, Maybe, Nothing


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
        assert c is not make_c()


def test_injection() -> None:
    conf_str = 'test'
    a = A()

    def factory(t: type) -> Maybe:
        match t.__name__:
            case 'str':
                return Just(conf_str)
            case 'A':
                return Just(a)
            case 'B':
                return Just(B())
            case 'C':
                return Just(C())
            case _:
                return Nothing

    storage.add_default_factory('', factory)

    instance = SomeClass()

    assert isinstance(instance.a, A)
    assert isinstance(instance.b, B)
    assert isinstance(instance.c, C)

    assert instance.a is a
    assert instance.b.a is a
    assert instance.c.get_data() is conf_str
