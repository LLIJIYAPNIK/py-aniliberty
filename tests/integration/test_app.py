"""``client.app`` and the HTTP core against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AccessBlockedError, AniLiberty, ApiStatus, NotFoundError, ValidationError

MISSING_ALIAS = "this-alias-does-not-exist-xyz"


@pytest.mark.vcr
async def test_status() -> None:
    async with AniLiberty() as client:
        status = await client.app.status()

    assert isinstance(status, ApiStatus)
    assert status.is_alive is True
    assert "https://aniliberty.top" in status.available_api_endpoints
    assert status.request is not None
    assert status.request.ip == "203.0.113.10"  # scrubbed by conftest._scrub_response
    assert status.request.iso_code


@pytest.mark.vcr
async def test_status_on_mirror() -> None:
    async with AniLiberty(base_url="https://anilibria.top/api/v1") as client:
        status = await client.app.status()

    assert status.is_alive is True


@pytest.mark.vcr
async def test_not_found_is_json_with_accept_header() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError) as excinfo:
            await client.http.request("GET", f"/anime/releases/{MISSING_ALIAS}")

    error = excinfo.value
    assert error.status_code == 404
    assert error.message == "Not found"
    assert error.url.endswith(f"/anime/releases/{MISSING_ALIAS}")
    assert isinstance(error.payload, dict)
    assert error.payload["message"].startswith("No query results for model")


@pytest.mark.vcr
async def test_validation_error_body() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.http.request("GET", "/anime/catalog/releases", params={"limit": 1000})

    error = excinfo.value
    assert error.status_code == 422
    assert list(error.errors) == ["limit"]
    assert "50" in error.errors["limit"][0]


@pytest.mark.vcr
async def test_html_error_page_without_json_accept_header() -> None:
    # Without `Accept: application/json` the backend renders its 404 as an HTML page — the
    # reason the SDK always sends that header (docs/api-notes.md). The SDK can't tell such a
    # page from a WAF block, so it raises AccessBlockedError.
    async with AniLiberty(headers={"Accept": "*/*"}) as client:
        with pytest.raises(AccessBlockedError) as excinfo:
            await client.http.request("GET", f"/anime/releases/{MISSING_ALIAS}")

    assert excinfo.value.status_code == 404
    assert "<html" in excinfo.value.payload.lower()
