"""Disk cache for raw JSON API responses, keyed by request identity (not public API)."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


class DiskCache:
    """Caches JSON-serializable values to disk, keyed by an arbitrary string.

    One file per key, named by the key's hash (so keys built from paths and query strings
    are always safe file names), holding the value plus the time it was written, so ``ttl``
    is checked on read without touching any other entry. Same layout as ``DiskCache`` of
    ranobelib-python-sdk.

    A cache must never break a request: a corrupted or unreadable entry is a miss, and a
    failed write is reported to the caller as ``OSError`` to log and move on from. Writes go
    through a temporary file and an atomic rename, so a concurrent reader never sees half an
    entry.
    """

    def __init__(
        self,
        cache_dir: str | os.PathLike[str],
        *,
        ttl: float | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initialize the cache.

        Args:
            cache_dir: Directory to store cache files in. Created on the first write.
            ttl: Seconds after which an entry is treated as a miss. ``None`` means entries
                never expire.
            clock: Wall-clock time source used to stamp and check entries (not a monotonic
                one: entries outlive the process). Replaceable in tests.

        Raises:
            ValueError: ``ttl`` is negative.
        """
        if ttl is not None and ttl < 0:
            raise ValueError(f"cache_ttl must not be negative, got {ttl}")
        self._dir = Path(cache_dir)
        self._ttl = ttl
        self._clock = clock

    @property
    def directory(self) -> Path:
        """The directory cache files are stored in."""
        return self._dir

    def get(self, key: str) -> Any | None:
        """Return the cached value for ``key``, or ``None`` on a miss or an expired entry."""
        try:
            entry = json.loads(self._path_for(key).read_text(encoding="utf-8"))
            cached_at = float(entry["cached_at"])
            data = entry["data"]
        except (OSError, ValueError, TypeError, KeyError):
            return None
        if self._ttl is not None and self._clock() - cached_at > self._ttl:
            return None
        return data

    def set(self, key: str, data: Any) -> None:
        """Write ``data`` under ``key``, creating the cache directory if needed.

        Raises:
            OSError: The entry couldn't be written.
        """
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps({"cached_at": self._clock(), "data": data}, ensure_ascii=False)
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                tmp.write(content)
            os.replace(tmp_name, path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._dir / f"{digest}.json"
