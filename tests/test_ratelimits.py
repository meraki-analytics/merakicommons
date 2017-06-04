from merakicommons.ratelimits import FixedWindowRateLimiter, TokenBucketRateLimiter

SECONDS = 1
PERMITS = 6
BURST = 2
TOKENS = SECONDS / PERMITS

MANY_PERMITS = 100000000
VALUE_COUNT = 25
LARGE_VALUE_COUNT = 10000
EPSILON = 0.0001  # threading.Timer isn't super precise so we allow some jitter in expected time comparisons

##########################
# FixedWindowRateLimiter #
##########################


def test_window_acquire_simple():
    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)
    x = False
    with limiter:
        x = True
    assert x


def test_window_decorator_simple():
    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)

    @limiter.limit
    def call():
        return True

    assert call()


def test_window_permit_count():
    limiter = FixedWindowRateLimiter(SECONDS, MANY_PERMITS)
    assert limiter.permits_issued == 0

    @limiter.limit
    def call():
        pass

    for i in range(LARGE_VALUE_COUNT // 2):
        with limiter:
            pass
        assert limiter.permits_issued == i + 1

    limiter.reset_permits_issued()
    assert limiter.permits_issued == 0

    for i in range(LARGE_VALUE_COUNT // 2):
        call()
        assert limiter.permits_issued == i + 1


def test_window_acquire_timing():
    from time import time

    limiter = FixedWindowRateLimiter(SECONDS, PERMITS)
    times = []
    for _ in range(VALUE_COUNT):
        with limiter:
            times.append(time())

    start_indexes = [i for i in range(VALUE_COUNT) if i % PERMITS == 0]

    last = -SECONDS
    for index in start_indexes:
        assert times[index] - last >= SECONDS - EPSILON
        last = times[index]


def test_window_decorator_timing():
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


def test_window_acquire_across_windows():
    from time import time, sleep

    limiter = FixedWindowRateLimiter(SECONDS, 1)

    # This should take up two fixed windows for the first task, and the second shouldn't execute until the third (after 2 x SECONDS).
    with limiter:
        first = time()
        sleep(SECONDS * 1.25)

    with limiter:
        second = time()

    assert (SECONDS - EPSILON) * 3 >= second - first >= (SECONDS - EPSILON) * 2


def test_window_decorator_across_windows():
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

##########################
# TokenBucketRateLimiter #
##########################


def test_bucket_acquire_simple():
    limiter = TokenBucketRateLimiter(SECONDS, PERMITS, BURST, TOKENS)
    x = False
    with limiter:
        x = True
    assert x


def test_bucket_decorator_simple():
    limiter = TokenBucketRateLimiter(SECONDS, PERMITS, BURST, TOKENS)

    @limiter.limit
    def call():
        return True

    assert call()


def test_bucket_permit_count():
    limiter = TokenBucketRateLimiter(SECONDS, MANY_PERMITS, MANY_PERMITS, SECONDS)
    assert limiter.permits_issued == 0

    @limiter.limit
    def call():
        pass

    for i in range(LARGE_VALUE_COUNT // 2):
        with limiter:
            pass
        assert limiter.permits_issued == i + 1

    limiter.reset_permits_issued()
    assert limiter.permits_issued == 0

    for i in range(LARGE_VALUE_COUNT // 2):
        call()
        assert limiter.permits_issued == i + 1


def test_bucket_acquire_timing():
    from time import time

    limiter = TokenBucketRateLimiter(SECONDS, PERMITS, BURST, TOKENS)
    times = []
    for _ in range(VALUE_COUNT):
        with limiter:
            times.append(time())

    frequency = SECONDS / PERMITS
    for i in range(BURST - 1):
        assert times[i + 1] - times[i] < frequency - EPSILON

    times = times[BURST:]
    for i in range(len(times) - 1):
        assert 2 * (frequency - EPSILON) > times[i + 1] - times[i] > frequency - EPSILON


def test_bucket_decorator_timing():
    from time import time

    limiter = TokenBucketRateLimiter(SECONDS, PERMITS, BURST, TOKENS)

    @limiter.limit
    def call():
        return time()

    times = []
    for _ in range(VALUE_COUNT):
        times.append(call())

    frequency = SECONDS / PERMITS
    for i in range(BURST - 1):
        assert times[i + 1] - times[i] < frequency - EPSILON

    times = times[BURST:]
    for i in range(len(times) - 1):
        assert 2 * (frequency - EPSILON) > times[i + 1] - times[i] > frequency - EPSILON
