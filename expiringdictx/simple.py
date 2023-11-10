from typing import Any, TypeVar
from collections.abc import Callable
from datetime import datetime, timedelta

StoreType = TypeVar("StoreType")
CacheRecord = tuple[Any, datetime, timedelta]


class SimpleCache:
    """Simple cache with expiration time"""

    def __init__(self, default_lifetime: timedelta = timedelta(minutes=5)):
        self.default_lifetime = default_lifetime
        self._cache: dict[str, CacheRecord] = {}

    def __setitem__(self, key: str | tuple[str, timedelta], value: Any):
        match key:
            case k, timedelta() as lifetime:
                self._cache[k] = (value, datetime.now(), lifetime)
            case k:
                self._cache[key] = (value, datetime.now(), self.default_lifetime)

    def __getitem__(self, key: str):
        if item := self._cache.get(key):
            value, create_time, lifetime = item
            if datetime.now() - create_time <= lifetime:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, lifetime: timedelta | None = None):
        self[key] = (value, lifetime)

    def get(
        self, key: str, default: Any = None, value_convert_func: Callable[..., StoreType | None] | None = None
    ) -> StoreType | None:
        if value := self[key]:
            if value_convert_func:
                return value_convert_func(value)
            return value
        return default

    def clear(self):
        self._cache.clear()
