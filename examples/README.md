# Examples

Every script in this directory is a complete, self-contained program — copy it as is and run
`python examples/<file>.py` (or `uv run python examples/<file>.py` inside this repository).
Each one was actually executed against the live API to produce the "Expected output" comment
at the bottom of the file, verbatim.

The API's data changes all the time — new episodes, random picks, vote counts — so a re-run
won't print exactly the same thing. That's the data changing, not a bug in the SDK. The
scripts stick to one long-finished release (`sousou-no-frieren`) where they can, to keep the
output as stable as possible.

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

See the [API reference](https://llijiyapnik.github.io/py-aniliberty/reference/) for every
public class and method.
