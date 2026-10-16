# Examples

Every script in this directory is a complete, self-contained program — copy it as is and run
`python examples/<file>.py` (or `uv run python examples/<file>.py` inside this repository).
Each one was actually executed against the live API to produce the "Expected output" comment
at the bottom of the file, verbatim.

The API's data changes all the time — new episodes, random picks, vote counts — so a re-run
won't print exactly the same thing. That's the data changing, not a bug in the SDK. The
scripts stick to one long-finished release (`sousou-no-frieren`) where they can, to keep the
output as stable as possible.

Examples 18–23 use an account: they read its credentials from the `ANILIBERTY_LOGIN` and
`ANILIBERTY_PASSWORD` environment variables, never print secrets, and leave the account as
they found it (they only remove what they added themselves). See the
[authentication guide](https://llijiyapnik.github.io/py-aniliberty/guides/authentication/).

Scripts are heavily commented on purpose: each one is meant to be read top to bottom as a
mini-tutorial for its feature, not just copy-pasted.

| File | Feature |
|---|---|
| [`01_quickstart.py`](01_quickstart.py) | `AniLiberty` client, `app.status()`, a first look at releases |
| [`02_latest_and_random_releases.py`](02_latest_and_random_releases.py) | `releases.latest()` / `random()` / `recommended()`, `limit` and `ValidationError` |
| [`03_release_details.py`](03_release_details.py) | `releases.get()` — names, value + description fields, ratings, images, team; `members()`; `list()` / `iter_list()` |
| [`04_episodes_and_hls_links.py`](04_episodes_and_hls_links.py) | `episodes.get()` — HLS playlists, opening/ending timings, previews, `NotFoundError` |
| [`05_quick_search.py`](05_quick_search.py) | `app.search_releases()` — what it matches and what it doesn't |
| [`06_catalog_filters.py`](06_catalog_filters.py) | `catalog.releases()` — how filters combine (AND/OR), years, sorting, search, invalid values |
| [`07_catalog_pagination.py`](07_catalog_pagination.py) | `Page` vs `iter_releases()` — request counts, early break, fetching pages concurrently |
| [`08_catalog_references.py`](08_catalog_references.py) | `catalog.references.*()` — every reference list, and their items as filter values |
| [`09_schedule.py`](09_schedule.py) | `schedule.now()` / `week()` — today's releases and episode status, the week grouped by weekday |
| [`10_genres.py`](10_genres.py) | `genres.list()` / `get()` / `random()` / `releases()` / `iter_releases()` |
| [`11_franchises.py`](11_franchises.py) | `franchises.list()` / `get()` / `for_release()` / `random()` — a franchise's releases in watch order |
| [`12_torrents_and_download.py`](12_torrents_and_download.py) | `torrents.for_release()` / `file()` / `download()` / `get()` / `rss_for_release()` |
| [`13_concurrency_gather.py`](13_concurrency_gather.py) | `asyncio.gather` / `TaskGroup` / `asyncio.timeout` — how `max_concurrency` and pacing bound the request rate |
| [`14_error_handling.py`](14_error_handling.py) | the exception hierarchy on real errors (404, 422, 405, timeout), automatic retries and their logging |
| [`15_custom_http_client_and_mirrors.py`](15_custom_http_client_and_mirrors.py) | the mirror via `base_url`, failing over between hosts, your own `httpx.AsyncClient` (hooks, timeouts, sharing), `headers=` |
| [`16_teams.py`](16_teams.py) | `teams.list()` / `roles()` / `users()` — members per team, roles, joining with release credits |
| [`17_media.py`](17_media.py) | `media.promotions()` / `videos()` — kinds of promo banners, latest YouTube videos and `limit` |
| [`18_authentication.py`](18_authentication.py) | `auth.login()` / `logout()`, `client.token` and `AniLiberty(token=...)`, `me.profile()`, 401 vs 403 |
| [`19_otp_device_login.py`](19_otp_device_login.py) | `auth.otp.issue()` / `accept()` / `login()` — logging a device in with a one-time code |
| [`20_favorites.py`](20_favorites.py) | `me.favorites.add()` / `remove()` / `ids()` / `releases()` / `iter_releases()` / `references` |
| [`21_collections.py`](21_collections.py) | `me.collections.add(..., to=...)` / `remove()` / `ids()` / `releases(collection)` — moving between collections |
| [`22_watch_progress.py`](22_watch_progress.py) | `me.views.save_timecodes()` / `timecodes()` / `history()`, `episodes.timecode()`, `releases.timecodes()` — and the API's delay |
| [`23_release_ratings.py`](23_release_ratings.py) | `releases.ratings.get()` / `set()` / `remove()` vs the overall `Release.rating` |

See the [API reference](https://llijiyapnik.github.io/py-aniliberty/reference/) for every
public class and method.
