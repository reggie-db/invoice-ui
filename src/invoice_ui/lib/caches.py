"""
Disk-based caching utilities with TTL support.

Provides a DiskCache class that stores cached values on disk with
automatic expiration. Uses the diskcache library for reliable,
thread-safe storage.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypeVar

import diskcache

T = TypeVar("T")


@dataclass
class CacheEntry:
    """
    Wrapper around a cached value.

    Attributes:
        value: The cached value.
    """

    value: Any


class DiskCache:
    """
    Disk-based cache with TTL support.

    Stores values in a directory on disk using the diskcache library.
    Thread-safe and process-safe.

    Attributes:
        cache_dir: Path to the cache directory.
    """

    def __init__(self, cache_dir: str | Path) -> None:
        """
        Initialize the disk cache.

        Args:
            cache_dir: Directory path for storing cache files.
                       Created if it doesn't exist.
        """
        self.cache_dir = Path(cache_dir)
        self._cache = diskcache.Cache(str(self.cache_dir))

    def get_or_load(
        self,
        key: str,
        loader: Callable[[], T],
        expire: int | None = None,
    ) -> CacheEntry:
        """
        Get a value from cache or load it using the provided function.

        If the key exists in cache and hasn't expired, returns the cached
        value. Otherwise, calls the loader function, stores the result,
        and returns it.

        Args:
            key: Cache key string.
            loader: Function to call if cache miss (no arguments).
            expire: TTL in seconds. None means no expiration.

        Returns:
            CacheEntry containing the value.
        """
        cached = self._cache.get(key, default=None)
        if cached is not None:
            return CacheEntry(value=cached)

        # Cache miss - load the value
        value = loader()
        self._cache.set(key, value, expire=expire)
        return CacheEntry(value=value)

    def get(self, key: str) -> CacheEntry | None:
        """
        Get a value from cache.

        Args:
            key: Cache key string.

        Returns:
            CacheEntry if found, None otherwise.
        """
        cached = self._cache.get(key, default=None)
        if cached is not None:
            return CacheEntry(value=cached)
        return None

    def set(self, key: str, value: Any, expire: int | None = None) -> None:
        """
        Store a value in cache.

        Args:
            key: Cache key string.
            value: Value to store.
            expire: TTL in seconds. None means no expiration.
        """
        self._cache.set(key, value, expire=expire)

    def delete(self, key: str) -> None:
        """
        Delete a key from cache.

        Args:
            key: Cache key to delete.
        """
        self._cache.delete(key)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()

    def close(self) -> None:
        """Close the cache and release resources."""
        self._cache.close()
