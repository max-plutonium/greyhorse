from typing import Any, override

import pydantic
import tomlkit
import tomlkit.exceptions
import yaml
from greyhorse.error import Error, ErrorCase
from greyhorse.result import Ok, Result


class ParserError(Error):
    namespace = 'greyhorse_renders.parser'

    Yaml = ErrorCase(msg='Yaml error occurred: "{details}"', details=str)
    Toml = ErrorCase(msg='Toml error occurred: "{details}"', details=str)
    Validation = ErrorCase(msg='Validation error occurred: "{details}"', details=str)


class DictParser:
    def parse_yaml(self, content: str) -> Result[dict[str, Any], ParserError]:
        try:
            result = yaml.safe_load(content)

        except yaml.YAMLError as e:
            return ParserError.Yaml(details=str(e)).to_result()

        return Ok(result)

    def parse_yaml_list(self, content: str) -> Result[list[dict[str, Any]], ParserError]:
        try:
            result = list(yaml.safe_load_all(content))

        except yaml.YAMLError as e:
            return ParserError.Yaml(details=str(e)).to_result()

        return Ok(result)

    def parse_toml(self, content: str) -> Result[dict[str, Any], ParserError]:
        try:
            result = tomlkit.parse(content)

        except tomlkit.exceptions.ParseError as e:
            return ParserError.Toml(details=str(e)).to_result()

        return Ok(result.unwrap())


class PydanticParser[DocumentModel: pydantic.BaseModel](DictParser):
    __slots__ = ('_doc_schema',)

    def __init__(self, doc_schema: type[DocumentModel]) -> None:
        self._doc_schema = doc_schema

    @override
    def parse_yaml(self, content: str) -> Result[DocumentModel, ParserError]:
        if not (res := super().parse_yaml(content)):
            return res  # type: ignore

        try:
            doc = self._doc_schema(**res.unwrap())

        except pydantic.ValidationError as e:
            return ParserError.Validation(details=str(e)).to_result()

        return Ok(doc)

    @override
    def parse_yaml_list(self, content: str) -> Result[list[DocumentModel], ParserError]:
        if not (res := super().parse_yaml_list(content)):
            return res  # type: ignore

        try:
            docs = [self._doc_schema(**data) for data in res.unwrap()]

        except pydantic.ValidationError as e:
            return ParserError.Validation(details=str(e)).to_result()

        return Ok(docs)

    @override
    def parse_toml(self, content: str) -> Result[DocumentModel, ParserError]:
        if not (res := super().parse_toml(content)):
            return res  # type: ignore

        try:
            doc = self._doc_schema(**res.unwrap())

        except pydantic.ValidationError as e:
            return ParserError.Validation(details=str(e)).to_result()

        return Ok(doc)
