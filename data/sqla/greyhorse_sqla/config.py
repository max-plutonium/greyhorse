import enum
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, Field, field_validator
from pydantic.networks import MySQLDsn, PostgresDsn, Url, UrlConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict


class SqlEngineType(str, enum.Enum):
    SQLITE = 'SQLite'
    POSTGRES = 'PostgreSQL'
    MYSQL = 'MySQL'


SQLiteDsn = Annotated[
    Url, UrlConstraints(allowed_schemes=['file', 'sqlite']),
]


class EngineConf(BaseModel):
    type: SqlEngineType
    dsn: PostgresDsn | MySQLDsn | SQLiteDsn
    echo: bool = False
    schema: str = 'public'
    pool_min_size: int = Field(default=1, gt=0)
    pool_max_size: int = Field(default=4, gt=0)
    pool_expire_seconds: int = Field(default=60, gt=0)
    pool_timeout_seconds: int = Field(default=15, gt=0)
    begin_tx: bool = True
    force_rollback: bool = False


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
    dsn: SQLiteDsn

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='sqlite_')


class PgSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 5432
    user: str
    password: str = ''
    password_file: Path | None = None
    database: str = 'postgres'
    schema: str = 'public'
    pool_min_size: int = 1
    pool_max_size: int = 4
    pool_expire_seconds: int = 60
    pool_timeout_seconds: int = 15

    dsn: PostgresDsn | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='postgres_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: PostgresDsn | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return PostgresDsn.build(
            scheme='postgresql',
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
            path=f'/{values.get("database", "public")}',
        )


class MySqlSettings(BaseSettings):
    host: str = 'localhost'
    port: int = 3306
    user: str
    password: str = ''
    password_file: Path | None = None
    database: str = 'postgres'
    pool_min_size: int = 1
    pool_max_size: int = 4
    pool_expire_seconds: int = 60
    pool_timeout_seconds: int = 15

    dsn: MySQLDsn | None = None

    model_config = SettingsConfigDict(env_file='.env', case_sensitive=False, env_prefix='mysql_')

    @classmethod
    @field_validator('dsn', mode='before')
    def assemble_dsn(cls, v: PostgresDsn | None, values: dict[str, Any]) -> str:
        if v is not None:
            return v

        if 'password_file' in values:
            password_file = values.get('password_file')
            if isinstance(password_file, Path) and password_file.exists():
                with password_file.open() as f:
                    values['password'] = f.read().strip()

        return MySQLDsn.build(
            scheme='mysql',
            user=values.get('user'),
            password=values.get('password'),
            host=values.get('host'),
            port=str(values.get('port')),
            path=f'/{values.get("database", "")}',
        )
