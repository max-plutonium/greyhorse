from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator
from pydantic.networks import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConf(BaseModel):
    dsn: AnyHttpUrl


class ElasticSearchSettings(BaseSettings):
    scheme: str = 'http'
    host: str = 'localhost'
    port: int = 9200
    user: str = 'elastic'
    password: str = 'elastic'
    password_file: Path | None = None

    dsn: AnyHttpUrl | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='es_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: AnyHttpUrl | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return AnyHttpUrl.build(
            scheme=values.get('scheme'),
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
        )
