from dependency_injector.containers import Container

from . import base
from .module import Module
from .service import Service
from ..utils.invoke import invoke_async, invoke_sync


# noinspection PyProtectedMember
class BindVisitor(base.Visitor):
    def visit_service(self, instance: Service):
        for name, provider in instance._resource_factories.items():
            res_instance = provider()
            if isinstance(res_instance, Container) and hasattr(res_instance, 'instance'):
                if issubclass(res_instance.instance.provides, base.HasContainer):
                    res_instance = res_instance.instance(container=res_instance)
                else:
                    res_instance = res_instance.instance()
            if isinstance(res_instance, base.Resource):
                instance._resources[name] = res_instance

        for r in instance.resources:
            invoke_sync(r.accept, self)

    def visit_module(self, instance: Module):
        for name, provider in instance._resource_factories.items():
            res_instance = provider()
            if isinstance(res_instance, Container) and hasattr(res_instance, 'instance'):
                if issubclass(res_instance.instance.provides, base.HasContainer):
                    res_instance = res_instance.instance(container=res_instance)
                else:
                    res_instance = res_instance.instance()
            if isinstance(res_instance, base.Resource):
                instance._resources[name] = res_instance

        for name, provider in instance._service_factories.items():
            svc_instance = provider()
            if isinstance(svc_instance, Container) and hasattr(svc_instance, 'instance'):
                if issubclass(svc_instance.instance.provides, base.HasContainer):
                    svc_instance = svc_instance.instance(container=svc_instance)
                else:
                    svc_instance = svc_instance.instance()
            if isinstance(svc_instance, base.Service):
                instance._services[name] = svc_instance

        for name, provider in instance._module_factories.items():
            mod_instance = provider()
            if isinstance(mod_instance, Container) and hasattr(mod_instance, 'instance'):
                if issubclass(mod_instance.instance.provides, base.HasContainer):
                    mod_instance = mod_instance.instance(container=mod_instance)
                else:
                    mod_instance = mod_instance.instance()
            if isinstance(mod_instance, base.Module):
                instance._modules[name] = mod_instance

        for r in instance.resources:
            invoke_sync(r.accept, self)
        for s in instance.services:
            invoke_sync(s.accept, self)
        for m in instance.modules:
            invoke_sync(m.accept, self)


# noinspection PyProtectedMember
class StartVisitor(base.Visitor):
    def __init__(
        self, application: base.Application,
        mod: base.Module | None = None,
        srv: base.Service | None = None,
    ):
        self._app = application
        self._module = mod
        self._service = srv

    async def visit_resource(self, instance: base.Resource):
        if instance._active:
            return
        await invoke_async(instance.create, self._app, self._module, self._service)
        instance._active = True

    async def visit_service(self, instance: Service):
        if instance._active:
            return

        for r in instance.resources:
            await invoke_async(r.accept, StartVisitor(self._app, self._module, instance))

        await invoke_async(instance.start, self._app, self._module)
        instance._active = True

    async def visit_module(self, instance: Module):
        visitor = StartVisitor(self._app, instance)

        for r in instance.resources:
            await invoke_async(r.accept, visitor)
        for s in instance.services:
            await invoke_async(s.accept, visitor)
        for m in instance.modules:
            await invoke_async(m.accept, visitor)

        await invoke_async(instance.initialize, self._app, instance)


# noinspection PyProtectedMember
class StopVisitor(base.Visitor):
    def __init__(
        self, application: base.Application,
        mod: base.Module | None = None,
        srv: base.Service | None = None,
    ):
        self._app = application
        self._module = mod
        self._service = srv

    async def visit_resource(self, instance: base.Resource):
        if not instance._active:
            return
        await invoke_async(instance.destroy, self._app, self._module, self._service)
        instance._active = False

    async def visit_service(self, instance: Service):
        if not instance._active:
            return

        for r in instance.resources:
            await invoke_async(r.accept, StopVisitor(self._app, self._module, instance))

        await invoke_async(instance.stop, self._app, self._module)
        instance._active = False

    async def visit_module(self, instance: Module):
        visitor = StopVisitor(self._app, instance)

        await invoke_async(instance.finalize, self._app, instance)

        for m in instance.modules:
            await invoke_async(m.accept, visitor)
        for s in instance.services:
            await invoke_async(s.accept, visitor)
        for r in instance.resources:
            await invoke_async(r.accept, visitor)


# noinspection PyProtectedMember
class AcquireVisitor(base.Visitor):
    def __init__(
        self, application: base.Application,
        mod: base.Module | None = None,
        srv: base.Service | None = None,
    ):
        self._app = application
        self._module = mod
        self._service = srv

    async def visit_resource(self, instance: base.Resource):
        if not instance._active:
            return

        await invoke_async(instance.acquire, self._app, self._module, self._service)

    async def visit_service(self, instance: Service):
        if not instance._active:
            return

        for r in instance.resources:
            await invoke_async(r.accept, AcquireVisitor(self._app, self._module, instance))

    async def visit_module(self, instance: Module):
        visitor = AcquireVisitor(self._app, instance)

        for r in instance.resources:
            await invoke_async(r.accept, visitor)
        for s in instance.services:
            await invoke_async(s.accept, visitor)
        for m in instance.modules:
            await invoke_async(m.accept, visitor)


# noinspection PyProtectedMember
class ReleaseVisitor(base.Visitor):
    def __init__(
        self, application: base.Application,
        mod: base.Module | None = None,
        srv: base.Service | None = None,
    ):
        self._app = application
        self._module = mod
        self._service = srv

    async def visit_resource(self, instance: base.Resource):
        if not instance._active:
            return

        await invoke_async(instance.release, self._app, self._module, self._service)

    async def visit_service(self, instance: Service):
        if not instance._active:
            return

        for r in instance.resources:
            await invoke_async(r.accept, ReleaseVisitor(self._app, self._module, instance))

    async def visit_module(self, instance: Module):
        visitor = ReleaseVisitor(self._app, instance)

        for m in instance.modules:
            await invoke_async(m.accept, visitor)
        for s in instance.services:
            await invoke_async(s.accept, visitor)
        for r in instance.resources:
            await invoke_async(r.accept, visitor)
