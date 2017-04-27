import pytest

from merakicommons.container import SearchError, searchable, SearchableList

VALUE_COUNT = 100

# Seriously where is this in the std lib...
GENERATOR_CLASS = (None for _ in range(0)).__class__


@searchable({str: "strings"})
class Inner(object):
    def __init__(self, strings):
        self.strings = strings


@searchable({Inner: "inner", str: ["strings", "inner"], int: "integer", float: "normal.value"})
class Outer(object):
    def __init__(self, inner, normal, strings, integer):
        self.inner = inner
        self.normal = normal
        self.strings = strings
        self.integer = integer


@searchable({str: "strings"})
class ContainsDefined(object):
    def __init__(self, strings):
        self.strings = strings

    def __contains__(self, item):
        return isinstance(item, int)


class NonSearchable(object):
    def __init__(self, value):
        self.value = value


inner = Inner(["hello", "world"])
normal = NonSearchable(100.0)
outer = Outer(inner, normal, ["cat", "dog"], 100)
other = Inner(["foo", "bar"])
defined = ContainsDefined(["larry", "moe", "curly"])
lst = SearchableList([other, normal, outer, inner, defined])


def test_simple_search():
    assert 100 in outer
    assert 0 not in outer


def test_bad_type():
    with pytest.raises(SearchError):
        100.0 in inner


def test_nested_key():
    assert 100.0 in outer
    assert 0.0 not in outer


def test_pass_through():
    assert "hello" in inner
    assert "world" in inner
    assert "cat" not in inner
    assert "dog" not in inner
    assert "foo" not in inner
    assert "bar" not in inner


def test_nested_object():
    assert inner in outer
    assert other not in outer

    assert "hello" in outer
    assert "world" in outer
    assert "foo" not in outer
    assert "bar" not in outer


def test_contains_defined():
    assert 0 in defined
    assert 100 in defined

    assert 0.0 not in defined
    assert 100.0 not in defined

    assert "larry" in defined
    assert "moe" in defined
    assert "curly" in defined
    assert "hello" not in defined
    assert "world" not in defined


def test_list_index():
    assert lst[0] is other
    assert lst[1] is normal
    assert lst[2] is outer
    assert lst[3] is inner
    assert lst[4] is defined
    for i in range(5, VALUE_COUNT):
        with pytest.raises(IndexError):
            lst[i]


def test_simple_list_membership():
    assert other in lst
    assert normal in lst
    assert outer in lst
    assert inner in lst
    assert defined in lst


def test_simple_list_contains():
    assert lst.contains(other)
    assert lst.contains(normal)
    assert lst.contains(outer)
    assert lst.contains(inner)
    assert lst.contains(defined)


def test_nested_list_membership():
    assert "hello" in lst
    assert "world" in lst
    assert "cat" in lst
    assert "dog" in lst
    assert "foo" in lst
    assert "bar" in lst
    assert "larry" in lst
    assert "moe" in lst
    assert "curly" in lst
    assert 0 in lst
    assert 100 in lst
    assert 100.0 in lst

    assert "value" not in lst
    assert 0.0 not in lst
    assert bytes() not in lst


def test_nested_list_contains():
    assert lst.contains("hello")
    assert lst.contains("world")
    assert lst.contains("cat")
    assert lst.contains("dog")
    assert lst.contains("foo")
    assert lst.contains("bar")
    assert lst.contains("larry")
    assert lst.contains("moe")
    assert lst.contains("curly")
    assert lst.contains(0)
    assert lst.contains(100)
    assert lst.contains(100.0)

    assert not lst.contains("value")
    assert not lst.contains(0.0)
    assert not lst.contains(bytes())


def test_enumerate_list():
    result = lst.enumerate("dog")
    assert isinstance(result, GENERATOR_CLASS)
    result = zip(result, [2], [outer])
    for one, index, two in result:
        i, one = one
        assert index == i
        assert one is two

    result = lst.enumerate("hello")
    assert isinstance(result, GENERATOR_CLASS)
    result = zip(result, [2, 3], [outer, inner])
    for one, index, two in result:
        i, one = one
        assert index == i
        assert one is two

    result = lst.enumerate("hello", reverse=True)
    assert isinstance(result, GENERATOR_CLASS)
    result = zip(result, [3, 2], [inner, outer])
    for one, index, two in result:
        i, one = one
        assert index == i
        assert one is two

    result = lst.enumerate("value")
    assert isinstance(result, GENERATOR_CLASS)
    result = zip(result, [], [])
    for one, index, two in result:
        i, one = one
        assert index == i
        assert one is two


def test_find_list():
    result = lst.find("dog")
    assert result is outer

    result = lst.find("hello")
    assert result is outer

    result = lst.find("hello", reverse=True)
    assert result is inner

    with pytest.raises(SearchError):
        lst.find("value")


def test_search_list():
    result = lst.search("dog")
    assert isinstance(result, SearchableList)
    result = zip(result, [outer])
    for one, two in result:
        assert one is two

    result = lst.search("hello")
    assert isinstance(result, SearchableList)
    result = zip(result, [outer, inner])
    for one, two in result:
        assert one is two

    result = lst.search("hello", reverse=True)
    assert isinstance(result, SearchableList)
    result = zip(result, [inner, outer])
    for one, two in result:
        assert one is two

    with pytest.raises(SearchError):
        lst.search("value")


def test_delete_index():
    lst = SearchableList([other, normal, outer, inner, defined])
    for i in range(5, VALUE_COUNT):
        with pytest.raises(IndexError):
            del lst[i]

    assert lst == [other, normal, outer, inner, defined]

    del lst[2]
    assert lst == [other, normal, inner, defined]

    del lst[0]
    assert lst == [normal, inner, defined]

    del lst[2]
    assert lst == [normal, inner]

    del lst[1]
    assert lst == [normal]

    del lst[0]
    assert lst == []


def test_delete_key():
    lst = SearchableList([other, normal, outer, inner, defined])

    with pytest.raises(SearchError):
        del lst["value"]

    with pytest.raises(SearchError):
        del lst[0.0]

    with pytest.raises(SearchError):
        del lst[bytes()]

    assert lst == [other, normal, outer, inner, defined]

    del lst["hello"]
    assert lst == [other, normal, defined]

    del lst[normal]
    assert lst == [other, defined]

    del lst["foo"]
    assert lst == [defined]

    del lst[defined]
    assert lst == []


def test_delete():
    lst = SearchableList([other, normal, outer, inner, defined])

    with pytest.raises(SearchError):
        lst.delete("value")

    with pytest.raises(SearchError):
        lst.delete(0.0)

    with pytest.raises(SearchError):
        lst.delete(bytes())

    assert lst == [other, normal, outer, inner, defined]

    lst.delete("hello")
    assert lst == [other, normal, defined]

    lst.delete(normal)
    assert lst == [other, defined]

    lst.delete(0)
    assert lst == [other]

    lst.delete("foo")
    assert lst == []
