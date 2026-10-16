# Pagination

Some endpoints return results page by page. In the SDK each of them comes as a pair:

| One page → [`Page`][aniliberty.Page] | All pages → async iterator |
|---|---|
| [`client.catalog.releases()`][aniliberty.resources.CatalogResource.releases] | [`client.catalog.iter_releases()`][aniliberty.resources.CatalogResource.iter_releases] |
| [`client.releases.list()`][aniliberty.resources.ReleasesResource.list] | [`client.releases.iter_list()`][aniliberty.resources.ReleasesResource.iter_list] |

Both take the same filters; the `iter_*` twin just doesn't take `page`. Endpoints that return a
short list without pages (`releases.latest()`, `random()`, `recommended()`,
`app.search_releases()`) return a plain `list`.

The numbers in the examples below come from a real run on 2026-10-16; the catalog changes, so
yours will differ.

## `Page`

```python
page = await client.catalog.releases(types=["MOVIE"], limit=20)
print(page.page, page.limit, page.total, page.total_pages, page.has_next_page)
# 1 20 148 8 True
for release in page.items:
    ...
```

| Field | Meaning |
|---|---|
| `items` | the releases on this page |
| `page` | number of this page, starting at 1 |
| `limit` | page size |
| `total` | number of results on all pages |
| `total_pages` | number of pages |
| `has_next_page` | `page < total_pages` |

`limit` is 1 to 50 — anything else is rejected by the API with a
[`ValidationError`][aniliberty.ValidationError]; so is `page` below 1. A `page` past the last
one is not an error, just an empty page.

### Counting without fetching

`total` comes with every page, so to know *how many* releases match, ask for the smallest
page possible:

```python
page = await client.catalog.releases(types=["MOVIE"], limit=1)
print(page.total)  # 148 — one request, one release transferred
```

## `iter_*`: all pages for you

```python
async for release in client.catalog.iter_releases(publish_statuses=["IS_ONGOING"], limit=50):
    print(release.name.main)
```

The iterator requests page 1, yields its items, requests page 2 only when you've consumed
page 1, and so on. It stops after the last page — or at the first empty page, so a total that
changes while you iterate can't make it loop forever.

**It's lazy, so breaking out stops the requests.** Taking the first 10 releases of the whole
catalog this way makes exactly one request:

```python
first_ten = []
async for release in client.catalog.iter_releases(limit=50):
    first_ten.append(release)
    if len(first_ten) == 10:
        break
```

**`limit` only changes the number of requests, not the result.** Iterating the 33 ongoing
releases took 4 requests with `limit=10` and 1 with `limit=50`. Use `limit=50` with `iter_*`
unless you have a reason not to.

To collect everything into a list, use a comprehension:

```python
ongoing = [r async for r in client.catalog.iter_releases(publish_statuses=["IS_ONGOING"], limit=50)]
```

## Walking pages yourself

When you need the page boundaries — for your own UI, progress reporting, or to resume later
— loop over `releases()` with `has_next_page`:

```python
page_number = 1
while True:
    page = await client.catalog.releases(
        publish_statuses=["IS_ONGOING"], page=page_number, limit=20
    )
    handle(page.items)
    if not page.has_next_page:
        break
    page_number += 1
```

## Fetching pages concurrently

`iter_*` is sequential: page 2 is requested after page 1 is consumed. If you need all pages
fast, fetch the first one to learn `total_pages`, then the rest at once:

```python
first = await client.catalog.releases(types=["MOVIE"], limit=50)
rest = await asyncio.gather(
    *(
        client.catalog.releases(types=["MOVIE"], page=n, limit=50)
        for n in range(2, first.total_pages + 1)
    )
)
movies = first.items + [release for page in rest for release in page.items]
# 148 movies, 3 requests
```

The client still keeps at most `max_concurrency` requests in flight and spaces them out, so
this is safe to do with many pages.

!!! warning "Pages are separate snapshots"
    Each page is a separate request. If the data changes between them — a release gets a new
    episode and moves to the top of the default `FRESH_AT_DESC` order — an item can shift from
    one page to the next, showing up twice or not at all. This is how offset pagination works
    in general, sequential or concurrent. When it matters, sort by something stable
    (`sorting="YEAR_ASC"`) and deduplicate by `release.id`.

## Several releases by ID

[`client.releases.list()`][aniliberty.resources.ReleasesResource.list] pages through the
releases you ask for by `ids`/`aliases` — useful for a long list of IDs, e.g. a user's
favorites stored elsewhere:

```python
async for release in client.releases.iter_list(ids=[9542, 10172, 10297], limit=50):
    print(release.id, release.name.main)
```

The result doesn't follow the order of `ids`, and an ID given twice (or both as an ID and as
an alias) is returned once.
