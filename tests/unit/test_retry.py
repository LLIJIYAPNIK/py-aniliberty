"""HttpClient: retries with backoff and Retry-After, request pacing, and the concurrency limit.

Time is faked: ``FakeTime.sleep`` records the requested delay and advances ``FakeTime.clock``
instead of waiting, so these tests are deterministic and instant.
"""

from __future__ import annotations

import asyncio
import logging

import httpx
import pytest

from aniliberty import (
    AniLiberty,
    APIError,
    HttpClient,
    RateLimitError,
    ServerError,
    TransportError,
)

Step = httpx.Response | Exception


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.now += delay


class Script:
    """Mock transport handler answering with ``steps`` in order, one per request."""

    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def make_client(script: Script, fake: FakeTime, **kwargs: object) -> HttpClient:
    kwargs.setdefault("request_delay", 0)
    return HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(script)),
        sleep=fake.sleep,
        clock=fake.clock,
        **kwargs,  # type: ignore[arg-type]
    )


OK = httpx.Response(200, json={"ok": True})


# --- retries ----------------------------------------------------------------------------------


async def test_429_with_retry_after_is_retried_after_that_delay() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "7"}), OK)
    fake = FakeTime()

    assert await make_client(script, fake).request("GET", "/x") == {"ok": True}
    assert fake.sleeps == [7.0]
    assert len(script.requests) == 2


async def test_429_without_retry_after_backs_off_exponentially_then_raises() -> None:
    script = Script(*[httpx.Response(429, json={"message": "Too Many Attempts."})] * 4)
    fake = FakeTime()

    with pytest.raises(RateLimitError) as excinfo:
        await make_client(script, fake).request("GET", "/x")

    assert fake.sleeps == [1.0, 2.0, 4.0]
    assert len(script.requests) == 4  # the first attempt + 3 retries
    assert excinfo.value.retry_after is None
    assert excinfo.value.message == "Too Many Attempts."


async def test_retry_after_as_http_date_is_measured_from_the_response_date() -> None:
    headers = {
        "Date": "Fri, 16 Oct 2026 05:00:00 GMT",
        "Retry-After": "Fri, 16 Oct 2026 05:00:30 GMT",
    }
    script = Script(httpx.Response(429, headers=headers), OK)
    fake = FakeTime()

    await make_client(script, fake).request("GET", "/x")

    assert fake.sleeps == [30.0]


async def test_retry_after_http_date_in_the_past_retries_immediately() -> None:
    script = Script(
        httpx.Response(429, headers={"Retry-After": "Wed, 01 Jan 2020 00:00:00 GMT"}), OK
    )
    fake = FakeTime()

    await make_client(script, fake).request("GET", "/x")

    assert fake.sleeps == [0.0]


async def test_unparseable_retry_after_falls_back_to_backoff() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "soon"}), OK)
    fake = FakeTime()

    await make_client(script, fake, retry_base_delay=0.5).request("GET", "/x")

    assert fake.sleeps == [0.5]


async def test_retry_after_longer_than_the_cap_raises_without_waiting() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "3600"}))
    fake = FakeTime()

    with pytest.raises(RateLimitError) as excinfo:
        await make_client(script, fake).request("GET", "/x")

    assert fake.sleeps == []
    assert excinfo.value.retry_after == 3600.0


async def test_429_is_retried_for_non_idempotent_methods_too() -> None:
    script = Script(httpx.Response(429, headers={"Retry-After": "1"}), OK)
    fake = FakeTime()

    await make_client(script, fake).request("POST", "/x", json={})

    assert len(script.requests) == 2


@pytest.mark.parametrize(
    "first",
    [
        httpx.Response(500, json={"message": "Server Error"}),
        httpx.Response(503, text="<html>Bad gateway</html>", headers={"Content-Type": "text/html"}),
    ],
)
async def test_5xx_is_retried_for_get(first: httpx.Response) -> None:
    script = Script(first, OK)
    fake = FakeTime()

    assert await make_client(script, fake).request("GET", "/x") == {"ok": True}
    assert fake.sleeps == [1.0]


async def test_5xx_exhausting_retries_raises_server_error() -> None:
    script = Script(*[httpx.Response(502, json={})] * 3)
    fake = FakeTime()

    with pytest.raises(ServerError):
        await make_client(script, fake, max_retries=2).request("GET", "/x")

    assert fake.sleeps == [1.0, 2.0]


async def test_5xx_is_not_retried_for_post() -> None:
    script = Script(httpx.Response(500, json={}))
    fake = FakeTime()

    with pytest.raises(ServerError):
        await make_client(script, fake).request("POST", "/x", json={})

    assert len(script.requests) == 1
    assert fake.sleeps == []


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404, json={"message": "No query results"}),
        httpx.Response(422, json={"errors": {"limit": ["bad"]}}),
        httpx.Response(403, text="<html></html>", headers={"Content-Type": "text/html"}),
    ],
)
async def test_client_errors_and_block_pages_are_not_retried(response: httpx.Response) -> None:
    script = Script(response)
    fake = FakeTime()

    with pytest.raises(APIError) as excinfo:
        await make_client(script, fake).request("GET", "/x")

    assert type(excinfo.value) is not ServerError
    assert len(script.requests) == 1
    assert fake.sleeps == []


async def test_network_errors_are_retried_for_get() -> None:
    script = Script(httpx.ConnectError("refused"), httpx.ReadTimeout("slow"), OK)
    fake = FakeTime()

    assert await make_client(script, fake).request("GET", "/x") == {"ok": True}
    assert fake.sleeps == [1.0, 2.0]


async def test_network_errors_exhausting_retries_raise_transport_error() -> None:
    last = httpx.ReadTimeout("slow")
    script = Script(httpx.ConnectError("refused"), last)
    fake = FakeTime()

    with pytest.raises(TransportError) as excinfo:
        await make_client(script, fake, max_retries=1).request("GET", "/x")

    assert excinfo.value.__cause__ is last


async def test_network_errors_are_not_retried_for_post() -> None:
    script = Script(httpx.ConnectError("refused"))
    fake = FakeTime()

    with pytest.raises(TransportError):
        await make_client(script, fake).request("POST", "/x", json={})

    assert len(script.requests) == 1


async def test_max_retries_zero_disables_retries() -> None:
    script = Script(httpx.Response(503, json={}))
    fake = FakeTime()

    with pytest.raises(ServerError):
        await make_client(script, fake, max_retries=0).request("GET", "/x")

    assert fake.sleeps == []


async def test_retries_are_logged(caplog: pytest.LogCaptureFixture) -> None:
    script = Script(httpx.Response(503, json={}), OK)
    with caplog.at_level(logging.INFO, logger="aniliberty"):
        await make_client(script, FakeTime()).request("GET", "/x")

    assert any(
        "HTTP 503, retrying in 1.0s (retry 1 of 3)" in r.getMessage() for r in caplog.records
    )


# --- pacing -----------------------------------------------------------------------------------


async def test_consecutive_requests_are_spaced_by_request_delay() -> None:
    script = Script(OK, OK, OK)
    fake = FakeTime()
    client = make_client(script, fake, request_delay=0.25)

    await client.request("GET", "/x")  # first request: no wait
    fake.now += 0.1  # the caller did something else for 0.1 s
    await client.request("GET", "/x")
    await client.request("GET", "/x")

    assert fake.sleeps == pytest.approx([0.15, 0.25])


async def test_no_pacing_wait_when_requests_are_already_far_apart() -> None:
    script = Script(OK, OK)
    fake = FakeTime()
    client = make_client(script, fake, request_delay=0.25)

    await client.request("GET", "/x")
    fake.now += 5
    await client.request("GET", "/x")

    assert fake.sleeps == []


async def test_default_pacing_is_a_tenth_of_a_second() -> None:
    script = Script(OK, OK)
    fake = FakeTime()
    client = HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(script)),
        sleep=fake.sleep,
        clock=fake.clock,
    )

    await client.request("GET", "/x")
    await client.request("GET", "/x")

    assert fake.sleeps == pytest.approx([0.1])


# --- concurrency ------------------------------------------------------------------------------


class PeakTracker:
    """Async mock handler that records how many requests were in flight at once."""

    def __init__(self, latency: float = 0.01) -> None:
        self.latency = latency
        self.in_flight = 0
        self.peak = 0

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        await asyncio.sleep(self.latency)
        self.in_flight -= 1
        return httpx.Response(200, json={"is_alive": True})


@pytest.mark.parametrize("limit", [1, 3])
async def test_requests_in_flight_never_exceed_max_concurrency(limit: int) -> None:
    tracker = PeakTracker()
    client = HttpClient(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(tracker)),
        max_concurrency=limit,
        request_delay=0,
    )
    await asyncio.gather(*(client.request("GET", "/x") for _ in range(10)))

    assert tracker.peak == limit


async def test_facade_passes_max_concurrency_through() -> None:
    # Responses must take longer than the facade's real 0.1 s pacing delay, otherwise the
    # requests never overlap and the limit isn't exercised.
    tracker = PeakTracker(latency=0.3)
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(tracker))
    async with AniLiberty(max_concurrency=2, http_client=http_client) as client:
        await asyncio.gather(*(client.app.status() for _ in range(6)))

    assert tracker.peak == 2
    await http_client.aclose()


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"max_concurrency": 0}, "max_concurrency"),
        ({"request_delay": -1}, "request_delay"),
        ({"max_retries": -1}, "max_retries"),
        ({"retry_base_delay": -0.5}, "retry_base_delay"),
        ({"max_retry_after": -1}, "max_retry_after"),
    ],
)
def test_invalid_limits_are_rejected(kwargs: dict[str, float], match: str) -> None:
    with pytest.raises(ValueError, match=match):
        HttpClient(**kwargs)  # type: ignore[arg-type]
