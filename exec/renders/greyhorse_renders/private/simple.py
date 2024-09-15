from pathlib import Path
from typing import override

from greyhorse.result import Result, Ok
from ..abc import AsyncRender, SyncRender, RenderError


class SimpleSyncRender(SyncRender):
    def __init__(self, templates_dirs: list[Path]):
        super().__init__(templates_dirs)

    @override
    def __call__(self, template: str | Path, **kwargs) -> Result[str, RenderError]:
        if isinstance(template, str):
            template = Path(template)

        if not template.exists():
            for template_dir in self.templates_dirs:
                candidate = template_dir / template
                if candidate.exists():
                    template = candidate
                    break

        if not template.exists() or not template.is_file():
            return RenderError.TemplateFileNotFound(file=template).to_result()

        content = template.read_text('utf-8')
        return Ok(content)


class SimpleAsyncRender(AsyncRender):
    def __init__(self, templates_dirs: list[Path]):
        super().__init__(templates_dirs)

    @override
    async def __call__(self, template: str | Path, **kwargs) -> Result[str, RenderError]:
        if isinstance(template, str):
            template = Path(template)

        if not template.exists():
            for template_dir in self.templates_dirs:
                candidate = template_dir / template
                if candidate.exists():
                    template = candidate
                    break

        if not template.exists() or not template.is_file():
            return RenderError.TemplateFileNotFound(file=template).to_result()

        content = template.read_text('utf-8')
        return Ok(content)
