from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import AmqpDsn, BaseSettings, validator


@dataclass
class EngineConfig:
    dsn: str
    virtualhost: str = '/'
    timeout_seconds: int = 5
    pool_max_connections: int = 4
    pool_max_channels_per_connection: int = 100


class RmqSettings(BaseSettings):
    RMQ_HOST: str = 'localhost'
    RMQ_PORT: int = 5672
    RMQ_USER: str = 'guest'
    RMQ_PASSWORD: str = 'guest'
    RMQ_PASSWORD_FILE: Path | None = None
    RMQ_VIRTUALHOST: str = '/'
    RMQ_TIMEOUT_SECONDS: int = 5
    RMQ_POOL_MAX_CONNECTIONS: int = 4
    RMQ_POOL_MAX_CHANNELS_PER_CONNECTION: int = 100

    RMQ_URI: AmqpDsn | None = None

    @validator('RMQ_URI', pre=True)
    def assemble_dsn(cls, v: str | None, values: dict[str, Any]) -> str:
        if isinstance(v, str):
            return v

        if 'RMQ_PASSWORD_FILE' in values:
            password_file = values.get('RMQ_PASSWORD_FILE')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['RMQ_PASSWORD'] = f.read().strip()

        return AmqpDsn.build(
            scheme='amqp',
            user=values.get('RMQ_USER'),
            password=values.get('RMQ_PASSWORD'),
            host=values.get('RMQ_HOST'),
            port=str(values.get('RMQ_PORT')),
        )

    class Config:
        case_sensitive = False
        env_file = '.env'
