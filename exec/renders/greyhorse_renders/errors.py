from greyhorse.result import ErrorKwargsMixin, Error


class RenderError(ErrorKwargsMixin, Error):
    app = 'greyhorse-renders'


class YamlError(RenderError):
    type = 'yaml-error'


class TomlError(RenderError):
    type = 'toml-error'


class SchemaValidationError(RenderError):
    type = 'validation-error'
