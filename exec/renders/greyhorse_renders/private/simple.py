from pathlib import Path
from typing import Any, override

from greyhorse.result import Ok, Result

from ..abc import AsyncRender, RenderError, SyncRender


class SimpleSyncRender(SyncRender):
    def __init__(self, templates_dirs: list[Path]) -> None:
        super().__init__(templates_dirs)

    @override
    def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]:
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
    def __init__(self, templates_dirs: list[Path]) -> None:
        super().__init__(templates_dirs)

    @override
    async def __call__(
        self, template: str | Path, **kwargs: dict[str, Any]
    ) -> Result[str, RenderError]:
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
