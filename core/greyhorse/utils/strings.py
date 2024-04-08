import re
from enum import Enum
from typing import Type


def snake2kebab(string: str) -> str:
    return re.sub('_', '-', string)


def kebab2snake(string: str) -> str:
    return re.sub('-', '_', string)


def snake2camel(string: str, upper: bool = False) -> str:
    result = []

    for i, word in enumerate(string.split('_')):
        if upper or i > 0:
            word = word.capitalize()
        result.append(word)

    return ''.join(result)


def prepare_enum_keys(enum_class: Type[Enum]):
    return [snake2kebab(str(e.value).lower()) for e in enum_class]


def to_human_size(num: int | float, suffix: str = 'B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return f'{num:3.1f}{unit}{suffix}'
        num /= 1024.0
    return f'{num:.1f}Yi{suffix}'
