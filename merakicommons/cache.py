from functools import wraps
from typing import Callable, Any, TypeVar
from weakref import WeakKeyDictionary
from threading import Lock

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


class _CacheSegment(object):
    def __init__(self) -> None:
        self._data = {}
        self._lock = Lock()

    def put(self, key: Any, value: Any, timeout: int = -1) -> None:
        with self._lock:
            self._data[key] = value

    def get(self, key: Any) -> Any:
        with self._lock:
            return self._data[key]

    def delete(self, key: Any) -> None:
        with self._lock:
            del self._data[key]

    def __len__(self) -> int:
        with self._lock:
            return self._data.__len__()

    def __getitem__(self, key: Any) -> Any:
        return self.get(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        self.put(key, value)

    def __delitem__(self, key: Any) -> None:
        self.delete(key)

    def __contains__(self, item: Any) -> bool:
        with self._lock:
            return self._data.__contains__(item)


# TODO: In development. Interface here for beginning integration.
class Cache(_CacheSegment):
    pass
