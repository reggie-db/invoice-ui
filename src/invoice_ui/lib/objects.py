"""
Object utilities for hashing and JSON serialization.

Provides convenience functions for creating stable hashes of objects
and serializing objects to JSON.
"""

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any


class HashResult:
    """
    Wrapper around a hash digest that provides hexdigest() method.

    Mimics the interface expected by the original dbx_core.objects.hash().
    """

    def __init__(self, data: bytes) -> None:
        """
        Initialize with the data to hash.

        Args:
            data: Bytes to compute hash from.
        """
        self._hash = hashlib.sha256(data)

    def hexdigest(self) -> str:
        """
        Return the hexadecimal digest of the hash.

        Returns:
            Hexadecimal string representation of the hash.
        """
        return self._hash.hexdigest()


def hash(obj: Any) -> HashResult:
    """
    Create a stable hash of an object or list of objects.

    Objects are serialized to JSON before hashing to ensure consistent
    results across different Python sessions.

    Args:
        obj: Any JSON-serializable object or list of objects.

    Returns:
        HashResult instance with hexdigest() method.
    """
    json_str = json.dumps(obj, sort_keys=True, default=str)
    return HashResult(json_str.encode("utf-8"))


def to_json(obj: Any, indent: int | None = None) -> str:
    """
    Serialize an object to JSON string.

    Handles dataclasses by converting them to dictionaries first.
    Falls back to str() for non-serializable objects.

    Args:
        obj: Object to serialize.
        indent: Optional indentation for pretty printing.

    Returns:
        JSON string representation.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        obj = asdict(obj)
    return json.dumps(obj, default=_default_serializer, indent=indent)


def _default_serializer(obj: Any) -> Any:
    """
    Default serializer for JSON encoding.

    Handles common types that aren't JSON serializable by default.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-serializable representation.
    """
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)
