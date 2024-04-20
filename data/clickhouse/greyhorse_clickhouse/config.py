from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import ClickHouseDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConf(BaseModel):
    dsn: ClickHouseDsn
    echo: bool = False
    pool_min_size: int = Field(default=1, gt=0)
    pool_max_size: int = Field(default=4, gt=0)


class ClickHouseSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 9000
    user: str = 'default'
    password: str = ''
    password_file: Path | None = None
    database: str = 'default'
    pool_min_size: int = 1
    pool_max_size: int = 4

    dsn: ClickHouseDsn | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='ch_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: ClickHouseDsn | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return ClickHouseDsn.build(
            scheme='clickhouse',
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
            path=f'/{values.get("database", "default")}',
        )
