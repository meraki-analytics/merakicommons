from typing import Callable
from time import sleep
from math import ceil
from abc import ABC, abstractmethod
from contextlib import contextmanager, _GeneratorContextManager
from threading import Lock, Timer, Thread


class RateLimiter(ABC):
    @property
    @abstractmethod
    def permits_issued(self) -> int:
        pass

    @abstractmethod
    def reset_permits_issued(self) -> None:
        pass

    @abstractmethod
    def acquire(self) -> _GeneratorContextManager:
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

    @contextmanager
    def acquire(self) -> _GeneratorContextManager:
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
        error = None
        try:
            yield
        except Exception as e:
            error = e

        # Decrement current count
        with self._currently_processing_lock:
            self._currently_processing -= 1

        # The fixed window starts after processing the first permit ends. The presence of a resetter indicates whether we're in a fixed window already, or need to start one.
        with self._resetter_lock:
            if not self._resetter:
                self._resetter = Timer(self._window_seconds, self._reset)
                self._resetter.daemon = True
                self._resetter.start()

        if error:
            raise error

    def _reset(self):
        with self._resetter_lock:
            self._resetter = None

        with self._permits_lock:
            with self._currently_processing_lock:
                self._permits = self._window_permits - self._currently_processing
                try:
                    self._permitter.release()
                except RuntimeError:
                    # Wasn't waiting on any acquire
                    pass

    @property
    def permits_issued(self) -> int:
        with self._total_permits_issued_lock:
            return self._total_permits_issued

    def reset_permits_issued(self) -> None:
        with self._total_permits_issued_lock:
            self._total_permits_issued = 0


class TokenBucketRateLimiter(RateLimiter):
    def __init__(self, epoch_seconds: int, epoch_permits: int, max_burst: int, token_update_frequency: float) -> None:
        if max_burst < 1 or max_burst > epoch_permits:
            raise ValueError("Max burst must be >= 1 and <= epoch permits!")

        if token_update_frequency <= 0 or token_update_frequency > epoch_seconds:
            raise ValueError("Token update frequency must be > 0 and <= epoch seconds!")

        self._epoch_seconds = epoch_seconds
        self._epoch_permits = epoch_permits

        self._permitter = Lock()
        self._token_limit = max_burst
        self._tokens = max_burst
        self._tokens_lock = Lock()

        self._token_update = token_update_frequency

        self._token_provider = None
        self._token_provider_lock = Lock()

        self._total_permits_issued = 0
        self._total_permits_issued_lock = Lock()

    @contextmanager
    def acquire(self) -> _GeneratorContextManager:
        # Grab the permit lock and decrement remaining permits. If this leaves it at 0, don't release the permit lock. It will be released by the resetter.
        self._permitter.acquire()
        with self._tokens_lock:
            self._tokens -= 1
            if self._tokens > 0:
                self._permitter.release()

        # Increment total count
        with self._total_permits_issued_lock:
            self._total_permits_issued += 1

        # Yield to processing
        error = None
        try:
            yield
        except Exception as e:
            error = e

        # We don't want a thread sitting around dumping tokens into a filled bucket during downtimes. We construct one when needed and it cleans itself up if the bucket is full for an entire epoch.
        with self._token_provider_lock:
            if not self._token_provider:
                self._token_provider = Thread(target=self._provide_tokens)
                self._token_provider.daemon = True
                self._token_provider.start()

        if error:
            raise error

    def _provide_tokens(self):
        tokens_per_segment = int(self._epoch_permits // (self._epoch_seconds / self._token_update))
        segments_full = 0

        # If we go an entire epoch with a full bucket we'll stop this provider
        segments_per_epoch = int(ceil(self._epoch_seconds / self._token_update))
        while segments_full < segments_per_epoch:
            sleep(self._token_update)

            with self._tokens_lock:
                if self._tokens == self._token_limit:
                    segments_full += 1
                elif self._tokens == 0:
                    self._tokens = min(tokens_per_segment, self._token_limit)
                    segments_full = 0
                    try:
                        self._permitter.release()
                    except RuntimeError:
                        # Wasn't waiting on any acquire
                        pass
                else:
                    self._tokens = min(self._tokens + tokens_per_segment, self._token_limit)
                    segments_full = 0

        # Clean up
        with self._token_provider_lock:
            self._token_provider = None

    @property
    def permits_issued(self) -> int:
        with self._total_permits_issued_lock:
            return self._total_permits_issued

    def reset_permits_issued(self) -> None:
        with self._total_permits_issued_lock:
            self._total_permits_issued = 0
