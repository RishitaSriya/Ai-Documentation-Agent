"""Hashing utilities for snapshot and content comparison."""

import hashlib
import json
from typing import Any


def calculate_content_hash(content: str) -> str:
    """Compute SHA-256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def calculate_dict_hash(data: Any) -> str:
    """Compute deterministic SHA-256 hash of a JSON-serializable structure."""
    serialized = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
