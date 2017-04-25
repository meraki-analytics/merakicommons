import pytest

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

    @Ghost.load_on
    def constant_value(self) -> str:
        return TEST_VALUE

    @Ghost.load_on
    def bad_value(self) -> None:
        return self._bad_value

    def unloaded_value(self) -> str:
        return TEST_VALUE


def test_ghost_value():
    x = GhostObject()
    for _ in range(VALUE_COUNT):
        value = x.value()
        assert type(value) is type(TEST_VALUE)
        assert value == TEST_VALUE


def test_constant_value():
    x = GhostObject()
    for _ in range(VALUE_COUNT):
        value = x.constant_value()
        assert type(value) is type(TEST_VALUE)
        assert value == TEST_VALUE


def test_bad_value():
    x = GhostObject()
    for _ in range(VALUE_COUNT):
        with pytest.raises(AttributeError):
            x.bad_value()


def test_ghost_load_normal_attribute():
    x = GhostObject()
    assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.unloaded_value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.unloaded_value()
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.unloaded_value
        assert x.load_calls == 0


def test_ghost_load_required():
    x = GhostObject()
    assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.value()
        assert x.load_calls == 1

    for _ in range(VALUE_COUNT):
        x.value
        assert x.load_calls == 1


def test_ghost_load_not_required():
    x = GhostObject()
    assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.constant_value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.constant_value()
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.constant_value
        assert x.load_calls == 0


def test_ghost_load_bad_value():
    x = GhostObject()
    assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        x.bad_value
        assert x.load_calls == 0

    for _ in range(VALUE_COUNT):
        with pytest.raises(AttributeError):
            x.bad_value()
        assert x.load_calls == 1

    for _ in range(VALUE_COUNT):
        x.bad_value
        assert x.load_calls == 1