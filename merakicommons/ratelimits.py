from typing import Callable
from abc import ABC, abstractmethod
from contextlib import contextmanager, AbstractContextManager
from threading import Lock, Timer


class RateLimiter(ABC):
    @property
    @abstractmethod
    def permits_issued(self) -> int:
        pass

    @abstractmethod
    def reset_permits_issued(self) -> None:
        pass

    @abstractmethod
    def acquire(self) -> AbstractContextManager:
        pass

    def limit(self, method: Callable) -> Callable:
        def limited(*args, **kwargs):
            with self.acquire():
                return method(*args, **kwargs)
        return limited


class FixedWindowRateLimiter(RateLimiter):
    def __init__(self, window_seconds: int, window_permits: int) -> None:
        self._window_seconds = window_seconds
        self._window_permits = window_permits

        self._total_permits_issued = 0
        self._total_permits_issued_lock = Lock()

        self._permitter = Lock()
        self._permits = window_permits
        self._permits_lock = Lock()

        self._currently_processing = 0
        self._currently_processing_lock = Lock()

        self._resetter = None
        self._resetter_lock = Lock()

    @property
    def permits_issued(self) -> int:
        with self._total_permits_issued_lock:
            return self._total_permits_issued

    @contextmanager
    def acquire(self) -> AbstractContextManager:
        # Grab the permit lock and decrement remaining permits. If this leaves it at 0, don't release the permit lock. It will be released by the resetter.
        self._permitter.acquire()
        with self._permits_lock:
            self._permits -= 1
            if self._permits > 0:
                self._permitter.release()

        # Increment total count
        with self._total_permits_issued_lock:
            self._total_permits_issued += 1

        # Increment current count
        with self._currently_processing_lock:
            self._currently_processing += 1

        # Yield to processing
        yield

        # Decrement current count
        with self._currently_processing_lock:
            self._currently_processing -= 1

        # The fixed window starts after processing the first permit ends. The presence of a resetter indicates whether we're in a fixed window already, or need to start one.
        with self._resetter_lock:
            if not self._resetter:
                self._resetter = Timer(self._window_seconds, self._reset)
                self._resetter.daemon = True
                self._resetter.start()

    def _reset(self):
        with self._resetter_lock:
            self._resetter = None

        with self._permits_lock:
            with self._currently_processing_lock:
                self._permits = self._window_permits - self._currently_processing
                try:
                    self._permitter.release()
                except RuntimeError:
                    # Wasn't out of permits
                    pass

    def reset_permits_issued(self) -> None:
        with self._total_permits_issued_lock:
            self._total_permits_issued = 0
