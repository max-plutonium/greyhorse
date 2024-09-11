from greyhorse.i18n import StaticTranslator


def test_load_file_unload_file() -> None:
    tr = StaticTranslator()
    assert tr.size() == 0

    tr.load_file('tests/translations.toml')
    assert tr.size() == 8
    tr.load_file('tests/translations.toml', namespace='root')
    assert tr.size() == 16

    assert tr('translations.title') == 'Title'
    assert tr('root.title') == 'Title'

    assert not tr.set_default_lang('translations1', 'ru')
    assert tr.set_default_lang('translations', 'ru')

    assert tr('translations.title') == 'Заголовок'
    assert tr('root.title') == 'Title'

    tr.unload('translations1')
    tr.unload('translations')

    assert tr.size() == 8
    assert not tr('translations.title')
    assert tr('root.title') == 'Title'


def test_one_namespace() -> None:
    tr = StaticTranslator()
    tr.load_file('tests/translations.toml')

    assert not tr('default')
    assert tr('title') == 'Title'
    assert tr('translations.title') == 'Title'
    assert tr('title', 'en') == 'Title'
    assert tr('title', 'ru') == 'Заголовок'
    assert tr('translations.title') == 'Title'
    assert tr('translations.title', 'en') == 'Title'
    assert tr('translations.title', 'ru') == 'Заголовок'

    assert tr('owner.name') == 'Name'
    assert tr('owner.name', 'en') == 'Name'
    assert tr('owner.name', 'ru') == 'Имя'
    assert tr('translations.owner.name') == 'Name'
    assert tr('translations.owner.name', 'en') == 'Name'
    assert tr('translations.owner.name', 'ru') == 'Имя'

    assert tr('owner.name.en') == 'Name'
    assert tr('owner.name.ru') == 'Имя'
    assert tr('translations.owner.name.en') == 'Name'
    assert tr('translations.owner.name.ru') == 'Имя'

    assert tr('owner.name.en', 'en') == 'Name'
    assert tr('owner.name.ru', 'en') == 'Имя'
    assert tr('owner.name.en', 'ru') == 'Name'
    assert tr('owner.name.ru', 'ru') == 'Имя'
    assert tr('translations.owner.name.en', 'en') == 'Name'
    assert tr('translations.owner.name.ru', 'en') == 'Имя'
    assert tr('translations.owner.name.en', 'ru') == 'Name'
    assert tr('translations.owner.name.ru', 'ru') == 'Имя'

    assert tr('data.title1') == 'Data'
    assert tr('data.title1', 'en') == 'Data'
    assert tr('data.title1', 'ru') == 'Data'
    assert tr('translations.data.title1') == 'Data'
    assert tr('translations.data.title1', 'en') == 'Data'
    assert tr('translations.data.title1', 'ru') == 'Data'

    assert not tr('data.title1.en')
    assert not tr('data.title1.ru')
    assert not tr('data.title1.en', 'en')
    assert not tr('data.title1.en', 'ru')
    assert not tr('data.title1.ru', 'en')
    assert not tr('data.title1.ru', 'ru')
    assert not tr('translations.data.title1.en')
    assert not tr('translations.data.title1.ru')
    assert not tr('translations.data.title1.en', 'en')
    assert not tr('translations.data.title1.en', 'ru')
    assert not tr('translations.data.title1.ru', 'en')
    assert not tr('translations.data.title1.ru', 'ru')

    assert not tr('data.title2')
    assert not tr('data.title2', 'en')
    assert tr('data.title2', 'ru') == 'Данные'
    assert not tr('translations.data.title2')
    assert not tr('translations.data.title2', 'en')
    assert tr('translations.data.title2', 'ru') == 'Данные'

    assert not tr('data.title2.en')
    assert tr('data.title2.ru') == 'Данные'
    assert not tr('data.title2.en', 'en')
    assert not tr('data.title2.en', 'ru')
    assert tr('data.title2.ru', 'en') == 'Данные'
    assert tr('data.title2.ru', 'ru') == 'Данные'
    assert not tr('translations.data.title2.en')
    assert tr('translations.data.title2.ru') == 'Данные'
    assert not tr('translations.data.title2.en', 'en')
    assert not tr('translations.data.title2.en', 'ru')
    assert tr('translations.data.title2.ru', 'en') == 'Данные'
    assert tr('translations.data.title2.ru', 'ru') == 'Данные'


def test_two_namespaces() -> None:
    tr = StaticTranslator()
    tr.load_file('tests/translations.toml')
    tr.load_file('tests/translations.toml', namespace='root')

    assert not tr('default')
    assert not tr('root.default')
    assert not tr('title')
    assert tr('translations.title') == 'Title'
    assert tr('root.title') == 'Title'
    assert not tr('title', 'en')
    assert not tr('title', 'ru')
    assert tr('translations.title', 'en') == 'Title'
    assert tr('translations.title', 'ru') == 'Заголовок'
    assert tr('root.title', 'en') == 'Title'
    assert tr('root.title', 'ru') == 'Заголовок'

    assert not tr('owner.name')
    assert not tr('owner.name', 'en')
    assert not tr('owner.name', 'ru')
    assert tr('translations.owner.name') == 'Name'
    assert tr('translations.owner.name', 'en') == 'Name'
    assert tr('translations.owner.name', 'ru') == 'Имя'
    assert tr('root.owner.name') == 'Name'
    assert tr('root.owner.name', 'en') == 'Name'
    assert tr('root.owner.name', 'ru') == 'Имя'

    assert not tr('owner.name.en')
    assert not tr('owner.name.ru')
    assert tr('translations.owner.name.en') == 'Name'
    assert tr('translations.owner.name.ru') == 'Имя'
    assert tr('root.owner.name.en') == 'Name'
    assert tr('root.owner.name.ru') == 'Имя'

    assert not tr('owner.name.en', 'en')
    assert not tr('owner.name.ru', 'en')
    assert not tr('owner.name.en', 'ru')
    assert not tr('owner.name.ru', 'ru')
    assert tr('translations.owner.name.en', 'en') == 'Name'
    assert tr('translations.owner.name.ru', 'en') == 'Имя'
    assert tr('translations.owner.name.en', 'ru') == 'Name'
    assert tr('translations.owner.name.ru', 'ru') == 'Имя'
    assert tr('root.owner.name.en', 'en') == 'Name'
    assert tr('root.owner.name.ru', 'en') == 'Имя'
    assert tr('root.owner.name.en', 'ru') == 'Name'
    assert tr('root.owner.name.ru', 'ru') == 'Имя'

    assert not tr('data.title1')
    assert not tr('data.title1', 'en')
    assert not tr('data.title1', 'ru')
    assert tr('translations.data.title1') == 'Data'
    assert tr('translations.data.title1', 'en') == 'Data'
    assert tr('translations.data.title1', 'ru') == 'Data'
    assert tr('root.data.title1') == 'Data'
    assert tr('root.data.title1', 'en') == 'Data'
    assert tr('root.data.title1', 'ru') == 'Data'

    assert not tr('data.title1.en')
    assert not tr('data.title1.ru')
    assert not tr('data.title1.en', 'en')
    assert not tr('data.title1.en', 'ru')
    assert not tr('data.title1.ru', 'en')
    assert not tr('data.title1.ru', 'ru')
    assert not tr('translations.data.title1.en')
    assert not tr('translations.data.title1.ru')
    assert not tr('translations.data.title1.en', 'en')
    assert not tr('translations.data.title1.en', 'ru')
    assert not tr('translations.data.title1.ru', 'en')
    assert not tr('translations.data.title1.ru', 'ru')
    assert not tr('root.data.title1.en')
    assert not tr('root.data.title1.ru')
    assert not tr('root.data.title1.en', 'en')
    assert not tr('root.data.title1.en', 'ru')
    assert not tr('root.data.title1.ru', 'en')
    assert not tr('root.data.title1.ru', 'ru')

    assert not tr('data.title2')
    assert not tr('data.title2', 'en')
    assert not tr('data.title2', 'ru')
    assert not tr('translations.data.title2')
    assert not tr('translations.data.title2', 'en')
    assert tr('translations.data.title2', 'ru') == 'Данные'
    assert not tr('root.data.title2')
    assert not tr('root.data.title2', 'en')
    assert tr('root.data.title2', 'ru') == 'Данные'

    assert not tr('data.title2.en')
    assert not tr('data.title2.ru')
    assert not tr('data.title2.en', 'en')
    assert not tr('data.title2.en', 'ru')
    assert not tr('data.title2.ru', 'en')
    assert not tr('data.title2.ru', 'ru')
    assert not tr('translations.data.title2.en')
    assert tr('translations.data.title2.ru') == 'Данные'
    assert not tr('translations.data.title2.en', 'en')
    assert not tr('translations.data.title2.en', 'ru')
    assert tr('translations.data.title2.ru', 'en') == 'Данные'
    assert tr('translations.data.title2.ru', 'ru') == 'Данные'
    assert not tr('root.data.title2.en')
    assert tr('root.data.title2.ru') == 'Данные'
    assert not tr('root.data.title2.en', 'en')
    assert not tr('root.data.title2.en', 'ru')
    assert tr('root.data.title2.ru', 'en') == 'Данные'
    assert tr('root.data.title2.ru', 'ru') == 'Данные'
