# Catalog filters

[`client.catalog.releases()`][aniliberty.resources.CatalogResource.releases] browses the whole
release catalog with filters, sorting and pagination — the "Catalog" page of the site.
For finding one title by name, [`client.app.search_releases()`][aniliberty.resources.AppResource.search_releases]
is simpler.

## A first query

```python
page = await client.catalog.releases(types=["TV"], year_from=2020, sorting="RATING_DESC", limit=10)
print(f"{page.total} releases, page {page.page} of {page.total_pages}")
for release in page.items:
    print(release.year, release.name.main)
```

Every filter is optional and keyword-only; without any, you get the whole catalog (about two
thousand releases), most recently updated first.

| Parameter | Type | Example |
|---|---|---|
| `genres` | genre IDs or `Genre` objects | `[14, 29]` |
| `types` | release types | `["TV", "MOVIE"]` |
| `seasons` | seasons | `["winter", "spring"]` |
| `year_from`, `year_to` | `int` | `2018`, `2020` |
| `search` | `str` | `"frieren"` |
| `sorting` | one sort order | `"RATING_DESC"` |
| `age_ratings` | age ratings | `["R16_PLUS"]` |
| `publish_statuses` | `"IS_ONGOING"` / `"IS_NOT_ONGOING"` | `["IS_ONGOING"]` |
| `production_statuses` | `"IS_IN_PRODUCTION"` / `"IS_NOT_IN_PRODUCTION"` | `["IS_IN_PRODUCTION"]` |
| `page`, `limit` | `int`; `limit` is 1 to 50 | `1`, `50` |

## Where the values come from

[`client.catalog.references`][aniliberty.resources.CatalogReferencesResource] returns the lists
the site's own filters show. Their items can be passed to the filters directly — no need to
copy IDs or strings by hand:

```python
refs = client.catalog.references
genres = {genre.name: genre for genre in await refs.genres()}
page = await client.catalog.releases(genres=[genres["Экшен"], genres["Фэнтези"]], limit=5)
```

`refs.types()`, `refs.seasons()`, `refs.age_ratings()`, `refs.publish_statuses()`,
`refs.production_statuses()` and `refs.sorting()` work the same way: pass the items, or their
`.value`. `refs.years()` lists only the years that have releases.

```python
for option in await refs.sorting():
    print(option.value, "—", option.label)
```

```text
FRESH_AT_DESC — Обновлены недавно
FRESH_AT_ASC — Обновлены давно
RATING_DESC — Самый высокий рейтинг
RATING_ASC — Самый низкий рейтинг
YEAR_DESC — Самые новые
YEAR_ASC — Самые старые
```

## How filters combine

Checked against the live API (see [API notes](../api-notes.md#catalog-filters-checked-2026-10-16)):

- **`genres` — all of them.** `genres=[14, 29]` returns releases that have *both* genres.
- **Every other list — any of them.** `types=["TV", "ONA"]` returns TV *or* ONA releases;
  the same for `seasons`, `age_ratings`, `publish_statuses`, `production_statuses`.
- **Different filters — all of them.** `genres=[14], types=["TV"]` means genre 14 *and* TV.
- **Years are inclusive.** `year_from=2018, year_to=2020` includes 2018 and 2020; either bound
  can be used alone.

```python
# Action AND fantasy, TV or ONA, released 2018–2020
page = await client.catalog.releases(
    genres=[14, 29], types=["TV", "ONA"], year_from=2018, year_to=2020
)
```

## Sorting

`sorting` takes one value; the default is `"FRESH_AT_DESC"` (recently updated first).

- `FRESH_AT_*` — by when a release was last updated (usually a new episode).
- `YEAR_*` — by release year.
- `RATING_*` — by **popularity**: in every live check, the order followed
  `added_in_users_favorites` (how many users added the release to favorites), not the
  average score in `release.rating`.

## Search

`search` uses the same matching as the quick search: Russian and English names and aliases,
sensitive to punctuation. It also shares its cap — **at most about 20 matches in total**,
whatever the other filters and the page size. Use it to narrow down a title, not to list
"everything with the word *magic*".

```python
page = await client.catalog.releases(search="frieren", types=["TV"])
```

An empty `search=""` is the same as no search.

## All pages

`releases()` returns one [`Page`][aniliberty.Page]; `iter_releases()` takes the same filters
(minus `page`) and walks all pages, requesting the next one only when you reach it:

```python
async for release in client.catalog.iter_releases(
    publish_statuses=["IS_ONGOING"], sorting="FRESH_AT_DESC", limit=50
):
    print(release.name.main)
```

Use `limit=50` with `iter_releases()` — it only changes how many requests are made. Breaking
out of the loop stops the requests. A page number past the last page returns an empty page.

## Invalid values

The API doesn't report wrong filter values: an unknown type silently returns no releases, an
unknown sort order or a non-numeric year is silently ignored. So the SDK checks them before
sending and raises right away:

```python
await client.catalog.releases(types=["tv"])
# ValueError: Unknown types value 'tv'; expected one of: TV, ONA, WEB, OVA, OAD, MOVIE, DORAMA, SPECIAL
```

- An unknown value of a list filter or of `sorting` → `ValueError`.
- `year_from` after `year_to` → `ValueError` (the API would return nothing).
- A single string instead of a list, e.g. `types="TV"` → `TypeError`.
- `page` below 1 or `limit` outside 1–50 → the API's own
  [`ValidationError`][aniliberty.ValidationError].

The allowed values are the `enum`s of the API's OpenAPI spec; with a type checker, the
parameters' `Literal` types catch typos before the code even runs.
