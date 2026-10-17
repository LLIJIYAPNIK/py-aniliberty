# Response cache

Much of the API's data changes rarely — franchises, genres, the catalog's reference lists, a
finished release — but an application may ask for it again and again: a website showing a
franchise block on every page view, a matcher trying several spellings of one title. The SDK
can keep such responses on disk and answer repeated calls from there.

[`examples/24_response_cache.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/24_response_cache.py)
is a runnable version of this page.

## Turning it on

The cache is off by default. Give the client a directory and, usually, a lifetime:

```python
async with AniLiberty(cache_dir=".aniliberty_cache", cache_ttl=6 * 3600) as client:
    franchises = await client.franchises.for_release(9839)  # cached if fresh
    franchises = await client.franchises.for_release(9839, refresh=True)  # straight to the API
```

| Parameter | Default | Meaning |
|---|---|---|
| `cache_dir` | `None` | Directory for cache files, created on the first write. `None` disables the cache. |
| `cache_ttl` | `None` | Seconds a cached response stays fresh. `None` — forever, until `refresh=True`. |

A stale entry isn't an error: the call simply goes to the API and the new response replaces
it. `refresh=True` does the same before the TTL runs out.

The cache lives only in files — nothing is kept in memory — so it survives restarts and is
shared by every client and every process pointed at the same directory. Writes are atomic,
so concurrent processes never read half an entry.

## What is cached

A method uses the cache exactly when it has a `refresh` parameter:

| Namespace | Cached methods |
|---|---|
| `client.app` | `search_releases()` |
| `client.releases` | `latest()`, `get()`, `members()`, `list()`, `iter_list()` |
| `client.catalog` | `releases()`, `iter_releases()`, every `references.*()` |
| `client.schedule` | `now()`, `week()` |
| `client.genres` | `list()`, `get()`, `releases()`, `iter_releases()` |
| `client.franchises` | `list()`, `get()`, `for_release()` |
| `client.teams` | `list()`, `roles()`, `users()` |
| `client.media` | `videos()` |

Everything else always goes to the API:

- **random picks** — `releases.random()`, `releases.recommended()` (random without a
  `release`), `genres.random()`, `franchises.random()`, `media.promotions()` (shuffled on every
  call): caching them would freeze the "random" result;
- `app.status()` — it reports whether the API is alive right now;
- `episodes.get()` — HLS links are best fetched fresh. Note that `releases.get()` includes the
  release's episodes, links and all, so with a long TTL those may be old too;
- **torrents** — their magnet links carry the account's passkey when logged in, and the
  `.torrent` files and RSS feeds aren't JSON;
- **everything account-related** — `client.me.*`, `releases.timecodes()`,
  `releases.ratings.*`, `episodes.timecode()`, `client.auth.*`.

And **while a session token is set** (`client.token`, after `client.auth.login()` or
`AniLiberty(token=...)`), no request uses the cache at all — not even the cached methods
above. With a token, the API puts user-specific details into public responses, and those
must never end up in a file another user's client could read. A client used both logged-in
and anonymously reads and writes the cache only while anonymous.

`client.http.request("GET", path, cache=True)` opts a raw request into the same cache, under
the same rules.

## How entries are stored

- **One file per request**, named by the SHA-256 of its key: the method, the full URL
  (including `base_url`, so a mirror has entries of its own) and the query parameters in
  sorted order. Different arguments — another page, another search text — are different
  entries; the same arguments in another order are the same entry.
- **The raw JSON is stored**, not the model, together with the time it was written. Every
  cache hit is validated into models anew, so you get equal, not identical, objects.
- **Only successful responses** are cached. Errors (`NotFoundError`, ...) are raised as usual
  and the next call asks the API again.
- **A broken cache never breaks a call**: an unreadable or corrupted file is a miss, and a
  failed write (a full disk, a read-only directory) is logged as a warning on the
  `aniliberty` logger while the call returns the data it got.

There is no size limit and no automatic cleanup: stale entries stay on disk until they are
fetched again. To clear the cache, delete the directory (or the files in it) — it is
recreated on the next write.

## Seeing it work

Hits are logged at `DEBUG` level on the `aniliberty` logger, next to the network requests:

```python
import logging

logging.basicConfig()
logging.getLogger("aniliberty").setLevel(logging.DEBUG)
# DEBUG:aniliberty:GET https://aniliberty.top/api/v1/anime/genres -> 200
# DEBUG:aniliberty:GET https://aniliberty.top/api/v1/anime/genres: from cache
```
