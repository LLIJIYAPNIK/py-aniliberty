"""HttpClient.request_raw / stream: non-JSON responses with the same retries and errors."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from aniliberty import AccessBlockedError, HttpClient, NotFoundError, TransportError

Handler = Callable[[httpx.Request], httpx.Response]
TORRENT = b"d8:announce35:http://tracker.example/announce4:infod4:name3:abcee"


class FakeSleep:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def make_client(handler: Handler, sleep: FakeSleep | None = None) -> HttpClient:
    return HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        request_delay=0,
        sleep=sleep or FakeSleep(),
    )


def file_response(content: bytes = TORRENT) -> httpx.Response:
    return httpx.Response(
        200, content=content, headers={"Content-Type": "application/x-bittorrent"}
    )


async def test_request_raw_returns_the_response() -> None:
    response = await make_client(lambda r: file_response()).request_raw("GET", "/f")
    assert response.content == TORRENT
    assert response.headers["Content-Type"] == "application/x-bittorrent"


async def test_request_raw_maps_json_errors() -> None:
    client = make_client(lambda r: httpx.Response(404, json={"message": "No query results"}))
    with pytest.raises(NotFoundError):
        await client.request_raw("GET", "/f")


async def test_request_raw_maps_html_pages() -> None:
    client = make_client(
        lambda r: httpx.Response(403, text="<html></html>", headers={"Content-Type": "text/html"})
    )
    with pytest.raises(AccessBlockedError):
        await client.request_raw("GET", "/f")


async def test_stream_yields_the_body_in_chunks() -> None:
    client = make_client(lambda r: file_response(TORRENT * 1000))
    async with client.stream("GET", "/f") as response:
        body = b"".join([chunk async for chunk in response.aiter_bytes()])
    assert body == TORRENT * 1000


async def test_stream_retries_server_errors_before_yielding() -> None:
    answers = [httpx.Response(503, json={}), file_response()]
    sleep = FakeSleep()
    client = make_client(lambda r: answers.pop(0), sleep)

    async with client.stream("GET", "/f") as response:
        assert await response.aread() == TORRENT
    assert sleep.delays == [1.0]


async def test_stream_raises_on_error_status_with_the_body_read() -> None:
    client = make_client(lambda r: httpx.Response(404, json={"message": "No query results"}))
    with pytest.raises(NotFoundError) as excinfo:
        async with client.stream("GET", "/f"):
            pytest.fail("must not yield an error response")  # pragma: no cover
    assert excinfo.value.payload == {"message": "No query results"}


async def test_stream_raises_on_an_html_page_even_with_200() -> None:
    client = make_client(
        lambda r: httpx.Response(200, text="<html></html>", headers={"Content-Type": "text/html"})
    )
    with pytest.raises(AccessBlockedError):
        async with client.stream("GET", "/f"):
            pytest.fail("must not yield a block page")  # pragma: no cover


async def test_stream_transport_error_is_wrapped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    client = HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        request_delay=0,
        max_retries=0,
    )
    with pytest.raises(TransportError):
        async with client.stream("GET", "/f"):
            pytest.fail("must not yield")  # pragma: no cover


class BrokenStream(httpx.AsyncByteStream):
    """A body that fails after the first chunk, like a dropped connection."""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield TORRENT[:10]
        raise httpx.ReadError("connection reset")


async def test_stream_body_error_surfaces_to_the_reader() -> None:
    client = make_client(
        lambda r: httpx.Response(
            200, stream=BrokenStream(), headers={"Content-Type": "application/x-bittorrent"}
        )
    )
    with pytest.raises(httpx.ReadError):
        async with client.stream("GET", "/f") as response:
            async for _ in response.aiter_bytes():
                pass
