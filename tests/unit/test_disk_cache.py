"""DiskCache: storage, expiry and tolerance to broken entries."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from aniliberty._cache import DiskCache


class FakeClock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_miss_on_empty_cache_does_not_create_the_directory(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "cache")

    assert cache.get("key") is None
    assert not (tmp_path / "cache").exists()


def test_set_then_get_round_trips_json(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path / "nested" / "cache")
    data = {"name": "Фрирен", "ids": [1, 2], "rating": None}

    cache.set("key", data)

    assert cache.get("key") == data
    assert cache.get("other") is None
    assert cache.directory == tmp_path / "nested" / "cache"


def test_one_file_per_key_named_by_hash_and_no_temporary_files_left(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)

    cache.set('["GET", "https://x/a?b=1/../c"]', [1])
    cache.set("key", [2])
    cache.set("key", [3])

    names = sorted(p.name for p in tmp_path.iterdir())
    assert len(names) == 2
    assert all(len(name) == 64 + len(".json") and name.endswith(".json") for name in names)
    assert cache.get("key") == [3]


def test_entry_expires_after_ttl(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = DiskCache(tmp_path, ttl=60, clock=clock)
    cache.set("key", [1])

    clock.now += 60
    assert cache.get("key") == [1]
    clock.now += 0.001
    assert cache.get("key") is None


def test_without_ttl_entries_never_expire(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = DiskCache(tmp_path, clock=clock)
    cache.set("key", [1])

    clock.now += 10 * 365 * 24 * 3600

    assert cache.get("key") == [1]


def test_entries_outlive_the_cache_object(tmp_path: Path) -> None:
    DiskCache(tmp_path).set("key", {"a": 1})

    assert DiskCache(tmp_path, ttl=3600).get("key") == {"a": 1}


@pytest.mark.parametrize(
    "content",
    ["", "not json", "[1, 2]", '{"data": [1]}', '{"cached_at": "soon", "data": [1]}'],
    ids=["empty", "not-json", "not-an-object", "no-timestamp", "bad-timestamp"],
)
def test_broken_entry_is_a_miss(tmp_path: Path, content: str) -> None:
    cache = DiskCache(tmp_path, ttl=60)
    cache.set("key", [1])
    [path] = tmp_path.iterdir()
    path.write_text(content, encoding="utf-8")

    assert cache.get("key") is None


def test_negative_ttl_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cache_ttl"):
        DiskCache(tmp_path, ttl=-1)


def test_failed_write_raises_and_removes_the_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = DiskCache(tmp_path)

    def fail(src: str, dst: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError, match="disk full"):
        cache.set("key", [1])

    assert list(tmp_path.iterdir()) == []
