from typing import Any, Callable

from greyhorse.result import Result
from ..utils.registry import ReadonlyRegistry

type Operator = Any
type OperatorKey = type
type OperatorFactoryFn = Callable[[...], Result[Operator]]
type OperatorFactoryRegistry = ReadonlyRegistry[OperatorKey, OperatorFactoryFn]
