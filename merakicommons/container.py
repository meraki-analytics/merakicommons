from typing import Type, TypeVar, Mapping, Callable, Union, Collection, Any, Generator, Tuple

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
        max = len(items) - 1
        if reverse:
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
    def __getitem__(self, item: Any) -> Any:
        return self.find(item)

    def __contains__(self, item: Any) -> bool:
        return self.contains(item)

    def __delitem__(self, item: Any) -> None:
        self.delete(item)

    def _search_generator(self, item: Any) -> Generator[Any, None, None]:
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
