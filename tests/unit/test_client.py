"""AniLiberty facade: lifecycle, configuration, and resource wiring."""

from __future__ import annotations

import httpx
import pytest

from aniliberty import AniLiberty, ApiStatus, ResponseParseError
from aniliberty.resources import AppResource

STATUS = {
    "request": {"ip": "203.0.113.10", "country": "Russia", "iso_code": "RU", "timezone": "UTC"},
    "is_alive": True,
    "available_api_endpoints": ["https://aniliberty.top"],
}


def mock_http_client(payload: object, status: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_status_returns_model() -> None:
    async with AniLiberty(http_client=mock_http_client(STATUS)) as client:
        status = await client.app.status()

    assert status == ApiStatus.model_validate(STATUS)
    assert status.request is not None
    assert status.request.iso_code == "RU"


async def test_status_tolerates_missing_optional_fields_and_extra_ones() -> None:
    async with AniLiberty(http_client=mock_http_client({"is_alive": False, "new": 1})) as client:
        status = await client.app.status()

    assert status.is_alive is False
    assert status.available_api_endpoints == []
    assert status.request is None


async def test_status_with_unexpected_shape_raises_response_parse_error() -> None:
    payload = {"is_alive": "maybe"}
    async with AniLiberty(http_client=mock_http_client(payload)) as client:
        with pytest.raises(ResponseParseError) as excinfo:
            await client.app.status()

    assert excinfo.value.payload == payload
    assert excinfo.value.url == "https://aniliberty.top/api/v1/app/status"
    assert "ApiStatus" in str(excinfo.value)


async def test_models_are_frozen() -> None:
    status = ApiStatus.model_validate(STATUS)
    with pytest.raises(Exception, match="frozen"):
        status.is_alive = False  # type: ignore[misc]


async def test_base_url_and_headers_are_passed_to_http_client() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=STATUS)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(
        base_url="https://anilibria.top/api/v1/", headers={"X-Test": "1"}, http_client=http_client
    ) as client:
        await client.app.status()

    assert str(seen[0].url) == "https://anilibria.top/api/v1/app/status"
    assert seen[0].headers["X-Test"] == "1"
    assert client.http.base_url == "https://anilibria.top/api/v1"
    # The SDK didn't create this client, so it must not close it.
    assert not http_client.is_closed
    await http_client.aclose()


async def test_context_manager_closes_and_cannot_be_reentered() -> None:
    client = AniLiberty()
    async with client:
        pass

    assert client.http.closed
    with pytest.raises(RuntimeError, match="closed"):
        async with client:
            pass


async def test_explicit_aclose_without_context_manager() -> None:
    client = AniLiberty(http_client=mock_http_client(STATUS))
    assert (await client.app.status()).is_alive
    await client.aclose()

    with pytest.raises(RuntimeError, match="closed"):
        await client.app.status()


def test_resources_declare_their_spec_endpoints() -> None:
    assert AppResource.ENDPOINTS == (("GET", "/app/status"), ("GET", "/app/search/releases"))
    assert isinstance(AniLiberty().app, AppResource)


async def test_search_releases_sends_the_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[])

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        assert await client.app.search_releases("Мастера меча") == []

    assert seen[0].url.path == "/api/v1/app/search/releases"
    assert seen[0].url.params["query"] == "Мастера меча"
    await http_client.aclose()
