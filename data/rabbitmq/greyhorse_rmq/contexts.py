from dataclasses import dataclass

import aio_pika

from greyhorse.app.entities.providers import AsyncContextProvider


@dataclass(slots=True, frozen=True)
class RmqAsyncContext:
    name: str
    connection: aio_pika.RobustChannel


class RmqAsyncContextProvider(AsyncContextProvider[RmqAsyncContext]):
    pass
