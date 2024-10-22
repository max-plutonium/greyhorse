import base64
from pathlib import Path
from typing import Any, cast, override

import yaml
from greyhorse.result import Ok, Result
from greyhorse.utils import json
from jinja2 import Environment, FileSystemLoader, exceptions

from ..abc import AsyncRender, RenderError, SyncRender


class JinjaBasicRender:
    def __init__(self, templates_dirs: list[Path], enable_async: bool = False) -> None:
        self._templates_env = Environment(
            loader=FileSystemLoader(templates_dirs), enable_async=enable_async
        )
        self._templates_env.filters['b64encode'] = lambda s: base64.b64encode(
            s.encode('utf-8')
        ).decode('utf-8')
        self._templates_env.filters['b64decode'] = lambda s: base64.b64decode(
            s.encode('utf-8')
        ).decode('utf-8')
        self._templates_env.filters['toYaml'] = self.to_yaml
        self._templates_env.filters['toJson'] = self.to_json
        self._templates_env.globals['readBinary'] = self.read_binary

    @staticmethod
    def to_yaml(data: dict, indent: int = 0) -> str:
        dump = yaml.safe_dump(data)
        res = [' ' * indent + line for line in dump.splitlines()]
        return '\n'.join(res)

    @staticmethod
    def to_json(data: dict, indent: int = 0) -> str:
        dump = json.dumps(data, use_indent=True)
        res = [' ' * indent + line for line in dump.splitlines()]
        return '\n'.join(res)

    def read_binary(self, path: str) -> str:
        loader = cast(FileSystemLoader, self._templates_env.loader)

        for template_dir in loader.searchpath:
            target_path = Path(template_dir) / path
            if not target_path.is_file():
                continue
            content = target_path.read_bytes()
            return base64.b64encode(content).decode('utf-8')

        return ''


class JinjaSyncRender(SyncRender, JinjaBasicRender):
    def __init__(self, templates_dirs: list[Path]) -> None:
        SyncRender.__init__(self, templates_dirs)
        JinjaBasicRender.__init__(self, templates_dirs, enable_async=False)

    @override
    def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]:
        if isinstance(template, Path):
            if not template.exists() or not template.is_file():
                return RenderError.TemplateFileNotFound(file=template).to_result()

            template = str(template)

        try:
            template = self._templates_env.get_template(template)
            rendered = template.render(**kwargs)

        except exceptions.TemplateNotFound:
            return RenderError.TemplateFileNotFound(file=template).to_result()
        except exceptions.TemplateSyntaxError as e:
            return RenderError.TemplateSyntaxError(
                filename=e.filename, lineno=e.lineno, details=e.message
            ).to_result()

        return Ok(rendered)

    @override
    def eval_string(self, source: str, **kwargs: dict[str, Any]) -> Result[Any, RenderError]:
        try:
            tmpl = self._templates_env.compile_expression(source)
            context = tmpl._template.new_context(kwargs)  # noqa: SLF001
            for _ in tmpl._template.root_render_func(context):  # noqa: SLF001
                pass

        except exceptions.TemplateSyntaxError as e:
            return RenderError.TemplateSyntaxError(
                filename=e.filename, lineno=e.lineno, details=e.message
            ).to_result()

        return Ok(context.vars['result'])


class JinjaAsyncRender(AsyncRender, JinjaBasicRender):
    def __init__(self, templates_dirs: list[Path]) -> None:
        AsyncRender.__init__(self, templates_dirs)
        JinjaBasicRender.__init__(self, templates_dirs, enable_async=True)

    @override
    async def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]:
        if isinstance(template, Path):
            if not template.exists() or not template.is_file():
                return RenderError.TemplateFileNotFound(file=template).to_result()

            template = str(template)

        try:
            template = self._templates_env.get_template(template)
            rendered = await template.render_async(**kwargs)

        except exceptions.TemplateNotFound:
            return RenderError.TemplateFileNotFound(file=template).to_result()
        except exceptions.TemplateSyntaxError as e:
            return RenderError.TemplateSyntaxError(
                filename=e.filename, lineno=e.lineno, details=e.message
            ).to_result()

        return Ok(rendered)

    @override
    async def eval_string(
        self, source: str, **kwargs: dict[str, Any]
    ) -> Result[Any, RenderError]:
        try:
            tmpl = self._templates_env.compile_expression(source)
            context = tmpl._template.new_context(kwargs)  # noqa: SLF001
            async for _ in tmpl._template.root_render_func(context):  # noqa: SLF001
                pass

        except exceptions.TemplateSyntaxError as e:
            return RenderError.TemplateSyntaxError(
                filename=e.filename, lineno=e.lineno, details=e.message
            ).to_result()

        return Ok(context.vars['result'])
