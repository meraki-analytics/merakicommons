from typing import Type, TypeVar, Mapping, Callable, Union, Collection, Any, Generator, Tuple, Optional

T = TypeVar("T")


class SearchError(TypeError):
    pass


def searchable(search_key_types: Mapping[Type, Union[str, Collection[str]]]) -> Callable[[T], T]:
    search_key_types = dict(search_key_types)

    # For each key type, we want to store the ordered attributes to query.
    # We accept attribute.sub_attribute, so split all target attributes on "."
    for key, types in search_key_types.items():
        if isinstance(types, str):
            types = [types]
        types = [type.split(".") for type in types]
        search_key_types[key] = types

    def search(instance: T, item: Any) -> bool:
        try:
            search_keys = search_key_types[type(item)]
        except KeyError:
            raise SearchError("Attempted to search for invalid type! Accepted types are {types}".format(types=[key_type.__name__ for key_type in search_key_types.keys()]))

        for search_key in search_keys:
            failed = False
            value = instance
            for sub_attribute in search_key:
                try:
                    value = getattr(value, sub_attribute)
                except AttributeError:
                    failed = True
                    break

            # This search key didn't exist for the item
            if failed:
                continue

            # Found the search item directly as an attribute
            if value == item:
                return True

            # Try to pass it along to the attribute's __contains__
            try:
                if item in value:
                    return True
            except (TypeError, SearchError):
                # The attribute doesn't define __contains__ or is searchable and doesn't accept this key type
                continue

    def decorator(cls: T) -> T:
        if hasattr(cls, "__contains__"):
            contains = cls.__contains__

            def new_contains(self, item: Any) -> bool:
                result = contains(self, item)

                # If it's contained by normal means, short circuit
                if result:
                    return True
                try:
                    # Try a search
                    if search(self, item):
                        return True
                except SearchError:
                    # Search doesn't accept that type
                    pass

                # Search and normal __contains__ implementations both were False
                return False
        else:
            new_contains = search

        cls.__contains__ = new_contains

        if cls.__doc__ is not None:
            cls.__doc__ += "\n\n"
        else:
            cls.__doc__ = ""
        cls.__doc__ += "Searchable by {types}".format(types=[key_type.__name__ for key_type in search_key_types.keys()])

        return cls

    return decorator


class SearchableList(list):
    def filter(self, function):
        return filter(function, self)

    def __getitem__(self, item: Any) -> Any:
        try:
            return super().__getitem__(item)
        except TypeError:
            return self.find(item)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def __delitem__(self, item: Any) -> None:
        try:
            super().__delitem__(item)
        except TypeError:
            self.delete(item)

    def _search_generator(self, item: Any, reverse: bool = False) -> Generator[Any, None, None]:
        """A helper method for `self.search` that returns a generator rather than a list."""
        results = 0
        for _, x in self.enumerate(item, reverse=reverse):
            yield x
            results += 1
        if results == 0:
            raise SearchError(str(item))

    def search(self, item: Any, streaming: bool = False, reverse: bool = False) -> Union["SearchableList", Generator[Any, None, None]]:
        if streaming:
            return self._search_generator(item, reverse=reverse)
        else:
            result = SearchableList(x for _, x in self.enumerate(item, reverse=reverse))
            if len(result) == 0:
                raise SearchError(str(item))
            return result

    def find(self, item: Any, reverse: bool = False) -> Any:
        for _, x in self.enumerate(item, reverse=reverse):
            return x
        raise SearchError(str(item))

    def contains(self, item: Any) -> bool:
        for _, _ in self.enumerate(item):
            return True
        return False

    def enumerate(self, item: Any, reverse: bool = False) -> Generator[Tuple[int, Any], None, None]:
        items = self
        if reverse:
            max = len(items) - 1
            items = reversed(items)
        for index, x in enumerate(items):
            if x == item:
                yield max - index if reverse else index, x
                continue

            try:
                if item in x:
                    yield max - index if reverse else index, x
            except TypeError:
                # x doesn't define __contains__
                pass

    def delete(self, item: Any) -> None:
        deleted = 0
        for index, _ in self.enumerate(item, reverse=True):
            del self[index]
            deleted += 1
        if deleted == 0:
            raise SearchError(str(item))


class SearchableSet(set):
    def filter(self, function):
        return filter(function, self)

    def __getitem__(self, item: Any) -> Any:
        return self.find(item)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def __delitem__(self, item: Any) -> None:
        self.delete(item)

    def _search_generator(self, item: Any) -> Generator[Any, None, None]:
        """A helper method for `self.search` that returns a generator rather than a list."""
        results = 0
        for x in self.enumerate(item):
            yield x
            results += 1
        if results == 0:
            raise SearchError(str(item))

    def search(self, item: Any, streaming: bool = False) -> Union["SearchableSet", Generator[Any, None, None]]:
        if streaming:
            return self._search_generator(item)
        else:
            result = SearchableSet(self.enumerate(item))
            if len(result) == 0:
                raise SearchError(str(item))
            return result

    def find(self, item: Any) -> Any:
        for x in self.enumerate(item):
            return x
        raise SearchError(str(item))

    def contains(self, item: Any) -> bool:
        for _ in self.enumerate(item):
            return True
        return False

    def enumerate(self, item: Any) -> Generator[Any, None, None]:
        for x in self:
            if x == item:
                yield x
                continue

            try:
                if item in x:
                    yield x
            except TypeError:
                # x doesn't define __contains__
                pass

    def delete(self, item: Any) -> None:
        to_delete = set(self.enumerate(item))
        if len(to_delete) == 0:
            raise SearchError(str(item))
        for x in to_delete:
            self.remove(x)


class SearchableDictionary(dict):
    def filter(self, function):
        return filter(function, self.items())

    def __getitem__(self, item: Any) -> Any:
        try:
            return super().__getitem__(item)
        except KeyError:
            return self.find(item)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def __delitem__(self, item: Any) -> None:
        try:
            super().__delitem__(item)
        except KeyError:
            self.delete(item)

    def _search_generator(self, item: Any) -> Generator[Tuple[Any, Any], None, None]:
        """A helper method for `self.search` that returns a generator rather than a list."""
        results = 0
        for key, value in self.enumerate(item):
            yield key, value
            results += 1
        if results == 0:
            raise SearchError(str(item))

    def search(self, item: Any, streaming: bool = False) -> Union["SearchableDictionary", Generator[Tuple[Any, Any], None, None]]:
        if streaming:
            return self._search_generator(item)
        else:
            result = SearchableDictionary(self.enumerate(item))
            if len(result) == 0:
                raise SearchError(str(item))
            return result

    def find(self, item: Any) -> Tuple[Any, Any]:
        for key, value in self.items():
            if key == item:
                return key, value

            try:
                if item in key:
                    return key, value
            except TypeError:
                # key doesn't define __contains__
                pass

            if value == item:
                return key, value

            try:
                if item in value:
                    return key, value
            except TypeError:
                # value doesn't define __contains__
                pass
        raise SearchError(str(item))

    def contains(self, item: Any) -> bool:
        for _, _ in self.enumerate(item):
            return True
        return False

    def enumerate(self, item: Any) -> Generator[Tuple[Any, Any], None, None]:
        for key, value in self.items():
            if key == item:
                yield key, value
                continue

            try:
                if item in key:
                    yield key, value
                    continue
            except TypeError:
                # key doesn't define __contains__
                pass

            if value == item:
                yield key, value
                continue

            try:
                if item in value:
                    yield key, value
                    continue
            except TypeError:
                # value doesn't define __contains__
                pass

    def delete(self, item: Any) -> None:
        to_delete = {key for key, _ in self.enumerate(item)}
        if len(to_delete) == 0:
            raise SearchError(str(item))
        for key in to_delete:
            del self[key]


class SearchableLazyList(SearchableList):
    """A SearchableList where the values of the list are generated on-demand.

    Arguments:
        constructor (callable): A function that returns a generator of the values to be put in the list.
    """
    def __init__(self, generator: Generator):
        self._generator = generator
        self._empty = False
        super().__init__()  # initialize an empty list

    def __str__(self):
        if self._empty:
            return super().__str__()
        else:
            string = super().__str__()
            if string == "[]":
                return "[...]"
            else:
                return string[:-1] + ", ...]"

    def __iter__(self):
        for item in super().__iter__():
            yield item
        while not self._empty:
            yield next(self)

    def __len__(self):
        if self._empty:
            return super().__len__()
        else:
            raise RuntimeError("SearchableLazyList hasn't been fully generated yet and therefore has an unknown length.")

    def __next__(self):
        try:
            value = next(self._generator)
            self.append(value)
        except StopIteration as error:
            self._empty = True
            raise error
        return value

    def _generate_many(self, count: Optional[int] = None):
        if count is not None:
            for _ in range(count):
                next(self)
        else:
            for _ in self:
                pass
            assert self._empty

    def __getitem__(self, item: Any) -> Any:
        try:
            return list.__getitem__(self, item)
        except IndexError:
            # Generate new values until: 1) we get to position `item` (which is an int) or 2) no more values are left
            iterate_until = item - super().__len__() + 1
            try:
                self._generate_many(iterate_until)
            except StopIteration:
                pass
            # Now that we have 1) enough or 2) all the values, try returning again.
            # If we still get an index error, then we have an int that is being searched on.
            try:
                return list.__getitem__(self, item)
            except IndexError:
                return self.find(item)
        except TypeError:
            return self.find(item)

    def __delitem__(self, item: Any) -> None:
        if isinstance(item, int):
            # Make sure we have enough values generated
            try:
                iterate_until = item - super().__len__() + 1
                self._generate_many(iterate_until)
            except StopIteration:
                pass
        try:
            list.__delitem__(self, item)
        except (IndexError, TypeError) as error:
            self.delete(item)

    def __reversed__(self):
        self._generate_many()
        return super().__reversed__()

    def delete(self, item: Any) -> None:
        deleted = 0
        for index, _ in self.enumerate(item, reverse=False):
            del self[index]
            deleted += 1
        if deleted == 0:
            raise SearchError(str(item))
