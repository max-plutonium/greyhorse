from dataclasses import dataclass

import asynch

from greyhorse.app.entities.providers import AsyncContextProvider


@dataclass(slots=True, frozen=True)
class ClickHouseContext:
    name: str
    connection: asynch.connection.Cursor


class ClickHouseContextProvider(AsyncContextProvider[ClickHouseContext]):
    pass
