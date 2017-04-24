from merakicommons.ghost import Ghost

TEST_VALUE = "TEST VALUE"
VALUE_COUNT = 100


class GhostObject(Ghost):
    def __init__(self) -> None:
        super().__init__()
        self.load_calls = 0

    def _load(self) -> None:
        self.load_calls += 1
        self._value = TEST_VALUE

    @Ghost.load_on
    def value(self) -> str:
        return self._value

    def other_value(self) -> str:
        return TEST_VALUE


def test_ghost_value():
    x = GhostObject()
    for _ in range(VALUE_COUNT):
        value = x.value()
        assert type(value) is type(TEST_VALUE)
        assert value == TEST_VALUE


def test_ghost_loading():
    x = GhostObject()
    assert x.load_calls == 0
    for _ in range(VALUE_COUNT):
        x.other_value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.other_value()
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.value()
        assert x.load_calls == 1

    for _ in range(VALUE_COUNT):
        x.other_value
        assert x.load_calls == 1

    for _ in range(VALUE_COUNT):
        x.other_value()
        assert x.load_calls == 1

    for _ in range(VALUE_COUNT):
        x.value
        assert x.load_calls == 1
