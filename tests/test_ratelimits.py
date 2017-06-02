from merakicommons.ratelimits import FixedWindowRateLimiter

SECONDS = 1
PERMITS = 5
MANY_PERMITS = 100000000
VALUE_COUNT = 25
LARGE_VALUE_COUNT = 10000
EPSILON = 0.0001  # threading.Timer isn't super precise so we allow some jitter in expected time comparisons


def test_acquire_simple():
    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)
    x = False
    with limiter.acquire():
        x = True
    assert x


def test_decorator_simple():
    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)

    @limiter.limit
    def call():
        return True

    assert call()


def test_permit_count():
    limiter = FixedWindowRateLimiter(SECONDS, MANY_PERMITS)
    assert limiter.permits_issued == 0

    @limiter.limit
    def call():
        pass

    for i in range(LARGE_VALUE_COUNT // 2):
        with limiter.acquire():
            pass
        assert limiter.permits_issued == i + 1

    limiter.reset_permits_issued()
    assert limiter.permits_issued == 0

    for i in range(LARGE_VALUE_COUNT // 2):
        call()
        assert limiter.permits_issued == i + 1


def test_acquire_timing():
    from time import time

    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)
    times = []
    for _ in range(VALUE_COUNT):
        with limiter.acquire():
            times.append(time())

    start_indexes = [i for i in range(VALUE_COUNT) if i % PERMITS == 0]

    last = -SECONDS
    for index in start_indexes:
        assert times[index] - last >= SECONDS - EPSILON
        last = times[index]


def test_decorator_timing():
    from time import time

    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)

    @limiter.limit
    def call():
        return time()

    times = []
    for _ in range(VALUE_COUNT):
        times.append(call())

    start_indexes = [i for i in range(VALUE_COUNT) if i % PERMITS == 0]

    last = -SECONDS
    for index in start_indexes:
        assert times[index] - last >= SECONDS - EPSILON
        last = times[index]


def test_acquire_across_windows():
    from time import time, sleep

    limiter = FixedWindowRateLimiter(SECONDS, 1)

    # This should take up two fixed windows for the first task, and the second shouldn't execute until the third (after 2 x SECONDS).
    with limiter.acquire():
        first = time()
        sleep(SECONDS * 1.25)

    with limiter.acquire():
        second = time()

    assert (SECONDS - EPSILON) * 3 >= second - first >= (SECONDS - EPSILON) * 2


def test_decorator_across_windows():
    from time import time, sleep

    limiter = FixedWindowRateLimiter(SECONDS, 1)

    @limiter.limit
    def call():
        t = time()
        sleep(SECONDS * 1.25)
        return t

    # This should take up two fixed windows for the first task, and the second shouldn't execute until the third (after 2 x SECONDS).
    first = call()
    second = call()

    assert (SECONDS - EPSILON) * 3 >= second - first >= (SECONDS - EPSILON) * 2
