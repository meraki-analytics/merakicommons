from typing import Callable
from time import sleep, monotonic
from math import ceil
from abc import ABC, abstractmethod
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
    def __enter__(self) -> "RateLimiter":
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def limit(self, method: Callable) -> Callable:
        def limited(*args, **kwargs):
            with self:
                return method(*args, **kwargs)
        return limited


class MultiRateLimiter(RateLimiter):
    def __init__(self, *limiters: RateLimiter) -> None:
        self._limiters = limiters

        self._total_permits_issued = 0
        self._total_permits_issued_lock = Lock()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        for limiter in self._limiters:
            limiter.__exit__(exc_type, exc_val, exc_tb)

    def __enter__(self) -> "RateLimiter":
        for limiter in self._limiters:
            limiter.__enter__()

        # Increment total count
        with self._total_permits_issued_lock:
            self._total_permits_issued += 1

        return self

    @property
    def permits_issued(self) -> int:
        with self._total_permits_issued_lock:
            return self._total_permits_issued

    def reset_permits_issued(self) -> None:
        with self._total_permits_issued_lock:
            self._total_permits_issued = 0


class FixedWindowRateLimiter(RateLimiter):
    def __init__(self, window_seconds: int, window_permits: int) -> None:
        self._window_seconds = window_seconds
        self._window_permits = window_permits

        self._permitter = Lock()
        self._permits = window_permits

        self._total_permits_issued = 0
        self._total_permits_issued_lock = Lock()

        self._enter_exit_lock = Lock()
        self._currently_processing = 0
        self._resetter = None

    def __enter__(self) -> "FixedWindowRateLimiter":
        # Grab the permit lock and decrement remaining permits. If this leaves it at 0, don't release the permit lock. It will be released by the resetter.
        self._permitter.acquire()
        with self._enter_exit_lock, self._total_permits_issued_lock:
            self._permits -= 1

            self._total_permits_issued += 1
            self._currently_processing += 1

            if self._permits > 0:
                self._permitter.release()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        with self._enter_exit_lock:
            self._currently_processing -= 1

            # The fixed window starts after processing the first permit ends. The presence of a resetter indicates whether we're in a fixed window already or if we need to start one.
            if not self._resetter:
                self._resetter = Timer(self._window_seconds, self._reset)
                self._resetter.daemon = True
                self._resetter.start()

    def _reset(self):
        with self._enter_exit_lock:
            self._permits = self._window_permits - self._currently_processing
            self._resetter = None

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

        self._total_permits_issued = 0
        self._total_permits_issued_lock = Lock()

        self._enter_exit_lock = Lock()

        self._token_update = token_update_frequency
        self._token_provider = None

    def __enter__(self) -> "TokenBucketRateLimiter":
        # Grab the permit lock and decrement remaining permits. If this leaves it at 0, don't release the permit lock. It will be released by the token provider.
        self._permitter.acquire()
        with self._enter_exit_lock, self._total_permits_issued_lock:
            self._tokens -= 1

            self._total_permits_issued += 1

            if self._tokens >= 1:
                self._permitter.release()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # We don't want a thread sitting around dumping tokens into a filled bucket during downtimes. We construct one when needed and it cleans itself up if the bucket is full for an entire epoch.
        with self._enter_exit_lock:
            if not self._token_provider:
                self._token_provider = Thread(target=self._provide_tokens)
                self._token_provider.daemon = True
                self._token_provider.start()

    def _provide_tokens(self):
        tokens_per_segment = self._epoch_permits / (self._epoch_seconds / self._token_update)
        segments_full = 0

        start_time = monotonic()
        next_time = start_time + self._token_update

        # If we go an entire epoch with a full bucket we'll stop this provider
        segments_per_epoch = int(ceil(self._epoch_seconds / self._token_update))
        while True:
            sleep(max(next_time - monotonic(), 0))
            next_time = next_time + self._token_update

            with self._enter_exit_lock:
                if self._tokens == self._token_limit:
                    segments_full += 1
                elif self._tokens < 1:
                    self._tokens = min(self._tokens + tokens_per_segment, self._token_limit)
                    segments_full = 0
                    if self._tokens >= 1:
                        try:
                            self._permitter.release()
                        except RuntimeError:
                            # Wasn't waiting on any acquire
                            pass
                else:
                    self._tokens = min(self._tokens + tokens_per_segment, self._token_limit)
                    segments_full = 0

                if segments_full >= segments_per_epoch:
                    # End this thread
                    self._token_provider = None
                    break

    @property
    def permits_issued(self) -> int:
        with self._total_permits_issued_lock:
            return self._total_permits_issued

    def reset_permits_issued(self) -> None:
        with self._total_permits_issued_lock:
            self._total_permits_issued = 0
