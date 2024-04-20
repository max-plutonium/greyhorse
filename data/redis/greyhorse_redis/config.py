from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConf(BaseModel):
    dsn: RedisDsn
    timeout_seconds: int = Field(default=5, gt=0)
    connect_timeout_seconds: int = Field(default=5, gt=0)
    pool_max_connections: int = Field(default=4, gt=0)
    client_name: str = 'greyhorse-redis'


class RedisSettings(BaseSettings):
    scheme: str = 'redis'
    host: str = 'localhost'
    port: int = 6379
    user: str = 'redis'
    password: str = ''
    password_file: Path | None = None
    database: int = 0
    timeout_seconds: int = 5
    connect_timeout_seconds: int = 5
    pool_max_connections: int = 4
    client_name: str = 'greyhorse-redis'

    dsn: RedisDsn | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='redis_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: RedisDsn | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return RedisDsn.build(
            scheme=values.get('scheme'),
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
            path=f'/{values.get("database", "0")}',
        )
