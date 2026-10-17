# Examples

The [`examples/`](https://github.com/LLIJIYAPNIK/py-aniliberty/tree/main/examples) directory
of the repository has a runnable script for every feature of the SDK. Each is a complete
program — `python examples/<file>.py` — heavily commented so that it reads as a short
tutorial, and ends with the output of a real run against the live API.

Examples 18–23 need an account: they read its credentials from the `ANILIBERTY_LOGIN` and
`ANILIBERTY_PASSWORD` environment variables and leave the account as they found it — see
[Authentication](guides/authentication.md).

| File | Feature |
|---|---|
| [`01_quickstart.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/01_quickstart.py) | `AniLiberty` client, `app.status()`, a first look at releases |
| [`02_latest_and_random_releases.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/02_latest_and_random_releases.py) | `releases.latest()` / `random()` / `recommended()`, `limit` and `ValidationError` |
| [`03_release_details.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/03_release_details.py) | `releases.get()` — names, value + description fields, ratings, images, team; `members()`; `list()` / `iter_list()` |
| [`04_episodes_and_hls_links.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/04_episodes_and_hls_links.py) | `episodes.get()` — HLS playlists, opening/ending timings, previews, `NotFoundError` |
| [`05_quick_search.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/05_quick_search.py) | `app.search_releases()` — what it matches and what it doesn't |
| [`06_catalog_filters.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/06_catalog_filters.py) | `catalog.releases()` — how filters combine (AND/OR), years, sorting, search, invalid values |
| [`07_catalog_pagination.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/07_catalog_pagination.py) | `Page` vs `iter_releases()` — request counts, early break, fetching pages concurrently |
| [`08_catalog_references.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/08_catalog_references.py) | `catalog.references.*()` — every reference list, and their items as filter values |
| [`09_schedule.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/09_schedule.py) | `schedule.now()` / `week()` — today's releases and episode status, the week grouped by weekday |
| [`10_genres.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/10_genres.py) | `genres.list()` / `get()` / `random()` / `releases()` / `iter_releases()` |
| [`11_franchises.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/11_franchises.py) | `franchises.list()` / `get()` / `for_release()` / `random()` — a franchise's releases in watch order |
| [`12_torrents_and_download.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/12_torrents_and_download.py) | `torrents.for_release()` / `file()` / `download()` / `get()` / `list()` / `iter_list()` / `rss()` / `rss_for_release()` |
| [`13_concurrency_gather.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/13_concurrency_gather.py) | `asyncio.gather` / `TaskGroup` / `asyncio.timeout` — how `max_concurrency` and pacing bound the request rate |
| [`14_error_handling.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/14_error_handling.py) | the exception hierarchy on real errors (404, 422, 405, timeout), automatic retries and their logging |
| [`15_custom_http_client_and_mirrors.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/15_custom_http_client_and_mirrors.py) | the mirror via `base_url`, failing over between hosts, your own `httpx.AsyncClient` (hooks, timeouts, sharing), `headers=` |
| [`16_teams.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/16_teams.py) | `teams.list()` / `roles()` / `users()` — members per team, roles, joining with release credits |
| [`17_media.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/17_media.py) | `media.promotions()` / `videos()` — kinds of promo banners, latest YouTube videos and `limit` |
| [`18_authentication.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/18_authentication.py) | `auth.login()` / `logout()`, `client.token` and `AniLiberty(token=...)`, `me.profile()`, 401 vs 403 |
| [`19_otp_device_login.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/19_otp_device_login.py) | `auth.otp.issue()` / `accept()` / `login()` — logging a device in with a one-time code |
| [`20_favorites.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/20_favorites.py) | `me.favorites.add()` / `remove()` / `ids()` / `releases()` / `iter_releases()` / `references` |
| [`21_collections.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/21_collections.py) | `me.collections.add(..., to=...)` / `remove()` / `ids()` / `releases(collection)` / `iter_releases()` / `references` — moving between collections |
| [`22_watch_progress.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/22_watch_progress.py) | `me.views.save_timecodes()` / `timecodes()` / `history()` / `iter_history()`, `episodes.timecode()`, `releases.timecodes()` — and the API's delay |
| [`23_release_ratings.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/23_release_ratings.py) | `releases.ratings.get()` / `set()` / `remove()` vs the overall `Release.rating` |
| [`24_response_cache.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/24_response_cache.py) | `AniLiberty(cache_dir=..., cache_ttl=...)` — answering repeated calls from disk, `refresh=True`, what is never cached |
