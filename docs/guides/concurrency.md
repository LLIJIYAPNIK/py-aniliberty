# Concurrency

The SDK is async-only, and one [`AniLiberty`][aniliberty.AniLiberty] client is meant to be
shared by every coroutine in your program. Run requests concurrently with the usual asyncio
tools — `asyncio.gather`, `asyncio.TaskGroup` — and let the client keep the load on the API
reasonable.

[`examples/13_concurrency_gather.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/13_concurrency_gather.py)
is a runnable version of this page.

## What the client limits for you

Every request — from any resource, and from `client.http` — goes through the same
[`HttpClient`][aniliberty.HttpClient], which enforces two limits:

| Limit | Default | Set with |
|---|---|---|
| Requests in flight at once | 5 | `AniLiberty(max_concurrency=...)` |
| Time between the starts of two consecutive requests | 0.1 s | fixed |

Requests over the concurrency limit wait for a free slot; a slot is held until the response
headers arrive. The pacing on top means **at most about 10 requests per second per client**,
however many you start at once. So there's no need for your own semaphore around SDK calls:

```python
releases = await asyncio.gather(*(client.releases.get(i) for i in ids))
```

Retries (see [Errors and retries](errors.md)) go through the same limits.

## How much faster is it?

Twenty `client.releases.get()` calls, measured on 2026-10-16:

| How | Time | Peak in flight |
|---|---|---|
| sequential `await` in a loop | 2.3 s | 1 |
| `gather`, `max_concurrency=1` | 2.7 s | 1 |
| `gather`, `max_concurrency=5` (default) | 2.1 s | 5 |
| `gather`, `max_concurrency=20` | 2.1 s | 5–6 |

Timings vary by a few tenths of a second between runs. The API answers single releases
quickly, so here the pacing — not the concurrency limit — is
what bounds the rate: 20 requests can't start in less than 1.9 s. Concurrency pays off when
responses are slow (large catalog pages, a slow network); it is not a way around the pacing,
which is there on purpose so the API doesn't rate-limit you.

Raising `max_concurrency` above the default rarely helps for that reason. Setting it to `1`
makes requests strictly sequential even if your code gathers.

## `gather` vs `TaskGroup` when something fails

By default `asyncio.gather` raises the first exception and leaves the other coroutines
running in the background, their results lost. Pass `return_exceptions=True` to get every
result or exception, in order:

```python
results = await asyncio.gather(
    client.releases.get(9542),
    client.releases.get("no-such-release"),
    return_exceptions=True,
)
# [Release(...), NotFoundError(...)]
releases = [r for r in results if not isinstance(r, BaseException)]
```

`asyncio.TaskGroup` (Python 3.11+) cancels the remaining tasks as soon as one fails and raises
the errors together as an `ExceptionGroup`:

```python
try:
    async with asyncio.TaskGroup() as group:
        tasks = [group.create_task(client.releases.get(a)) for a in aliases]
except* NotFoundError as errors:
    ...  # errors.exceptions — the failures that happened before the rest was cancelled
```

Use `gather(return_exceptions=True)` when you want everything that can be fetched, and
`TaskGroup` when one failure makes the whole batch pointless.

## A deadline for a batch

`asyncio.timeout` cancels whatever is still running or queued, including requests waiting for
a slot or for the pacing:

```python
try:
    async with asyncio.timeout(5):
        releases = await asyncio.gather(*(client.releases.get(i) for i in ids))
except TimeoutError:
    ...
```

This is separate from the client's `timeout`, which applies to each attempt of each request —
see [Errors and retries](errors.md#timeouts).

## Do and don't

- **Do** create one client and share it. Each `AniLiberty` has its own limits and its own
  connection pool: a client per task multiplies the load on the API and throws away
  keep-alive connections.
- **Do** fetch pages concurrently when you know how many there are — see
  [Pagination](pagination.md#fetching-pages-concurrently).
- **Don't** use one client from several threads or event loops. Create and use it inside one
  event loop; from synchronous code, run your async entry point with `asyncio.run()`.
