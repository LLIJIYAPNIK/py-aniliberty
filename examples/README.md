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

See the [API reference](https://llijiyapnik.github.io/py-aniliberty/reference/) for every
public class and method.
