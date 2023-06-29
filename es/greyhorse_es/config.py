from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, BaseSettings, validator


@dataclass
class EngineConfig:
    dsn: str


class ESSettings(BaseSettings):
    ES_HOST: str = 'localhost'
    ES_PORT: int = 9200
    ES_USER: str = 'elastic'
    ES_PASSWORD: str = 'elastic'
    ES_PASSWORD_FILE: Path | None = None

    ES_URI: AnyHttpUrl | None = None

    @validator('ES_URI', pre=True)
    def assemble_dsn(cls, v: str | None, values: dict[str, Any]) -> str:
        if isinstance(v, str):
            return v

        if 'ES_PASSWORD_FILE' in values:
            password_file = values.get('ES_PASSWORD_FILE')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['ES_PASSWORD'] = f.read().strip()

        return f'http://{values.get("ES_USER")}:{values.get("ES_PASSWORD")}' \
               f'@{values.get("ES_HOST")}:{values.get("ES_PORT")}/'

    class Config:
        case_sensitive = False
        env_file = '.env'
