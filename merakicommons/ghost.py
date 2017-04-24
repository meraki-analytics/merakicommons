from abc import ABC, abstractmethod
from sys import _getframe
from typing import Any, Callable


class Ghost(ABC):
    @staticmethod
    def load_on(method: Callable) -> Callable:
        method.__triggers_load = True
        return method

    def __init__(self) -> None:
        self.__loaded = False

    @abstractmethod
    def _load(self) -> None:
        pass

    def __getattr__(self, item: str) -> Any:
        default_error = AttributeError("'{cls}' object has no attribute '{item}'".format(cls=self.__class__.__name__, item=item))

        if self.__loaded:
            raise default_error

        # Check if we're inside one of self's methods
        calling_frame = _getframe(1)
        try:
            calling_self = calling_frame.f_locals["self"]
        except KeyError:
            # Caller didn't have a "self"
            raise default_error

        if calling_self is not self:
            raise default_error

        try:
            class_method = getattr(self.__class__, calling_frame.f_code.co_name)
        except AttributeError:
            # Class doesn't have an attribute with the caller's name
            raise default_error

        # Class had an attribute with caller's name. If it's a property, get the underlying method
        class_method = getattr(class_method, "fget", class_method)

        triggers_load = getattr(class_method, "_Ghost__triggers_load", False)
        if not triggers_load:
            raise default_error

        # Load and try to get attribute again
        self._load()
        self.__loaded = True
        return self.__getattribute__(item)
