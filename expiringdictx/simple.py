from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar, Union, Optional, cast
from datetime import datetime, timedelta

KT = TypeVar("KT")
VT = TypeVar("VT")
_T = TypeVar("_T")
CacheRecord = tuple[VT, datetime, timedelta]


class SimpleCache(Generic[KT, VT]):
    """Simple cache with expiration time"""

    def __init__(self, default_lifetime: timedelta = timedelta(minutes=5)):
        self.default_lifetime = default_lifetime
        self._cache: dict[KT, CacheRecord[VT]] = {}

    def __setitem__(self, key: Union[KT, tuple[KT, timedelta]], value: VT):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise ValueError("key must be a tuple of (key, lifetime)")
            if TYPE_CHECKING:
                key = cast(tuple[KT, timedelta], key)
            key, lifetime = key
        else:
            lifetime = self.default_lifetime

        self._cache[key] = (value, datetime.now(), lifetime)

    def __getitem__(self, key: KT) -> Optional[VT]:
        if item := self._cache.get(key):
            value, create_time, lifetime = item
            if datetime.now() - create_time <= lifetime:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: KT, value: VT, lifetime: Optional[timedelta] = None):
        self._cache[key] = (value, datetime.now(), lifetime or self.default_lifetime)

    def get(
        self,
        key: KT,
        default: Optional[_T] = None,
        value_convert_func: Optional[Callable[[VT], _T]] = None,
    ) -> Optional[Union[VT, _T]]:
        if value := self[key]:
            if value_convert_func:
                return value_convert_func(value)
            return value
        return default

    def clear(self):
        self._cache.clear()
