from importlib.resources import Package, as_file, files
from pathlib import Path
from typing import Any

import tomlkit

from greyhorse.utils.dicts import build_dotted_keys_from_dict


class StaticTranslator:
    def __init__(self) -> None:
        self._data = {}
        self._defaults = {}

    def load_string(self, content: str, namespace: str) -> None:
        parsed = tomlkit.parse(content)
        self._defaults[namespace] = parsed.pop('default', None)
        self._data |= build_dotted_keys_from_dict(parsed, root_key=namespace)

    def load_file(self, filename: str, namespace: str | None = None) -> None:
        filename = Path(filename)
        namespace = namespace if namespace else filename.stem
        self.load_string(filename.read_text('utf-8'), namespace)

    def load_package(
        self, package: Package, filename: str, namespace: str | None = None
    ) -> None:
        filename = Path(filename)
        namespace = namespace if namespace else filename.stem
        source = files(package).joinpath(filename)
        with as_file(source) as file:
            self.load_string(file.read_text(), namespace)

    def unload(self, namespace: str) -> None:
        self._defaults.pop(namespace, None)
        keys_to_remove = [k for k, v in self._data.items() if k.startswith(f'{namespace}.')]
        for k in keys_to_remove:
            self._data.pop(k)

    def size(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def set_default_lang(self, namespace: str, lang: str) -> bool:
        if namespace not in self._defaults:
            return False
        self._defaults[namespace] = lang
        return True

    def namespaces(self) -> frozenset[str]:
        return frozenset(self._defaults.keys())

    def __call__(
        self, key: str, /, lang: str | None = None, default: str = '', **kwargs: dict[str, Any]
    ) -> str:
        if len(self._defaults) == 1:
            ns = next(iter(self._defaults.keys()))
        else:
            ns = key.find('.')
            ns = key[0:ns] if ns != -1 else None

        tries = []

        if lang:
            tries += [f'{key}.{lang}']
            if ns and ns in self._defaults:
                tries += [f'{ns}.{key}.{lang}']
                default_lang = self._defaults.get(ns)
                if default_lang != lang:
                    tries += [f'{key}.{default_lang}', f'{ns}.{key}.{default_lang}']

        tries += [key]
        if len(self._defaults) == 1:
            tries += [f'{ns}.{key}']
        if not lang and ns and ns in self._defaults:
            default_lang = self._defaults.get(ns)
            tries += [f'{key}.{default_lang}', f'{ns}.{key}.{default_lang}']

        for t in tries:
            if res := self._data.get(t):
                return res.format(**kwargs) if kwargs else res

        return default.format(**kwargs) if kwargs else default
