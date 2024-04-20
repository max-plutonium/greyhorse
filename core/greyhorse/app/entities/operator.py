from typing import Any, Callable

from ..utils.registry import ReadonlyRegistry

type Operator = Any
type OperatorKey = type
type OperatorFactoryFn = Callable[[], Operator]
type OperatorFactoryRegistry = ReadonlyRegistry[OperatorKey, OperatorFactoryFn]
