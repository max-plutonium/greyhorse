from typing import override

import pydantic
import tomlkit
import tomlkit.exceptions
import yaml

from greyhorse.result import Result
from ..errors import YamlError, SchemaValidationError, TomlError


class DictParser:
    def parse_yaml(self, content: str) -> Result[dict]:
        try:
            result = yaml.safe_load(content)

        except yaml.YAMLError as e:
            error = YamlError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(result)

    def parse_yaml_list(self, content: str) -> Result[list[dict]]:
        try:
            result = list(yaml.safe_load_all(content))

        except yaml.YAMLError as e:
            error = YamlError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(result)

    def parse_toml(self, content: str) -> Result[dict]:
        try:
            result = tomlkit.parse(content)

        except tomlkit.exceptions.ParseError as e:
            error = TomlError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(result.unwrap())


class PydanticParser[DocumentModel: pydantic.BaseModel](DictParser):
    def __init__(self, doc_schema: type[DocumentModel]):
        self._doc_schema = doc_schema

    @override
    def parse_yaml(self, content: str) -> Result[DocumentModel]:
        res = super().parse_yaml(content)
        if not res.success:
            return Result.from_errors(res.errors)

        try:
            doc = self._doc_schema(**res.result)

        except pydantic.ValidationError as e:
            error = SchemaValidationError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(doc)

    @override
    def parse_yaml_list(self, content: str) -> Result[list[DocumentModel]]:
        res = super().parse_yaml_list(content)
        if not res.success:
            return Result.from_errors(res.errors)

        docs = []

        try:
            for data in res.result:
                docs.append(self._doc_schema(**data))

        except pydantic.ValidationError as e:
            error = SchemaValidationError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(docs)

    @override
    def parse_toml(self, content: str) -> Result[DocumentModel]:
        res = super().parse_toml(content)
        if not res.success:
            return Result.from_errors(res.errors)

        try:
            doc = self._doc_schema(**res.result)

        except pydantic.ValidationError as e:
            error = SchemaValidationError(exc=str(e))
            return Result.from_error(error)

        return Result.from_ok(doc)
