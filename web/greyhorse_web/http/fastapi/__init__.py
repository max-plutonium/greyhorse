from fastapi import APIRouter
from greyhorse.app.abc.collectors import MutCollector

FastAPIRouterCollector = MutCollector[str, APIRouter]
