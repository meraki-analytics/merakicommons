from merakicommons.cache import lazy_property

TEST_VALUE = "TEST VALUE"
VALUE_COUNT = 100


class LazyProperty(object):
    def __init__(self) -> None:
        self.property_calls = 0

    @lazy_property
    def property(self) -> str:
        self.property_calls += 1
        return TEST_VALUE


def test_lazy_property_type():
    assert type(LazyProperty.property) is property


def test_lazy_property_value():
    x = LazyProperty()
    for _ in range(VALUE_COUNT):
        value = x.property
        assert type(value) is type(TEST_VALUE)
        assert value == TEST_VALUE


def test_lazy_property_loading():
    x = LazyProperty()
    assert x.property_calls == 0
    for _ in range(VALUE_COUNT):
        x.property
        assert x.property_calls == 1
