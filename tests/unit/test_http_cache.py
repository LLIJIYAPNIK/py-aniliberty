"""HttpClient's response cache: what is cached, under which key, and for how long."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
import pytest

from aniliberty import HttpClient, NotFoundError
from aniliberty._cache import DiskCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


class Api:
    """A mock API answering every request with a new number, so a cached answer shows."""

    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.status = status
        self.body = body

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.body is not None:
            return httpx.Response(self.status, content=self.body)
        return httpx.Response(self.status, json={"n": len(self.requests)})


def make_client(api: Api, cache_dir: Path | None, **kwargs: Any) -> HttpClient:
    return HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(api)),
        cache_dir=cache_dir,
        max_retries=0,
        request_delay=0,
        **kwargs,
    )


async def test_repeated_request_is_served_from_cache(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path)

    first = await client.request("GET", "/anime/franchises", cache=True)
    second = await client.request("GET", "/anime/franchises", cache=True)

    assert first == second == {"n": 1}
    assert len(api.requests) == 1


async def test_cache_is_shared_through_the_directory(tmp_path: Path) -> None:
    await make_client(Api(), tmp_path).request("GET", "/x", cache=True)
    api = Api()

    assert await make_client(api, tmp_path).request("GET", "/x", cache=True) == {"n": 1}
    assert api.requests == []


async def test_refresh_bypasses_the_cache_and_replaces_the_entry(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path)
    await client.request("GET", "/x", cache=True)

    refreshed = await client.request("GET", "/x", cache=True, refresh=True)
    cached = await client.request("GET", "/x", cache=True)

    assert refreshed == cached == {"n": 2}
    assert len(api.requests) == 2


async def test_stale_entry_is_fetched_again(tmp_path: Path) -> None:
    api = Api()
    clock = FakeClock()
    client = make_client(api, tmp_path, cache_ttl=60, cache_clock=clock)
    await client.request("GET", "/x", cache=True)

    clock.now += 30
    assert await client.request("GET", "/x", cache=True) == {"n": 1}
    clock.now += 31
    assert await client.request("GET", "/x", cache=True) == {"n": 2}


async def test_query_parameter_order_does_not_matter(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path)

    await client.request("GET", "/x", params={"a": "1", "b": "2"}, cache=True)
    await client.request("GET", "/x", params={"b": "2", "a": "1"}, cache=True)

    assert len(api.requests) == 1


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/x", {"a": "2"}),
        ("/x", None),
        ("/y", {"a": "1"}),
    ],
)
async def test_different_requests_are_cached_separately(
    tmp_path: Path, path: str, params: dict[str, str] | None
) -> None:
    api = Api()
    client = make_client(api, tmp_path)
    await client.request("GET", "/x", params={"a": "1"}, cache=True)

    assert await client.request("GET", path, params=params, cache=True) == {"n": 2}


async def test_base_url_is_part_of_the_key(tmp_path: Path) -> None:
    api = Api()
    await make_client(api, tmp_path).request("GET", "/x", cache=True)

    mirror = make_client(api, tmp_path, base_url="https://anilibria.top/api/v1")

    assert await mirror.request("GET", "/x", cache=True) == {"n": 2}


@pytest.mark.parametrize(
    "kwargs",
    [
        {},  # the SDK's own non-cacheable methods don't pass cache=True
        {"cache": False},
    ],
)
async def test_nothing_is_cached_without_cache_true(tmp_path: Path, kwargs: Any) -> None:
    api = Api()
    client = make_client(api, tmp_path)

    await client.request("GET", "/x", **kwargs)
    await client.request("GET", "/x", **kwargs)

    assert len(api.requests) == 2
    assert list(tmp_path.iterdir()) == []


async def test_nothing_is_cached_without_cache_dir() -> None:
    api = Api()
    client = make_client(api, None)

    await client.request("GET", "/x", cache=True)
    await client.request("GET", "/x", cache=True)

    assert len(api.requests) == 2
    assert client.cache_dir is None


async def test_cache_dir_property(tmp_path: Path) -> None:
    assert make_client(Api(), tmp_path / "c").cache_dir == tmp_path / "c"


@pytest.mark.parametrize("method", ["POST", "DELETE"])
async def test_only_get_is_cached(tmp_path: Path, method: str) -> None:
    api = Api()
    client = make_client(api, tmp_path)

    await client.request(method, "/x", cache=True)
    await client.request(method, "/x", cache=True)

    assert len(api.requests) == 2


async def test_request_with_a_body_is_not_cached(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path)

    await client.request("GET", "/x", json={"a": 1}, cache=True)
    await client.request("GET", "/x", json={"a": 1}, cache=True)

    assert len(api.requests) == 2


async def test_requests_with_a_session_token_are_never_cached(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path, token="secret-token")

    await client.request("GET", "/x", cache=True)
    await client.request("GET", "/x", cache=True)

    assert len(api.requests) == 2
    assert all(r.headers["Authorization"] == "Bearer secret-token" for r in api.requests)
    assert list(tmp_path.iterdir()) == []


async def test_entry_cached_before_login_is_not_served_while_logged_in(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path)
    await client.request("GET", "/x", cache=True)

    client.token = "secret-token"
    assert await client.request("GET", "/x", cache=True) == {"n": 2}
    client.token = None
    assert await client.request("GET", "/x", cache=True) == {"n": 1}


async def test_request_sent_without_the_token_is_cached(tmp_path: Path) -> None:
    api = Api()
    client = make_client(api, tmp_path, token="secret-token")

    await client.request("GET", "/x", with_token=False, cache=True)
    await client.request("GET", "/x", with_token=False, cache=True)

    assert len(api.requests) == 1
    assert "Authorization" not in api.requests[0].headers


async def test_errors_are_not_cached(tmp_path: Path) -> None:
    api = Api(status=404)
    client = make_client(api, tmp_path)

    for _ in range(2):
        with pytest.raises(NotFoundError):
            await client.request("GET", "/x", cache=True)

    assert len(api.requests) == 2
    assert list(tmp_path.iterdir()) == []


async def test_empty_body_is_not_cached(tmp_path: Path) -> None:
    api = Api(body=b"")
    client = make_client(api, tmp_path)

    assert await client.request("GET", "/x", cache=True) is None
    assert await client.request("GET", "/x", cache=True) is None

    assert len(api.requests) == 2


async def test_empty_list_is_cached(tmp_path: Path) -> None:
    api = Api(body=b"[]")
    client = make_client(api, tmp_path)

    assert await client.request("GET", "/x", cache=True) == []
    assert await client.request("GET", "/x", cache=True) == []

    assert len(api.requests) == 1


async def test_failed_cache_write_is_logged_and_the_response_still_returned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(self: DiskCache, key: str, data: Any) -> None:
        raise PermissionError("read-only")

    monkeypatch.setattr(DiskCache, "set", fail)
    client = make_client(Api(), tmp_path)

    with caplog.at_level(logging.WARNING, logger="aniliberty"):
        assert await client.request("GET", "/x", cache=True) == {"n": 1}

    assert "Couldn't write to the response cache" in caplog.text
    assert "read-only" in caplog.text


async def test_cache_hit_is_logged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    client = make_client(Api(), tmp_path)
    await client.request("GET", "/x", cache=True)

    with caplog.at_level(logging.DEBUG, logger="aniliberty"):
        await client.request("GET", "/x", cache=True)

    assert "GET https://aniliberty.top/api/v1/x: from cache" in caplog.text


def test_negative_ttl_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cache_ttl"):
        HttpClient(cache_dir=tmp_path, cache_ttl=-1)
