"""Concurrency: running many requests at once with asyncio.gather / TaskGroup.

One AniLiberty client can be shared by any number of coroutines. It keeps at most
max_concurrency requests in flight (5 by default) and starts consecutive requests at least
0.1 s apart, so a big gather is polite to the API without any limiting on your side. This
script measures that: wall time, request count and the peak number of requests in flight.
"""

import asyncio
import time

import httpx

from aniliberty import AniLiberty, NotFoundError


class InFlight:
    """Counts requests in flight with httpx event hooks (more in 15_custom_http_client...)."""

    def __init__(self) -> None:
        self.now = self.peak = self.total = 0

    async def on_request(self, request: httpx.Request) -> None:
        self.now += 1
        self.total += 1
        self.peak = max(self.peak, self.now)

    async def on_response(self, response: httpx.Response) -> None:
        # Fires when the response headers arrive — the moment the SDK frees the slot.
        self.now -= 1

    def client(self) -> httpx.AsyncClient:
        hooks = {"request": [self.on_request], "response": [self.on_response]}
        return httpx.AsyncClient(timeout=30.0, event_hooks=hooks)


async def fetch_all(ids: list[int], *, max_concurrency: int) -> None:
    counter = InFlight()
    async with (
        counter.client() as http_client,
        AniLiberty(http_client=http_client, max_concurrency=max_concurrency) as client,
    ):
        started = time.perf_counter()
        # gather starts every coroutine at once; the client queues the requests beyond
        # max_concurrency, so there's no need for your own semaphore.
        releases = await asyncio.gather(*(client.releases.get(i) for i in ids))
        elapsed = time.perf_counter() - started
    print(
        f"  max_concurrency={max_concurrency}: {len(releases)} releases in {elapsed:.1f}s, "
        f"{counter.total} requests, peak {counter.peak} in flight"
    )


async def main() -> None:
    async with AniLiberty() as client:
        ids = [release.id for release in await client.releases.latest(limit=20)]

        # Sequential awaits: each request waits for the previous one to finish.
        started = time.perf_counter()
        for release_id in ids:
            await client.releases.get(release_id)
        print(f"Sequential: {len(ids)} releases in {time.perf_counter() - started:.1f}s")

    # The same 20 requests concurrently, with different limits. The peak never exceeds
    # max_concurrency. But the API answers fast, so the real bound here is the pacing: request
    # *starts* are spaced 0.1 s apart, about 10 requests/s at most, however high the limit.
    # Concurrency pays off when responses are slow (big pages, slow network), not as a way
    # around the pacing — which is there on purpose, to keep the API from rate-limiting you.
    print("Concurrent (asyncio.gather):")
    for limit in (1, 5, 20):
        await fetch_all(ids, max_concurrency=limit)

    async with AniLiberty() as client:
        # One failure in gather: by default the first exception propagates, and the other
        # coroutines keep running unobserved in the background. return_exceptions=True
        # gives you every result or exception in order instead.
        results = await asyncio.gather(
            client.releases.get(ids[0]),
            client.releases.get("no-such-release"),
            client.releases.get(ids[1]),
            return_exceptions=True,
        )
        print("gather(return_exceptions=True):", [type(r).__name__ for r in results])

        # TaskGroup (Python 3.11+) is the structured alternative: when one task fails, the
        # others are cancelled, and the errors arrive together as an ExceptionGroup —
        # handle them with except*. Only one NotFoundError makes it into the group below:
        # the first failure cancelled the other tasks before their responses arrived.
        try:
            async with asyncio.TaskGroup() as group:
                for alias in ("sousou-no-frieren", "no-such-release", "no-such-release-2"):
                    group.create_task(client.releases.get(alias))
        except* NotFoundError as errors:
            print(f"TaskGroup: {len(errors.exceptions)} NotFoundError(s) in the group")

        # A deadline for a whole batch: asyncio.timeout cancels whatever is still running
        # or queued. Here 20 requests can't fit into 0.5 s because of the pacing alone.
        try:
            async with asyncio.timeout(0.5):
                await asyncio.gather(*(client.releases.get(i) for i in ids))
        except TimeoutError:
            print("asyncio.timeout(0.5): batch cancelled")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Sequential: 20 releases in 2.3s
# Concurrent (asyncio.gather):
#   max_concurrency=1: 20 releases in 2.7s, 20 requests, peak 1 in flight
#   max_concurrency=5: 20 releases in 2.1s, 20 requests, peak 5 in flight
#   max_concurrency=20: 20 releases in 2.1s, 20 requests, peak 5 in flight
# gather(return_exceptions=True): ['Release', 'NotFoundError', 'Release']
# TaskGroup: 1 NotFoundError(s) in the group
# asyncio.timeout(0.5): batch cancelled
