from greyhorse_core.app.base import ContainerResource, SessionResource
from greyhorse_sqla.factory import SqlaSyncEngineFactory, SqlaAsyncEngineFactory


class SqlaSyncResource(SessionResource):
    def __init__(self, factory: SqlaSyncEngineFactory):
        super().__init__()
        self._factory = factory
        self._sessions = list()

    def sync_startup(self, *args, **kwargs):
        if self.initialized:
            return

        for engine in self._factory.get_engines().values():
            engine.start()

        self._initialized = True

    def sync_shutdown(self, *args, **kwargs):
        if not self.initialized:
            return

        for engine in reversed(self._factory.get_engines().values()):
            engine.stop()

        self._initialized = False

    def sync_session_begin(self, *args, **kwargs):
        if not self.initialized:
            return

        for engine in self._factory.get_engines().values():
            session = engine.session()
            session.__enter__()
            self._sessions.append(session)

    def sync_session_finish(self, *args, **kwargs):
        if not self.initialized:
            return

        for session in reversed(self._sessions):
            session.__exit__(None, None, None)
        self._sessions.clear()

        for engine in reversed(self._factory.get_engines().values()):
            engine.teardown_session()

    def get_engine(self, name: str):
        return self._factory.get_engine(name)


class SqlaAsyncResource(SessionResource):
    def __init__(self, factory: SqlaAsyncEngineFactory):
        super().__init__()
        self._factory = factory
        self._sessions = list()

    async def startup(self, *args, **kwargs):
        if self.initialized:
            return

        for engine in self._factory.get_engines().values():
            await engine.start()

        self._initialized = True

    async def shutdown(self, *args, **kwargs):
        if not self.initialized:
            return

        for engine in reversed(self._factory.get_engines().values()):
            await engine.stop()

        self._initialized = False

    async def session_begin(self, *args, **kwargs):
        if not self.initialized:
            return

        for engine in self._factory.get_engines().values():
            session = engine.session()
            await session.__aenter__()
            self._sessions.append(session)

    async def session_finish(self, *args, **kwargs):
        if not self.initialized:
            return

        for session in reversed(self._sessions):
            await session.__aexit__(None, None, None)
        self._sessions.clear()

        for engine in reversed(self._factory.get_engines().values()):
            await engine.teardown_session()

    def get_engine(self, name: str):
        return self._factory.get_engine(name)
