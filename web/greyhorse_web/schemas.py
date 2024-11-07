from pydantic import BaseModel, IPvAnyAddress


class ClientInfo(BaseModel, frozen=True):
    ip: IPvAnyAddress
    port: int
    host: str
    agent: str | None = None
    referrer: str | None = None
    scheme: str | None = None
