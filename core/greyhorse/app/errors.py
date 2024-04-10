from ..result import Error, ErrorKwargsMixin


class GreyhorseError(ErrorKwargsMixin, Error):
    app = 'greyhorse'


class ModuleLoadError(GreyhorseError):
    type = 'app.builder.load-error'


class ModuleUnloadError(GreyhorseError):
    type = 'app.builder.unload-error'


class ModuleValidationError(GreyhorseError):
    type = 'app.builder.validation-error'


class InvalidModuleConfError(GreyhorseError):
    type = 'app.builder.invalid-module-conf'


class ControllerCreationError(GreyhorseError):
    type = 'app.builder.ctrl-error'


class CtrlFactoryNotFoundError(GreyhorseError):
    type = 'app.builder.ctrl-not-found'


class ServiceCreationError(GreyhorseError):
    type = 'app.builder.service-error'


class ServiceFactoryNotFoundError(GreyhorseError):
    type = 'app.builder.service-not-found'


class ModuleCreationError(GreyhorseError):
    type = 'app.builder.module-error'


class AppNotLoadedError(RuntimeError):
    pass


class OpPolicyViolation(GreyhorseError):
    type = 'app.entities.operator-policy-violation'


class NoOpFoundForPattern(GreyhorseError):
    type = 'app.entities.operator-pattern-violation'


class ProvPolicyViolation(GreyhorseError):
    type = 'app.entities.provider-policy-violation'


class NoProvFoundForPattern(GreyhorseError):
    type = 'app.entities.provider-pattern-violation'


class ProvClaimPolicyViolation(GreyhorseError):
    type = 'app.entities.prov-claim-policy-violation'


class DependencyCreationFailure(GreyhorseError):
    type = 'app.entities.dep-failure'
