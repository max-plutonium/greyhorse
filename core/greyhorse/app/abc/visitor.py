from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .controllers import Controller
    from .services import Service


class Visitor:
    def visit_controller(self, controller: 'Controller') -> None: ...

    def visit_service(self, service: 'Service') -> None: ...

    def start_component(self, component: object) -> None: ...

    def finish_component(self, component: object) -> None: ...

    def start_module(self, module: object) -> None: ...

    def finish_module(self, module: object) -> None: ...
