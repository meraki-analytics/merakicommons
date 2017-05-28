from functools import wraps
from typing import Callable, Any, TypeVar
from weakref import WeakKeyDictionary

T = TypeVar("T")


def lazy(method: Callable[[Any], T]) -> property:
    values = WeakKeyDictionary()

    @wraps(method)
    def wrapper(self) -> T:
        try:
            return values[self]
        except KeyError as error:
            values[self] = method(self)
            return values[self]

    def _lazy_reset(self) -> None:
        try:
            del values[self]
        except KeyError:
            pass

    wrapper._lazy_reset = _lazy_reset

    return wrapper


def lazy_property(method: Callable[[Any], T]) -> property:
    return property(lazy(method))
