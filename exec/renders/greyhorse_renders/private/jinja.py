import base64
from pathlib import Path
from typing import override, cast

import yaml
from jinja2 import Environment, FileSystemLoader, exceptions

from greyhorse.result import Result
from greyhorse.utils import json
from ..abc import AsyncRender, SyncRender
from ..errors import TemplateFileNotFound, TemplateSyntaxError


class JinjaBasicRender:
    def __init__(self, templates_dirs: list[Path], enable_async: bool = False):
        self._templates_env = Environment(
            loader=FileSystemLoader(templates_dirs),
            enable_async=enable_async,
        )
        self._templates_env.filters['b64encode'] = lambda s: base64.b64encode(s.encode('utf-8')).decode('utf-8')
        self._templates_env.filters['b64decode'] = lambda s: base64.b64decode(s.encode('utf-8')).decode('utf-8')
        self._templates_env.filters['toYaml'] = self.to_yaml
        self._templates_env.filters['toJson'] = self.to_json
        self._templates_env.globals['readBinary'] = self.read_binary

    @staticmethod
    def to_yaml(data: dict, indent: int = 0):
        dump = yaml.safe_dump(data)
        res = list()
        for line in dump.splitlines():
            res.append(' ' * indent + line)
        return '\n'.join(res)

    @staticmethod
    def to_json(data: dict, indent: int = 0):
        dump = json.dumps(data, use_indent=True).decode('utf-8')
        res = list()
        for line in dump.splitlines():
            res.append(' ' * indent + line)
        return '\n'.join(res)

    def read_binary(self, path: str):
        loader = cast(FileSystemLoader, self._templates_env.loader)

        for template_dir in loader.searchpath:
            target_path = Path(template_dir) / path
            if not target_path.is_file():
                continue
            content = target_path.read_bytes()
            return base64.b64encode(content).decode('utf-8')

        return ''


class JinjaSyncRender(SyncRender, JinjaBasicRender):
    def __init__(self, templates_dirs: list[Path]):
        SyncRender.__init__(self, templates_dirs)
        JinjaBasicRender.__init__(self, templates_dirs, enable_async=False)

    @override
    def __call__(self, template: str | Path, **kwargs) -> Result[str]:
        if isinstance(template, Path):
            if not template.exists() or not template.is_file():
                error = TemplateFileNotFound(template=template)
                return Result.from_error(error)
            template = str(template)

        try:
            template = self._templates_env.get_template(template)
            rendered = template.render(**kwargs)

        except exceptions.TemplateNotFound:
            error = TemplateFileNotFound(template=template)
            return Result.from_error(error)
        except exceptions.TemplateSyntaxError as e:
            error = TemplateSyntaxError(detail=e.message, filename=e.filename, lineno=e.lineno)
            return Result.from_error(error)

        return Result.from_ok(rendered)

    # noinspection PyProtectedMember
    @override
    def eval_string(self, source: str, **kwargs) -> Result[str]:
        try:
            tmpl = self._templates_env.compile_expression(source)
            context = tmpl._template.new_context(kwargs)
            for _ in tmpl._template.root_render_func(context):
                pass

        except exceptions.TemplateSyntaxError as e:
            error = TemplateSyntaxError(detail=e.message, filename=e.filename, lineno=e.lineno)
            return Result.from_error(error)

        return Result.from_ok(context.vars['result'])


class JinjaAsyncRender(AsyncRender, JinjaBasicRender):
    def __init__(self, templates_dirs: list[Path]):
        AsyncRender.__init__(self, templates_dirs)
        JinjaBasicRender.__init__(self, templates_dirs, enable_async=True)

    @override
    async def __call__(self, template: str | Path, **kwargs) -> Result[str]:
        if isinstance(template, Path):
            if not template.exists() or not template.is_file():
                error = TemplateFileNotFound(template=template)
                return Result.from_error(error)
            template = str(template)

        try:
            template = self._templates_env.get_template(template)
            rendered = await template.render_async(**kwargs)

        except exceptions.TemplateNotFound:
            error = TemplateFileNotFound(template=template)
            return Result.from_error(error)
        except exceptions.TemplateSyntaxError as e:
            error = TemplateSyntaxError(detail=e.message, filename=e.filename, lineno=e.lineno)
            return Result.from_error(error)

        return Result.from_ok(rendered)

    # noinspection PyProtectedMember
    @override
    async def eval_string(self, source: str, **kwargs) -> Result[str]:
        try:
            tmpl = self._templates_env.compile_expression(source)
            context = tmpl._template.new_context(kwargs)
            # noinspection PyTypeChecker
            async for _ in tmpl._template.root_render_func(context):
                pass

        except exceptions.TemplateSyntaxError as e:
            error = TemplateSyntaxError(detail=e.message, filename=e.filename, lineno=e.lineno)
            return Result.from_error(error)

        return Result.from_ok(context.vars['result'])
