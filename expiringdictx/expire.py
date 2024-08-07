from functools import wraps
from threading import RLock
from contextlib import suppress
from typing_extensions import Self
from typing import TYPE_CHECKING, Generic, TypeVar, Union, Optional, cast, overload
from datetime import datetime, timedelta
from collections.abc import Mapping, Callable

from lru import LRU


KT = TypeVar("KT")
VT = TypeVar("VT")
_T = TypeVar("_T")
Callbackable = Callable[[KT, tuple[VT, datetime]], None]
Number = TypeVar("Number", int, float)


def cleanup_expired(expiringdict_method):
    """Decorator to cleanup expired items before calling the wrapped method.

    It already acquires the lock, so no need to do it again in the wrapped method.
    """

    @wraps(expiringdict_method)
    def wrapper(self: "ExpiringDict", *args, **kwargs):
        self._cleanup_expired()
        return expiringdict_method(self, *args, **kwargs)

    return wrapper


def exlock(expiringdict_method):
    """Decorator to acquire the lock before calling the wrapped method."""

    @wraps(expiringdict_method)
    def wrapper(self: "ExpiringDict", *args, **kwargs):
        with self.lock:
            return expiringdict_method(self, *args, **kwargs)

    return wrapper


class ExpiringDict(Generic[KT, VT]):
    """A thread-safe dictionary with auto-expiring values for caching purposes.

    Expiration happens on any access, object is locked during cleanup from expired
    values.

    When the item insert into a full capacity dictionary, the least recently used item
    will be removed.

    :param capacity: The maximum number of items the dictionary can hold.
    :param default_age: The default age of the items in the dictionary.
    :param callback: A function called when an item is operated.
        The function must accept two positional arguments:
        `key` and `value`. The function is called only during normal operations,
        i.e. when an item is accessed before it is removed.
        See by `lru.LRU` for more details.

    >>> from expiringdictx import ExpiringDict
    >>> from datetime import timedelta
    >>> d = ExpiringDict(max_len=100, default_age=timedelta(seconds=10))
    >>> d["key1"] = "value1" # key expires in 10 seconds
    >>> d["key2", timedelta(minutes=5)] = "value2" # key expires in 5 minutes
    >>> d["key3", 5] = "value3" # key expires in 5 seconds
    >>> sleep(5)
    >>> print(d["key3"]) # print None
    """

    def __init__(
        self,
        capacity: int,
        default_age: Union[timedelta, Number],
        callback: Optional[Callbackable[KT, VT]] = None,
    ) -> None:
        if callback is not None:
            self._lru: LRU[KT, tuple[VT, datetime]] = LRU(capacity, callback) # pyright: ignore[reportRedeclaration]
        else:
            self._lru: LRU[KT, tuple[VT, datetime]] = LRU(capacity)
        self.default_age = default_age if isinstance(default_age, timedelta) else timedelta(seconds=default_age)
        self.lock = RLock()

    @property
    def capacity(self) -> int:
        """The maximum number of items the dictionary can hold."""
        return self._lru.get_size()

    @exlock
    def __setitem__(self, _key: Union[tuple[KT, Union[timedelta, Number]], KT], value: VT) -> None:
        if isinstance(_key, tuple):
            if TYPE_CHECKING:
                _key = cast(tuple[KT, Union[timedelta, Number]], _key)
            key, age = _key
            self.__insert_with_age(key, value, age)
        else:
            self.__insert_with_age(_key, value, None)

    @exlock
    def __getitem__(self, key: KT) -> VT:
        if self._is_expired(key):
            del self._lru[key]
            raise KeyError(key)
        return self._lru[key][0]

    @exlock
    def __delitem__(self, key: KT) -> None:
        del self._lru[key]

    @cleanup_expired
    def __contains__(self, key: KT) -> bool:
        return key in self._lru

    @cleanup_expired
    def __len__(self) -> int:
        return len(self._lru)

    @cleanup_expired
    def __iter__(self):
        return iter(self._lru.keys())

    @exlock
    def __str__(self):
        return f"ExpiringDict({self._lru}, default_age={self.default_age}, capacity={self.capacity})"

    @exlock
    def _cleanup_expired(self):
        """Remove expired items from the dictionary.

        The `cleanup_expired` decorator calls this method before calling the wrapped method.
        """
        current_time = datetime.now()
        expire_keys = [key for key, (_, expiry_time) in self._lru.items() if expiry_time < current_time]
        for key in expire_keys:
            del self._lru[key]

    @cleanup_expired
    def items(self):
        """Return a copy of the expiringdict's list of (key, value) pairs."""
        return [(item[0], item[1][0]) for item in self._lru.items()]

    @cleanup_expired
    def viewitems(self):
        """Exd.items() -> a set-like object providing a view on Exd's items"""
        return dict(self._lru).items()

    @cleanup_expired
    def keys(self):
        """Return a copy of the expiringdict's list of keys."""
        return self._lru.keys()

    @cleanup_expired
    def viewkeys(self):
        """Exd.keys() -> a set-like object providing a view on Exd's keys"""
        return dict(self._lru).keys()

    @cleanup_expired
    def values(self):
        """Return a copy of the expiringdict's list of values."""
        return [value[0] for value in self._lru.values()]

    @cleanup_expired
    def viewvalues(self):
        """Exd.values() -> an object providing a view on Exd's values"""
        return dict(self._lru).values()

    @exlock
    def update(self, updateable: Mapping[KT, Union[VT, tuple[VT, Number], tuple[VT, timedelta]]], /) -> None:
        """Update the dictionary with the key/value pairs from a mapping object.

        When value is a tuple, the second element is the age of the item.
        """
        for key, value in updateable.items():
            if isinstance(value, tuple):
                self.__insert_with_age(key, value[0], value[1])
            else:
                self.__insert_with_age(key, value, None)

    @cleanup_expired
    def refresh(self, key: KT, new_age: Optional[Union[timedelta, Number]] = None) -> None:
        """Refresh the expiry time of an existing key.

        When `new_age` is None, the default age is used. Otherwise, the new age is used.
        If remaining time is longer than the new age, the remaining time is used.
        """
        if key not in self._lru:
            raise KeyError(key)

        if isinstance(new_age, (int, float)):
            new_age = timedelta(seconds=new_age)
        elif isinstance(new_age, timedelta):
            pass
        else:
            new_age = self.default_age

        value, deadtime = self._lru[key]
        if deadtime - datetime.now() < new_age:
            self._lru[key] = value, datetime.now() + new_age

    @exlock
    def clear(self):
        """Remove all items from the dictionary."""
        self._lru.clear()

    @overload
    def pop(self, key: KT) -> Optional[VT]:
        ...

    @overload
    def pop(self, key: KT, default: VT) -> VT:
        ...

    @overload
    def pop(self, key: KT, default: _T) -> Union[VT, _T]:
        ...

    @exlock
    def pop(self, key: KT, default: Optional[Union[VT, _T]] = None) -> Optional[Union[VT, _T]]:
        """Remove specified key and return the corresponding value.

        If key is not found, default is returned if given, otherwise KeyError is raised.
        """
        p = self._lru.pop(key, default)
        if isinstance(p, tuple):
            return p[0]
        return p

    @exlock
    def popitem(self, least_recent: bool = True) -> Optional[tuple[KT, VT]]:
        """Remove and return the least recently used item.

        If least_recent is False, remove and return newest item.
        """
        if p := self._lru.popitem(least_recent):
            return p[0], p[1][0]
        return None

    @exlock
    def ttl(self, key: KT) -> Optional[timedelta]:
        """Return the remaining time to live of an item.

        If the item does not exist, return None.
        """
        if self._is_expired(key):
            with suppress(KeyError):
                del self._lru[key]
            return None
        _, entry_time = self._lru[key]
        return entry_time - datetime.now()

    @exlock
    def ddl(self, key: KT) -> Optional[datetime]:
        """Return the deadline of an item.

        If the item does not exist, return None.
        """
        if self._is_expired(key):
            with suppress(KeyError):
                del self._lru[key]
            return None
        return self._lru[key][1]

    @overload
    def get(self, key: KT) -> Optional[VT]:
        ...

    @overload
    def get(self, key: KT, default: VT) -> VT:
        ...

    @overload
    def get(self, key: KT, default: _T) -> Union[VT, _T]:
        ...

    @exlock
    def get(self, key: KT, default: Optional[Union[VT, _T]] = None) -> Optional[Union[VT, _T]]:
        """Return the value for key if key is in the dictionary, else None."""
        if self._is_expired(key):
            with suppress(KeyError):
                del self._lru[key]
            return default
        return self._lru[key][0]

    @exlock
    def get_with_deadtime(self, key: KT) -> Optional[tuple[VT, datetime]]:
        """Return the value and expiry time for key if key is in the dictionary, else None."""
        if self._is_expired(key):
            with suppress(KeyError):
                del self._lru[key]
            return None
        return self._lru[key]

    @exlock
    def set(self, key: KT, value: VT, age: Optional[Union[timedelta, Number]] = None) -> None:
        """Set the value for key in the dictionary.

        age is the expiry time of the item. If age is None, the default age is used.
        """
        self.__insert_with_age(key, value, age)

    def set_capacity(self, capacity: int) -> None:
        self._lru.set_size(capacity)

    @classmethod
    def fromkeys(
        cls,
        keys: list[KT],
        default_value: VT,
        default_age: Union[timedelta, Number],
        capacity: Optional[int] = None,
        callback: Optional[Callbackable[KT, VT]] = None,
    ) -> Self:
        """Create a new expiringdict with keys from iterable and values set to default_value."""
        if callback is not None:
            instance = cls(capacity or len(keys), default_age, callback)
        else:
            instance = cls(capacity or len(keys), default_age)
        for key in keys:
            instance[key] = default_value
        return instance

    @classmethod
    def frommapping(
        cls,
        mapping: Mapping[KT, VT],
        default_age: Union[timedelta, Number],
        /,
        capacity: Optional[int] = None,
        callback: Optional[Callbackable[KT, VT]] = None,
    ) -> Self:
        """Create a new expiringdict with keys and values from mapping."""
        if callback is not None:
            instance = cls(capacity or len(mapping), default_age, callback)
        else:
            instance = cls(capacity or len(mapping), default_age)
        for key, value in mapping.items():
            instance[key] = value
        return instance

    @classmethod
    def fromexpiringdict(
        cls,
        exd: Self,
        default_age: Union[timedelta, Number],
        /,
        capacity: Optional[int] = None,
        callback: Optional[Callbackable[KT, VT]] = None,
    ) -> Self:
        """Create a new expiringdict with keys and values from other expiringdict.

        old expiringdict's callback will lost.
        """
        if callback is not None:
            instance = cls(capacity or exd.capacity, default_age or exd.default_age, callback or callback)
        else:
            instance = cls(capacity or exd.capacity, default_age or exd.default_age)
        now = datetime.now()
        for key, (value, expiry_time) in exd.viewitems():
            if expiry_time < now:
                continue
            age = expiry_time - now
            instance[key, age] = value
        return instance

    @exlock
    def _is_expired(self, key: KT) -> bool:
        """Return True if the key is expired, else False."""
        if key not in self._lru:
            return True
        return self._lru[key][1] < datetime.now()

    def __insert_with_age(self, key: KT, value: VT, age: Optional[Union[timedelta, Number]] = None):
        """Insert a new item with specified age."""
        if isinstance(age, (int, float)):
            self._lru[key] = value, datetime.now() + timedelta(seconds=age)
        elif isinstance(age, timedelta):
            self._lru[key] = value, datetime.now() + age
        else:
            self._lru[key] = value, datetime.now() + self.default_age
