from .translator import StaticTranslator

tr = StaticTranslator()

tr.load_package('greyhorse', 'translations.toml', 'greyhorse')
