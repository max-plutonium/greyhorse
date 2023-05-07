from typing import Dict, List, Mapping, Optional

from dependency_injector.containers import Container

from . import base


class Service(base.Service):
    def __init__(self, name: str | None = None,
                 resources: Mapping[str, base.ResourceFactory] | None = None):
        super(Service, self).__init__()
        self._name = name
        self._resources: Dict[str, base.Resource] = dict()

        if resources:
            for name, provider in resources.items():
                instance = provider()
                if isinstance(instance, Container) and hasattr(instance, 'instance'):
                    instance = instance.instance()
                if isinstance(instance, base.Resource):
                    self._resources[name] = instance

    @property
    def name(self) -> str:
        return self._name or ''

    @property
    def resources(self) -> list[base.Resource]:
        return list(self._resources.values())

    def get_resource(self, name) -> base.Resource | None:
        return self._resources.get(name)

    def sync_startup(self, application, module, *args, **kwargs):
        super().sync_startup(application=application, module=module, service=self, *args, **kwargs)

        for resource in self._resources.values():
            if hasattr(resource, 'create_engine'):
                resource.create_engine()

        for r in self.resources:
            r.sync_startup(application=application, module=module, service=self, *args, **kwargs)

    def sync_shutdown(self, application, module, *args, **kwargs):
        for r in self.resources:
            r.sync_shutdown(application=application, module=module, service=self, *args, **kwargs)

        super().sync_shutdown(application=application, module=module, service=self, *args, **kwargs)

    async def startup(self, application, module, *args, **kwargs):
        await super().startup(application=application, module=module, service=self, *args, **kwargs)

        for resource in self._resources.values():
            if hasattr(resource, 'get_engine'):
                resource.get_engine()

        for r in self.resources:
            await r.startup(application=application, module=module, service=self, *args, **kwargs)

    async def shutdown(self, application, module, *args, **kwargs):
        for r in self.resources:
            await r.shutdown(application=application, module=module, service=self, *args, **kwargs)

        await super().shutdown(application=application, module=module, service=self, *args, **kwargs)


class SessionService(Service, base.SessionResource):
    def sync_session_begin(self, application, module, *args, **kwargs):
        super().sync_session_begin(application=application, module=module, service=self, *args, **kwargs)

        for r in self.resources:
            if not isinstance(r, base.SessionResource):
                continue
            r.sync_session_begin(application=application, module=module, service=self, *args, **kwargs)

    def sync_session_finish(self, application, module, *args, **kwargs):
        for r in self.resources:
            if not isinstance(r, base.SessionResource):
                continue
            r.sync_session_finish(application=application, module=module, service=self, *args, **kwargs)

        super().sync_session_finish(application=application, module=module, service=self, *args, **kwargs)

    async def session_begin(self, application, module, *args, **kwargs):
        await super().session_begin(application=application, module=module, service=self, *args, **kwargs)

        for r in self.resources:
            if not isinstance(r, base.SessionResource):
                continue
            await r.session_begin(application=application, module=module, service=self, *args, **kwargs)

    async def session_finish(self, application, module, *args, **kwargs):
        for r in self.resources:
            if not isinstance(r, base.SessionResource):
                continue
            await r.session_finish(application=application, module=module, service=self, *args, **kwargs)

        await super().session_finish(application=application, module=module, service=self, *args, **kwargs)
