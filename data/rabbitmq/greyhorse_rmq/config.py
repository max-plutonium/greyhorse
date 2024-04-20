from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import AmqpDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class EngineConf(BaseModel):
    dsn: AmqpDsn
    virtualhost: str = '/'
    timeout_seconds: int = Field(default=5, gt=0)
    pool_max_connections: int = Field(default=4, gt=0)
    pool_max_channels_per_connection: int = Field(default=100, gt=0)


class RmqSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 9200
    user: str = 'elastic'
    password: str = 'elastic'
    password_file: Path | None = None
    virtualhost: str = '/'
    timeout_seconds: int = 5
    pool_max_connections: int = 4
    pool_max_channels_per_connection: int = 100

    dsn: AmqpDsn | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='rmq_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: AmqpDsn | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return AmqpDsn.build(
            scheme='amqp',
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
        )
