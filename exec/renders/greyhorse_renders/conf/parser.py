import pydantic
import tomlkit
import tomlkit.exceptions
import yaml

from greyhorse.result import Result
from ..errors import YamlError, SchemaValidationError, TomlError


class ConfParser[DocumentModel: pydantic.BaseModel]:
    def __init__(self, doc_schema: type[DocumentModel]):
        self._doc_schema = doc_schema

    def parse_yaml(self, content: str) -> Result[DocumentModel]:
        try:
            content = yaml.safe_load(content)
            doc = self._doc_schema(**content)

        except yaml.YAMLError as e:
            error = YamlError(exc=str(e))
            return Result.from_error(error)

        except pydantic.ValidationError as e:
            error = SchemaValidationError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(doc)

    def parse_toml(self, content: str) -> Result[DocumentModel]:
        try:
            content = tomlkit.parse(content)
            doc = self._doc_schema(**content.unwrap())

        except tomlkit.exceptions.ParseError as e:
            error = TomlError(exc=str(e))
            return Result.from_error(error)

        except pydantic.ValidationError as e:
            error = SchemaValidationError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(doc)
