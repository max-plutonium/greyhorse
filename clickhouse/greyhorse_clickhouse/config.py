from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import AnyHttpUrl, BaseSettings, validator


@dataclass
class EngineConfig:
    dsn: str
    echo: bool = False
    pool_min_size: int = 1
    pool_max_size: int = 8


class CHSettings(BaseSettings):
    CH_HOST: str = 'localhost'
    CH_PORT: int = 9000
    CH_USER: str = 'default'
    CH_PASSWORD: str = ''
    CH_PASSWORD_FILE: Path | None = None
    CH_DB: str
    CH_POOL_MIN_SIZE: int = 1
    CH_POOL_MAX_SIZE: int = 4

    CH_URI: AnyHttpUrl | None = None

    @validator('CH_URI', pre=True)
    def assemble_dsn(cls, v: str | None, values: dict[str, Any]) -> str:
        if isinstance(v, str):
            return v

        if 'CH_PASSWORD_FILE' in values:
            password_file = values.get('CH_PASSWORD_FILE')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['CH_PASSWORD'] = f.read().strip()

        return f'clickhouse://{values.get("CH_USER")}:{values.get("CH_PASSWORD")}' \
               f'@{values.get("CH_HOST")}:{values.get("CH_PORT")}/{values.get("CH_DB", "")}'

    class Config:
        case_sensitive = False
        env_file = '.env'
