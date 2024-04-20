from dataclasses import dataclass

import elasticsearch

from greyhorse.app.entities.providers import AsyncContextProvider


@dataclass(slots=True, frozen=True)
class ElasticSearchContext:
    name: str
    connection: elasticsearch.AsyncElasticsearch


class ElasticSearchContextProvider(AsyncContextProvider[ElasticSearchContext]):
    pass
