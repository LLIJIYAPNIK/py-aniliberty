"""HttpClient: URLs, headers, response decoding and status → exception mapping."""

from __future__ import annotations

import logging
from collections.abc import Callable

import httpx
import pytest

from aniliberty import (
    AccessBlockedError,
    APIError,
    AuthRequiredError,
    HttpClient,
    NotFoundError,
    RateLimitError,
    ResponseParseError,
    ServerError,
    TransportError,
    ValidationError,
    __version__,
)

Handler = Callable[[httpx.Request], httpx.Response]
HTML = "<!DOCTYPE html><html><head><title>Just a moment...</title></head></html>"


def make_client(handler: Handler, **kwargs: object) -> HttpClient:
    # Retries and pacing are covered in test_retry.py; here every response is mapped as is.
    kwargs.setdefault("max_retries", 0)
    kwargs.setdefault("request_delay", 0)
    transport = httpx.MockTransport(handler)
    return HttpClient(http_client=httpx.AsyncClient(transport=transport), **kwargs)  # type: ignore[arg-type]


def respond(response: httpx.Response) -> Handler:
    return lambda request: response


async def request_error(response: httpx.Response) -> APIError:
    client = make_client(respond(response))
    with pytest.raises(APIError) as excinfo:
        await client.request("GET", "/x")
    return excinfo.value


# --- URLs and headers -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("base_url", "path", "expected"),
    [
        (
            "https://aniliberty.top/api/v1",
            "/app/status",
            "https://aniliberty.top/api/v1/app/status",
        ),
        (
            "https://aniliberty.top/api/v1/",
            "/app/status",
            "https://aniliberty.top/api/v1/app/status",
        ),
        ("https://aniliberty.top/api/v1", "app/status", "https://aniliberty.top/api/v1/app/status"),
        # The spec spells the teams list as `/teams/`; the trailing slash must survive.
        ("https://aniliberty.top/api/v1", "/teams/", "https://aniliberty.top/api/v1/teams/"),
    ],
)
def test_url_joins_base_and_path(base_url: str, path: str, expected: str) -> None:
    assert HttpClient(base_url=base_url).url(path) == expected


def test_default_base_url_is_main_server() -> None:
    assert HttpClient().base_url == "https://aniliberty.top/api/v1"


async def test_sends_default_headers() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    await make_client(handler).request("GET", "/app/status")

    assert seen[0].headers["Accept"] == "application/json"
    assert seen[0].headers["User-Agent"].startswith(f"py-aniliberty/{__version__} ")


async def test_custom_headers_override_defaults_case_insensitively() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    client = make_client(handler, headers={"user-agent": "my-app/1.0", "X-Extra": "1"})
    await client.request("GET", "/app/status")

    assert seen[0].headers.get_list("User-Agent") == ["my-app/1.0"]
    assert seen[0].headers["X-Extra"] == "1"
    assert seen[0].headers["Accept"] == "application/json"


async def test_passes_method_params_and_json_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"ok": True})

    result = await make_client(handler).request(
        "post", "/anime/catalog/releases", params={"page": 2}, json={"limit": 5}
    )

    assert result == {"ok": True}
    assert seen[0].method == "POST"
    assert seen[0].url.params["page"] == "2"
    assert seen[0].content == b'{"limit":5}'


async def test_logs_requests_at_debug_level(caplog: pytest.LogCaptureFixture) -> None:
    client = make_client(respond(httpx.Response(200, json={})))
    with caplog.at_level(logging.DEBUG, logger="aniliberty"):
        await client.request("GET", "/app/status")

    assert any("/app/status -> 200" in r.getMessage() for r in caplog.records)


# --- successful responses ---------------------------------------------------------------------


async def test_returns_decoded_json_list() -> None:
    client = make_client(respond(httpx.Response(200, json=[1, 2])))
    assert await client.request("GET", "/x") == [1, 2]


async def test_empty_body_returns_none() -> None:
    client = make_client(respond(httpx.Response(204)))
    assert await client.request("DELETE", "/x") is None


async def test_invalid_json_raises_response_parse_error_with_raw_text() -> None:
    response = httpx.Response(200, text="{not json", headers={"Content-Type": "application/json"})
    client = make_client(respond(response))

    with pytest.raises(ResponseParseError) as excinfo:
        await client.request("GET", "/x")

    assert excinfo.value.payload == "{not json"
    assert excinfo.value.url == "https://aniliberty.top/api/v1/x"
    assert excinfo.value.__cause__ is not None


# --- error statuses ---------------------------------------------------------------------------


async def test_404_raises_not_found_keeping_api_message_in_payload() -> None:
    body = {"message": "No query results for model [Release]."}
    error = await request_error(httpx.Response(404, json=body))

    assert type(error) is NotFoundError
    assert error.status_code == 404
    assert error.message == "Not found"
    assert error.payload == body
    assert error.method == "GET"
    assert error.url == "https://aniliberty.top/api/v1/x"


async def test_422_raises_validation_error_with_field_errors() -> None:
    body = {"errors": {"limit": ["Поле limit должно быть числом.", "Ещё одно."]}}
    error = await request_error(httpx.Response(422, json=body))

    assert type(error) is ValidationError
    assert error.errors == {"limit": ["Поле limit должно быть числом.", "Ещё одно."]}
    assert error.message == "limit: Поле limit должно быть числом. Ещё одно."


@pytest.mark.parametrize(
    ("body", "expected_errors"),
    [
        ({"errors": {"limit": "single message"}}, {"limit": ["single message"]}),
        ({"errors": ["not", "a", "dict"]}, {}),
        ({"message": "The given data was invalid."}, {}),
        ("plain text", {}),
    ],
)
async def test_422_tolerates_unexpected_error_shapes(
    body: object, expected_errors: dict[str, list[str]]
) -> None:
    response = (
        httpx.Response(422, text=body) if isinstance(body, str) else httpx.Response(422, json=body)
    )
    error = await request_error(response)

    assert isinstance(error, ValidationError)
    assert error.errors == expected_errors
    assert error.message  # falls back to the API message or the reason phrase


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"Retry-After": "7"}, 7.0),
        ({"Retry-After": "1.5"}, 1.5),
        ({}, None),
        ({"Retry-After": "soon"}, None),
    ],
)
async def test_429_raises_rate_limit_error_with_retry_after(
    headers: dict[str, str], expected: float | None
) -> None:
    error = await request_error(httpx.Response(429, json={}, headers=headers))

    assert type(error) is RateLimitError
    assert error.retry_after == expected


@pytest.mark.parametrize("status", [401, 403])
async def test_401_and_json_403_raise_auth_required(status: int) -> None:
    error = await request_error(httpx.Response(status, json={"message": "Unauthenticated."}))

    assert type(error) is AuthRequiredError
    assert error.message == "Unauthenticated."


@pytest.mark.parametrize("status", [200, 403, 404])
async def test_html_page_raises_access_blocked(status: int) -> None:
    response = httpx.Response(
        status, text=HTML, headers={"Content-Type": "text/html; charset=UTF-8"}
    )
    error = await request_error(response)

    assert type(error) is AccessBlockedError
    assert error.status_code == status
    assert error.payload == HTML


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, json={"message": "Server Error"}),
        # Cloudflare renders origin failures as HTML pages; those are server errors, not blocks.
        httpx.Response(502, text=HTML, headers={"Content-Type": "text/html"}),
    ],
)
async def test_5xx_raises_server_error(response: httpx.Response) -> None:
    error = await request_error(response)

    assert type(error) is ServerError
    assert error.status_code == response.status_code


async def test_other_statuses_raise_plain_api_error_with_reason_phrase() -> None:
    error = await request_error(httpx.Response(405, text=""))

    assert type(error) is APIError
    assert error.message == "Method Not Allowed"
    assert str(error) == "HTTP 405: Method Not Allowed (GET https://aniliberty.top/api/v1/x)"


# --- transport errors and lifecycle -----------------------------------------------------------


@pytest.mark.parametrize(
    "exc", [httpx.ConnectError("connection refused"), httpx.ReadTimeout("timed out")]
)
async def test_transport_failures_raise_transport_error(exc: httpx.TransportError) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    with pytest.raises(TransportError) as excinfo:
        await make_client(handler).request("GET", "/x")

    assert excinfo.value.__cause__ is exc
    assert excinfo.value.method == "GET"
    assert excinfo.value.url == "https://aniliberty.top/api/v1/x"
    assert type(exc).__name__ in str(excinfo.value)


async def test_request_after_close_raises_runtime_error() -> None:
    client = make_client(respond(httpx.Response(200, json={})))
    await client.aclose()

    with pytest.raises(RuntimeError, match="closed"):
        await client.request("GET", "/x")


async def test_aclose_closes_owned_client_once() -> None:
    client = HttpClient()
    await client.aclose()
    await client.aclose()

    assert client.closed
    assert client._client.is_closed


async def test_aclose_leaves_user_client_open() -> None:
    user_client = httpx.AsyncClient(transport=httpx.MockTransport(respond(httpx.Response(200))))
    client = HttpClient(http_client=user_client)
    await client.aclose()

    assert client.closed
    assert not user_client.is_closed
    await user_client.aclose()
