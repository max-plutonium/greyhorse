import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import validator, BaseSettings, PostgresDsn


@dataclass
class EngineConfig:
    dsn: str
    echo: bool = False
    pool_min_size: int = 1
    pool_max_size: int = 8
    pool_expire_seconds: int = 60
    pool_timeout_seconds: int = 15


class SqlEngineType(str, enum.Enum):
    SQLITE = 'SQLite'
    POSTGRES = 'PostgreSQL'
    MYSQL = 'MySQL'


# Recommended naming convention used by Alembic, as various different database
# providers will autogenerate vastly different names making migrations more
# difficult. See: http://alembic.zzzcomputing.com/en/latest/naming.html
NAMING_CONVENTION = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s'
}


class SqliteSettings(BaseSettings):
    DATABASE_URI: str

    class Config:
        case_sensitive = False
        env_file = '.env'


class PgSettings(BaseSettings):
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ''
    POSTGRES_PASSWORD_FILE: Path | None = None
    POSTGRES_DB: str
    POSTGRES_SCHEMA: str | None = None

    DATABASE_URI: PostgresDsn | None = None

    @validator('DATABASE_URI', pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, Any]) -> str:
        if isinstance(v, str):
            return v

        if 'POSTGRES_PASSWORD_FILE' in values:
            password_file = values.get('POSTGRES_PASSWORD_FILE')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['POSTGRES_PASSWORD'] = f.read().strip()

        return PostgresDsn.build(
            scheme='postgresql',
            user=values.get('POSTGRES_USER'),
            password=values.get('POSTGRES_PASSWORD'),
            host=values.get('POSTGRES_HOST'),
            port=str(values.get('POSTGRES_PORT')),
            path=f'/{values.get("POSTGRES_DB") or ""}',
        )

    class Config:
        case_sensitive = False
        env_file = '.env'


class MySqlSettings(BaseSettings):
    MYSQL_HOST: str = 'localhost'
    MYSQL_PORT: int = 3306
    MYSQL_USER: str
    MYSQL_PASSWORD: str = ''
    MYSQL_PASSWORD_FILE: Path | None = None
    MYSQL_DB: str

    DATABASE_URI: str | None = None

    @validator('DATABASE_URI', pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, Any]) -> str:
        if isinstance(v, str):
            return v

        if 'MYSQL_PASSWORD_FILE' in values:
            password_file = values.get('MYSQL_PASSWORD_FILE')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['MYSQL_PASSWORD'] = f.read().strip()

        return f'mysql://{values.get("MYSQL_USER")}:{values.get("MYSQL_PASSWORD")}' \
               f'@{values.get("MYSQL_HOST")}:{values.get("MYSQL_PORT")}/{values.get("MYSQL_DB")}'

    class Config:
        case_sensitive = False
        env_file = '.env'
