from greyhorse.error import Error, ErrorCase
from greyhorse.i18n import StaticTranslator
from greyhorse.result import Result

tr = StaticTranslator()


class TestError(Error, tr=tr):
    namespace = 'tests'

    FirstError = ErrorCase(msg='First Error: "{value}"', value=int)
    SecondError = ErrorCase(msg='Second Error: "{value}"', value=int)
    TranslatedError = ErrorCase(code='owner.error', value=str)
    Unexpected = ErrorCase(msg='Unexpected error: "{details}"', details=str)


def test_error():
    e1 = TestError.FirstError(value=123)
    e2 = TestError.SecondError(value='qwer')
    e3 = TestError.TranslatedError(value='error value')
    e4 = TestError.Unexpected(details='Unexpected')

    tr.load_file('tests/translations.toml', namespace='tests')

    assert 'First Error: "123"' == e1.message
    assert 'Second Error: "qwer"' == e2.message
    assert 'Error: \'error value\'' == e3.message
    assert 'Unexpected error: "Unexpected"' == e4.message

    res = 0

    for e in (e1, e2, e3, e4):
        match e:
            case TestError.FirstError(a):
                assert a == 123
                res += 1
            case TestError.SecondError(b):
                assert b == 'qwer'
                res += 1
            case TestError.TranslatedError(c):
                assert c == 'error value'
                res += 1
            case TestError.Unexpected(d):
                assert d == 'Unexpected'
                res += 1

        err_result = e.result()
        assert isinstance(err_result, Result.Err)
        assert err_result.is_err()

    assert res == 4
