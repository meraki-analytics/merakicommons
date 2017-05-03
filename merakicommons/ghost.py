from abc import ABC, abstractmethod
from sys import _getframe
from typing import Any, Callable


class GhostAttributeError(AttributeError):
    pass

class Ghost(ABC):
    @staticmethod
    def load_on(method: Callable) -> Callable:
        method.__triggers_load = True
        return method

    @abstractmethod
    def _load(self, attribute: str) -> None:
        pass

    def __getattribute__(self, attr):
        try:
            return super().__getattribute__(attr)
        except AttributeError as error:
            return self.__custom_getattr__(attr, error)

    def _search_traceback_for_ghost_property(self, tb):
        # Back up thru the stack trace to see if any method with @Ghost.load_on is in the stack that triggered this call
        while tb is not None:
            frame = tb.tb_frame
            while frame is not None:
                if "self" in frame.f_locals and isinstance(frame.f_locals["self"], Ghost):
                    calling_method = getattr(self.__class__, frame.f_code.co_name, None)
                    if isinstance(calling_method, property) and getattr(calling_method.fget, "_Ghost__triggers_load", False):
                        return calling_method.fget
                    elif getattr(calling_method, "_Ghost__triggers_load", False):
                        return calling_method
                frame = frame.f_back
            tb = tb.tb_next

    def __custom_getattr__(self, attr, error):
        #_, _, tb = sys.exc_info()  This seems to work if we don't want to pass in the error
        tb = error.__traceback__
        calling_method = self._search_traceback_for_ghost_property(tb)
        if calling_method is not None:
            self._load(calling_method.__name__)
        return super().__getattribute__(attr)
