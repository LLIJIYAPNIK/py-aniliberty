"""Which SDK methods use the response cache: exactly the ones with a ``refresh`` parameter."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, HttpClient
from aniliberty.resources._base import BaseResource

# Arguments for the methods that need some; every other method is called without any.
ARGS: dict[str, tuple[Any, ...]] = {
    "app.search_releases": ("frieren",),
    "releases.get": (9839,),
    "releases.members": (9839,),
    "genres.get": (1,),
    "genres.releases": (1,),
    "genres.iter_releases": (1,),
    "franchises.get": ("a1b2",),
    "franchises.for_release": (9839,),
}
KWARGS: dict[str, dict[str, Any]] = {
    "releases.list": {"ids": [9839]},
    "releases.iter_list": {"ids": [9839]},
}

CACHED = {
    "app.search_releases",
    "releases.latest",
    "releases.list",
    "releases.iter_list",
    "releases.get",
    "releases.members",
    "catalog.releases",
    "catalog.iter_releases",
    "catalog.references.genres",
    "catalog.references.types",
    "catalog.references.seasons",
    "catalog.references.years",
    "catalog.references.age_ratings",
    "catalog.references.publish_statuses",
    "catalog.references.production_statuses",
    "catalog.references.sorting",
    "schedule.now",
    "schedule.week",
    "genres.list",
    "genres.get",
    "genres.releases",
    "genres.iter_releases",
    "franchises.list",
    "franchises.get",
    "franchises.for_release",
    "teams.list",
    "teams.roles",
    "teams.users",
    "media.videos",
}

# Public reads that must always reach the API: random picks, liveness, HLS links, torrents
# (passkeys), and the user's own data.
NOT_CACHED: dict[str, tuple[Any, ...]] = {
    "app.status": (),
    "releases.random": (),
    "releases.recommended": (),
    "releases.timecodes": (9839,),
    "episodes.get": ("9a1b2c3d-0000-0000-0000-000000000000",),
    "genres.random": (),
    "franchises.random": (),
    "media.promotions": (),
    "torrents.list": (),
    "torrents.get": (1,),
    "torrents.for_release": (9839,),
    "me.profile": (),
    "me.favorites.ids": (),
    "me.collections.ids": (),
    "me.views.timecodes": (),
}


class Recorded(Exception):
    """Raised by the fake ``request`` once it has recorded the call."""


def public_methods(client: AniLiberty) -> Iterator[tuple[str, Callable[..., Any]]]:
    def walk(obj: object, prefix: str) -> Iterator[tuple[str, Callable[..., Any]]]:
        for name, value in vars(obj).items():
            if isinstance(value, BaseResource):
                path = f"{prefix}{name}"
                for method, _ in inspect.getmembers(type(value), predicate=inspect.isfunction):
                    if not method.startswith("_"):
                        yield f"{path}.{method}", getattr(value, method)
                yield from walk(value, f"{path}.")

    yield from walk(client, "")


def resolve(client: AniLiberty, name: str) -> Callable[..., Any]:
    obj: Any = client
    for part in name.split("."):
        obj = getattr(obj, part)
    return obj  # type: ignore[no-any-return]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []

    async def request(self: HttpClient, method: str, path: str, **kwargs: Any) -> Any:
        recorded.append({"method": method, "path": path, **kwargs})
        raise Recorded

    monkeypatch.setattr(HttpClient, "request", request)
    return recorded


async def call(method: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    result = method(*args, **kwargs)
    with pytest.raises(Recorded):
        if inspect.isawaitable(result):
            await result
        else:  # an iter_*() method: the first page is requested on the first item
            await anext(result)


def test_the_methods_with_refresh_are_the_cached_ones() -> None:
    with_refresh = {
        name
        for name, method in public_methods(AniLiberty())
        if "refresh" in inspect.signature(method).parameters
    }

    assert with_refresh == CACHED


@pytest.mark.parametrize("name", sorted(CACHED))
@pytest.mark.parametrize("refresh", [False, True])
async def test_cached_method_passes_cache_and_refresh(
    name: str, refresh: bool, calls: list[dict[str, Any]], tmp_path: Path
) -> None:
    client = AniLiberty(cache_dir=tmp_path)
    method = resolve(client, name)
    kwargs = {**KWARGS.get(name, {}), **({"refresh": True} if refresh else {})}

    await call(method, *ARGS.get(name, ()), **kwargs)

    [recorded] = calls
    assert recorded["method"] == "GET"
    assert recorded["cache"] is True
    assert recorded["refresh"] is refresh


@pytest.mark.parametrize("name", sorted(NOT_CACHED))
async def test_other_reads_never_use_the_cache(
    name: str, calls: list[dict[str, Any]], tmp_path: Path
) -> None:
    client = AniLiberty(cache_dir=tmp_path)

    await call(resolve(client, name), *NOT_CACHED[name])

    [recorded] = calls
    assert not recorded.get("cache")


async def test_client_passes_cache_settings_to_http(tmp_path: Path) -> None:
    async with AniLiberty(cache_dir=tmp_path, cache_ttl=3600) as client:
        assert client.http.cache_dir == tmp_path


def test_cache_is_off_by_default() -> None:
    assert AniLiberty().http.cache_dir is None


async def test_cached_release_end_to_end(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client, cache_dir=tmp_path) as client:
        assert await client.franchises.for_release(9839) == []
        assert await client.franchises.for_release(9839) == []
        assert await client.franchises.for_release(9839, refresh=True) == []

    assert len(seen) == 2
