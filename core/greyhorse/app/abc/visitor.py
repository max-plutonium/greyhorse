from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .component import Component
    from .controllers import Controller
    from .module import Module
    from .services import Service


class Visitor:
    def visit_controller(self, controller: 'Controller') -> None: ...

    def visit_service(self, service: 'Service') -> None: ...

    def start_component(self, component: 'Component') -> None: ...

    def finish_component(self, component: 'Component') -> None: ...

    def start_module(self, module: 'Module') -> None: ...

    def finish_module(self, module: 'Module') -> None: ...
