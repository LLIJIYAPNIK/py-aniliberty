# API notes

Living document of findings about the AniLibria API v1, gathered from the OpenAPI spec
([`spec/openapi.json`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/spec/openapi.json))
and live requests, before implementing the corresponding SDK feature. Each finding says what was
requested, what came back, and what the SDK does about it. Open questions are listed at the end.

All live requests below were made on **2026-10-16** from the maintainer's machine (the API
geolocated the client to the Netherlands), without authentication, with `httpx`'s default
`User-Agent` (`python-httpx/0.28.1`) unless stated otherwise.

## Spec location

The Swagger UI at <https://anilibria.top/api/docs/v1> is a static page whose
`SwaggerUIBundle({ url: ... })` option points to:

```
https://anilibria.top/storage/api/docs/v1?aniliberty-api-v1-docs.json
```

That URL returns the spec as `application/json` (OpenAPI `3.0.0`, `info.title` `AniLiberty`,
`info.version` `1.0.0`, 71 paths / 80 operations / 25 tags / 132 schemas). The query string is
part of the URL as-is — `/storage/api/docs/v1/aniliberty-api-v1-docs.json` is a 404.
`scripts/update_spec.py` downloads it.

## Base URL and mirrors

- The spec's `servers` are `/api/v1` (relative, "this server") and
  `https://aniliberty.top/api/v1` ("Main server #1").
- `GET /app/status` on `anilibria.top` returned:

  ```json
  {
    "request": {"ip": "...", "country": "The Netherlands", "iso_code": "NL", "timezone": "Europe/Amsterdam"},
    "is_alive": true,
    "available_api_endpoints": ["https://aniliberty.top"]
  }
  ```

The same requests against `https://aniliberty.top/api/v1` (`/app/status`, a missing release,
`/anime/releases/latest`) returned identical responses, `aniliberty.top/storage/...` serves the
same images, and the spec at `aniliberty.top/storage/api/docs/v1?aniliberty-api-v1-docs.json`
is byte-for-byte the same after normalization.

**Conclusion:** both hosts serve the same API. The SDK's default `base_url` is
`https://aniliberty.top/api/v1` — the host both the spec and `/app/status` call the main one;
`https://anilibria.top/api/v1` works as a mirror.

## No special User-Agent or anti-bot challenge (so far)

The Swagger page, the spec, and every API request in this document succeeded with plain
`curl/*` and `python-httpx/*` user agents — no browser `User-Agent`, `Referer`, or cookies. All
responses carry `server: cloudflare` and `cf-cache-status: DYNAMIC`, i.e. the API sits behind
Cloudflare, so a challenge page is still possible from other networks or under load.

**Conclusion:** the SDK sends its own `User-Agent` (`py-aniliberty/<version>`), nothing
browser-like. An HTML response is not by itself proof of a WAF block — see the next section.

## `Accept: application/json` is required for JSON error bodies

`GET /anime/releases/this-alias-does-not-exist-xyz`:

| `Accept` header | Status | `Content-Type` | Body |
|---|---|---|---|
| not sent (httpx default `*/*`) | 404 | `text/html; charset=UTF-8` | Laravel's generic "Not Found" HTML page (6.6 KB) |
| `application/json` | 404 | `application/json` | `{"message": "No query results for model [App\\Modules\\Anime\\Releases\\Models\\Release\\Release]."}` |

The backend is Laravel: without `Accept: application/json` its exception handler renders HTML.
The spec declares the 404 of this operation with a description only ("Релиз не найден"), no
body schema.

**Conclusion:** the SDK sends `Accept: application/json` on every JSON request. With it, an HTML
body really does mean something outside the API answered (WAF/CDN), which is what
`AccessBlockedError` is for. A 404 body is `{"message": str}` — the message is a Laravel model
lookup string, not user-facing text, so `NotFoundError` should carry it in `message`/`payload`
but build its own human-readable `str()`.

## Validation errors (422)

`GET /anime/releases/latest?limit=abc` → `422 application/json` (JSON even without the `Accept`
header):

```json
{"errors": {"limit": ["Поле limit должно быть числом."]}}
```

This matches the spec's shared `commons.v1.http.responses.422` response:
`{"errors": {<parameter>: [<message>, ...]}}`. Messages are in Russian.

**Conclusion:** `ValidationError` exposes `errors: dict[str, list[str]]` from the body.

## Pagination

Spec: shared query parameters `page` and `limit` (integers, no `minimum`/`maximum` declared) and
a shared response schema `commons.v1.utils.pagination.schemes.meta`. Paginated responses are
`{"data": [...], "meta": {"pagination": {...}}}`. Operations using it (per spec):
`GET`/`POST /anime/catalog/releases`, `GET /anime/releases/list`,
`GET /anime/genres/{genreId}/releases`, `GET /anime/torrents`, and the account
favorites/collections/history listings.

`GET /anime/catalog/releases?page=2&limit=3&f[types]=TV,WEB&f[years][from_year]=2020&include=id,type.value,year`:

```json
{
  "data": [{"id": 10335, "type": {"value": "TV"}, "year": 2026}, "..."],
  "meta": {
    "pagination": {
      "total": 834,
      "count": 3,
      "per_page": 3,
      "current_page": 2,
      "total_pages": 278,
      "links": {
        "previous": "https://anilibria.top/api/v1/anime/catalog/releases?limit=3&f%5Btypes%5D=TV%2CWEB&...&page=1",
        "next": "https://anilibria.top/api/v1/anime/catalog/releases?limit=3&f%5Btypes%5D=TV%2CWEB&...&page=3"
      }
    }
  }
}
```

`GET /anime/catalog/releases?limit=1000&include=id` → `422`:
`{"errors": {"limit": ["Поле limit не может быть больше 50."]}}`.

**Conclusion:**

- Pages are 1-based; `meta.pagination` has `total`, `count`, `per_page`, `current_page`,
  `total_pages`, `links.previous`/`links.next` (absolute URLs, keeping the original query).
  `Page[T]` maps these; "has next page" is `current_page < total_pages`.
- The catalog's maximum `limit` is **50** (exceeding it is a 422, not a silent clamp). Other
  endpoints' maximums are not checked yet.
- Non-paginated lists (`/anime/releases/latest`, `/random`, `/recommended`, ...) return a bare
  JSON array, not `{"data": ...}`.

## Array parameters in query filters

Spec: catalog filters are named `f[types]`, `f[seasons]`, `f[age_ratings]`,
`f[publish_statuses]`, `f[production_statuses]` with `style: form, explode: false` (i.e.
comma-separated values in one parameter); `f[genres]` has no schema, only the example `"15,20"`;
year range is `f[years][from_year]` / `f[years][to_year]`; free text is `f[search]`; sorting is
`f[sorting]`. `GET /anime/releases/list` takes `ids` and `aliases` the same way
(`form`, `explode: false`). `include`/`exclude` accept "comma-separated or repeated parameters".

`GET /anime/catalog/releases?limit=50&f[types]=WEB,MOVIE&include=id,type.value` → 200,
`total: 160`; the first page contained only `WEB` (7) and `MOVIE` (43) releases.

**Conclusion:** arrays are serialized as one comma-separated value: `f[types]=WEB,MOVIE`,
`f[genres]=1,5`, `ids=1,2,3`. Several values of one filter are OR-ed. The bracketed
`f[types][]=...` form was not tested and is not used by the SDK. `include=id,type.value` works
and nests with dots, as documented.

`POST /anime/catalog/releases` takes the same filters as a JSON body
(`{"page", "limit", "f": {"genres": [int], "types": [...], "years": {"from_year", "to_year"},
...}, "include", "exclude"}`) and returns the same response schema as `GET`. The `POST` variant
was not called live; the SDK plans to use `GET`.

## Enums declared in the spec

These are `enum:` schemas in the spec, so they can be `Literal`s in the SDK (with a pointer to
the schema name):

| Schema | Values |
|---|---|
| `enums.anime.releases.release.type` | `TV`, `ONA`, `WEB`, `OVA`, `OAD`, `MOVIE`, `DORAMA`, `SPECIAL` |
| `enums.anime.releases.release.season` | `winter`, `spring`, `summer`, `autumn` |
| `enums.anime.releases.release.ageRating` | `R0_PLUS`, `R6_PLUS`, `R12_PLUS`, `R16_PLUS`, `R18_PLUS` |
| `enums.anime.catalog.filter.sorting` | `FRESH_AT_DESC`, `FRESH_AT_ASC`, `RATING_DESC`, `RATING_ASC`, `YEAR_DESC`, `YEAR_ASC` |

The catalog references endpoints (`/anime/catalog/references/*`) return these lists at runtime
too; the publish/production status enums and the rest are left for step 2.1.

## Value + description fields

Spec: `type`, `season`, `age_rating`, `publish_day` of a release are objects
`{"value": <enum>, "description": <str>}`. Live (`GET /anime/releases/latest?limit=1`):

```json
"type":        {"value": "TV", "description": "ТВ"},
"season":      {"value": "autumn", "description": "Осень"},
"publish_day": {"value": 5, "description": "Пятница"},
"age_rating":  {"value": "R16_PLUS", "label": "16+", "is_adult": false,
                "description": "Для людей, достигших возраста шестнадцати лет (16+)"}
```

**Conclusion:** a generic `ValueDescription[T]` fits (`value` is a string *or* an integer —
`publish_day.value` is a weekday number). `age_rating` has two extra fields, `label` and
`is_adult`, that the spec does not mention — it needs its own subclass.

### Empty value + description objects (checked 2026-10-16)

`GET /anime/schedule/week` returned, for one release, `"season": {"value": null,
"description": null}` — the object is present with both keys `null` instead of being omitted
or `null` itself. Across `/anime/releases/random`, `/anime/schedule/week`, `/anime/torrents`,
`/media/promotions` and `/media/videos`, every other value + description object had a non-null
`value`: strings everywhere except `publish_day` (integer weekday).

**Conclusion:** optional value + description fields are annotated with `EMPTY_VALUE_AS_NONE`,
which turns such an object into `None`.

## Image and video URLs

- **Images are relative paths** on the site's domain, e.g. poster
  `"/storage/releases/posters/10297/Bcvffb9gHRoFRFhSD5SxAW7Ls3Ru5GjI.jpg"`. They resolve against
  the site root, not the API base: `HEAD https://anilibria.top/storage/releases/posters/10297/Bcvffb9gHRoFRFhSD5SxAW7Ls3Ru5GjI.jpg`
  → `200 image/jpeg`. Same for episode previews and genre images.
- The image object is `{"src", "preview", "thumbnail", "optimized": {"src", "preview",
  "thumbnail"}}` — `optimized` holds `.webp` variants. The spec
  (`commons.v1.models.components.image`) documents `preview`/`thumbnail`/`optimized` only;
  `src` is undocumented. Genre images have no `src`.
- **HLS links are absolute** on a separate CDN host, with query parameters that depend on the
  requester:
  `"https://cache.libria.fun/videos/media/ts/10297/3/1080/934fbfebe8559bc9866ea02c737bd235.m3u8?countryIso=NL&isAuthorized=0&isWithVideoAds=1&isWithVideoAdsAlways=1"`.
- `external_player` is protocol-relative in the spec example (`"//kodik.info/serial/..."`); it
  was `null` in the live sample.

A wider sample on 2026-10-16 (random releases, genres, franchises, torrents, team users,
promotions, videos, the week schedule — 574 image objects) found **only relative**
image paths. A missing image is not `null` but an object whose paths are all `null`
(12 of 271 franchises, team users and torrent members without an avatar).

**Conclusion:** URL fields stay `str` holding the raw value; `Image`/`ImageSet` get `*_url`
properties that join the path with the origin of the client's `base_url` (passed to
validation as context, so a mirror's images point to the mirror). Absolute and
protocol-relative paths are passed through. HLS URLs are returned untouched — the query
string is part of the link.

## Optional and nullable fields

The spec declares **no `required` lists in any schema** and `nullable: true` on only 13
properties (Shikimori/MAL ids and ratings, average rating, own score, member `user`, franchise
`total_duration`, schedule `next_release_episode_number`). Live data has `null` in fields the
spec does not mark nullable: `notification`, `external_player` (release), `rutube_id`,
`youtube_id` (episode).

**Conclusion:** the spec's `nullable` flags cannot be trusted. Models will treat fields as
optional unless they are identifiers or are observed non-null in every recorded cassette; each
such decision goes into these notes per model.

## Authentication (spec only)

The spec defines one security scheme, `sessionToken` (`type: http`, `scheme: bearer`,
"Bearer auth session token"), and sets it as the **global** `security` requirement. 31
operations repeat it explicitly; the other 49 (all public `anime/*`, `app/*`, `media/*`,
`teams/*` operations plus the login/OTP/password endpoints) do not override it. Strictly read,
that would make every operation require a token, but none of the unauthenticated requests in
this document got a 401/403 — the public endpoints answered normally.

**Conclusion:** the global requirement is a spec artefact. "Requires auth" in
`docs/endpoints.md` means the operation declares `security` itself. Token lifetime, refresh,
and the 401/403 bodies are left for step 4.1.

## Torrent and RSS endpoints (spec only)

`GET /anime/torrents/{hashOrId}/file` returns `application/x-bittorrent`; `GET
/anime/torrents/rss` and `/rss/release/{releaseId}` return `application/xml`. All three take an
optional `pk` (user passkey) query parameter. Not called live yet (step 3.4).

## Releases (checked 2026-10-16)

Requests: `GET /anime/releases/latest?limit=20`, `/random?limit=20`,
`/recommended?limit=5&release_id=10297` and without `release_id`,
`/anime/releases/tensei-shitara-ken-deshita-2nd-season` and `/anime/releases/10297`,
`/anime/releases/10297/members`, `/anime/releases/list` with several `ids`/`aliases`, plus
`limit=0`, `limit=51` and missing parameters.

- **`limit` is 1 to 50** on `latest`, `random`, `recommended` and `list` — `limit=51` gives
  `422 {"errors": {"limit": ["Поле limit не может быть больше 50."]}}`, `limit=0` gives
  `"Поле limit должно быть не меньше 1."`.
- **`list` needs `ids` or `aliases`**: without both, 422 (`"Поле ids обязательно для
  заполнения, когда aliases не указано."`). A release requested both by ID and by alias is
  returned once (`ids=10297&aliases=<its alias>` → `total: 1`). The result is **not** in the
  requested order (`ids=10297,3990` + an alias → `[3990, 9955]` on page 1).
- **`recommended` works without `release_id`** (general recommendations).
- `get()` by ID and by alias return the same body. A missing ID or alias → the JSON 404 from
  "`Accept: application/json` is required…", also on `/members`.
- **Extras per endpoint:** `genres` everywhere; `background_covers` on `random` and the release
  page; `latest_episode` on `latest`; `episodes`, `members`, `sponsors`, `torrents` on the
  release page and `list`.
- **Nulls the spec doesn't declare:** `name.alternative`, `description` (1 of 40), `notification`
  (40 of 40), `external_player` (29 of 40), `episodes_total` (14 of 40),
  `average_duration_of_episode` (11 of 40). `rating.average` was an integer (`1`) once — models
  accept it as a float.
- **Members:** `user` was `null` for all 8 members of release 10297; `id` is a UUID string;
  `role.value` values seen: `decorating`, `hevc`, `timing`, `translating`, `voicing`.
- `rating.distribution` has string keys `"1"`…`"10"`; the SDK turns them into ints.

**Conclusion:** `client.releases` validates only what the API can't (`list()` without
`ids`/`aliases` raises `ValueError` before sending). Range checks for `limit` are left to the
API's 422. Fields observed non-null in every response (counters, `is_*` flags, `id`, `alias`,
`name.main`) are required; everything else is optional.

## Episodes (checked 2026-10-16)

Requests: the episodes of 40 releases (20 from `latest`, 20 from `random`, fetched through
`/anime/releases/list` — 328 episodes, plus 20 `latest_episode` objects),
`GET /anime/releases/episodes/a159552a-9fa7-4737-867b-d22cf7115602`, and the same endpoint with
an all-zero UUID and with `not-a-uuid`.

- **HLS:** `hls_480` and `hls_720` were present on all 348 episodes, `hls_1080` was `null` on
  76. All links are absolute `.m3u8` URLs on `cache.libria.fun`.
- **`ordinal`** was an integer on all 348 (the spec allows fractions like `12.5`); it was equal
  to `sort_order` on every episode.
- **`opening`/`ending`** are always objects, but `{"start": null, "stop": null}` when not
  marked (84 of 328 openings). Never only one of the two was `null`. In all 38 episodes with
  timings, `stop` stayed within `duration` and endings started near the end (e.g. `1326`–`1502`
  of a 1502-second episode): the spec's "seconds from the start or the end" is, in practice,
  seconds **from the start**.
- **`preview`:** present on every episode, but with all paths `null` on 177 of 328.
- **`name`** was `null` on 273 of 348, **`name_english`, `rutube_id`, `youtube_id`** on all.
- **The episode endpoint** returns the episode plus `release` — the release with `episodes`
  but **without** `genres`.
- **Missing or malformed ID:** both an unknown UUID and `not-a-uuid` give the JSON 404
  (`"No query results for model [...ReleaseEpisode] <id>"`), so the SDK doesn't validate the
  UUID format itself.

**Conclusion:** `Episode` requires `id`, `release_id`, `ordinal` (`int | float`), `sort_order`
and `duration`; HLS links and everything else are optional. An all-`null` skip range becomes
`None`. `Release` gets `episodes` and `latest_episode`.

## Quick search (checked 2026-10-16)

Requests: `GET /app/search/releases?query=...` with about 25 queries — Russian, English and
romanized names, an alias, single letters, a number, punctuation variants, nonsense, an
empty `query` and none at all.

- **Matches every kind of name:** `frieren`, `Фрирен`, `провожающая` and the alias
  `sousou-no-frieren` all return the same 2 releases.
- **Fuzzy, punctuation-sensitive:** `Re Zero`, `Re: Zero` and `ReZero` find "Re: Перерыв с нуля",
  `Re:Zero` and `re:zero` find nothing.
- **Size:** 0 to 20 results; 20 was the maximum seen (`магия`), common one-letter queries
  gave 13–18. No paging, and an extra `limit=3` is ignored (`магия` still returned 20).
- **No matches:** `200 []`.
- **Empty or missing `query`:** `422 {"errors": {"query": ["Поле query обязательно для
  заполнения."]}}`.
- Results are bare releases (spec: `models.anime.releases.v1.release`) — no `genres`,
  `episodes` or other extras.

**Conclusion:** `client.app.search_releases(query)` returns `list[Release]`; the empty-query
check is left to the API (`ValidationError`), like `limit` on the release endpoints.

## Catalog references (checked 2026-10-16)

Requests: `GET /anime/catalog/references/{age-ratings,genres,production-statuses,publish-statuses,seasons,sorting,types,years}`.

All eight match the spec exactly, with no `null`s:

- `types`, `seasons`, `publish-statuses`, `production-statuses`: `[{"value", "description"}]`,
  values identical to the spec enums (8 types, 4 seasons, 2 + 2 statuses).
- `age-ratings`: `[{"value", "label", "description"}]` — the same as a release's `age_rating`
  minus `is_adult`.
- `sorting`: `[{"value", "label", "description"}]`, the 6 values of the spec enum.
- `genres`: `[{"id", "name"}]` — 35 genres, the same IDs as `GET /anime/genres` returns.
- `years`: a plain array of integers, ascending, **only years that have releases**
  (`1995`…`2026` without `1997`, `2000`, `2002`).
- A data quirk: the description of `ONA` starts with a Cyrillic "О" (`"ОNA"`).

**Conclusion:** the references reuse existing models — `Genre` (without image/count),
`AgeRating` (with `is_adult=None`), `ValueDescription[str]` — plus `SortingOption` for the
sorting list's `label`.

## Catalog filters (checked 2026-10-16)

Requests: about 50 `GET /anime/catalog/releases` calls with `limit=1` (to compare `total`) or
`limit=50` (to inspect items), trimmed with `include=`, plus one `POST` with the same filters.

- **`f[genres]` is AND:** genre 14 → 699, genre 29 → 629, both → 314, and all 50 items of the
  first page have both genres. (Genres 15 + 24 → 0: no release has both.)
- **Every other list filter is OR:** `f[types]=TV` 1533 + `MOVIE` 148 = `TV,MOVIE` 1681; the
  same arithmetic holds for `seasons`, `age_ratings`, `publish_statuses`,
  `production_statuses`.
- **Years are inclusive:** `from_year=2020&to_year=2020` → 106 releases, all from 2020;
  `from_year=2020` 1006 + `to_year=2020` 1008 − 106 = 1908 = the whole catalog. `from > to` → 0.
- **`f[search]`** gives exactly the same counts as `/app/search/releases` for five queries
  (`а` 16, `и` 18, `the` 18, `магия` 20, `сезон` 11) — same engine, same ~20 cap. An empty
  `f[search]=` returns the whole catalog.
- **Sorting:** without `f[sorting]` the order equals `FRESH_AT_DESC`. `RATING_DESC` followed
  `added_in_users_favorites` (38933, 37905, 37427, …), i.e. popularity, not `rating.average`.
- **Invalid values are not reported:** `f[types]=FOO`, `f[genres]=abc` and `f[genres]=999999`
  → `total: 0`; `f[sorting]=NOPE`, `f[years][from_year]=abc` and unknown keys like
  `f[unknown]=x` are ignored (the whole catalog). Only `page=0` (and `limit` outside 1–50) is a
  422.
- **A page past the end** (`page=100000`) → `200` with `"data": []`.
- **Items** are bare releases plus `genres`.
- **`POST` with a JSON body** (`{"page", "limit", "f": {...}}`) returned the same IDs and total
  as `GET` with the same filters.

**Conclusion:** `client.catalog.releases()` uses `GET`. Because the API silently swallows wrong
values, the SDK validates them itself: list filters and `sorting` against the spec `enum`s (the
`Literal` types in `aniliberty.models.catalog`, kept in sync with the spec by a test),
`year_from <= year_to`, and list-vs-string mistakes. Ranges of `page`/`limit` are left to the
API's 422.

## Rate limiting (probed 2026-10-16)

To see how the API limits clients, `GET https://aniliberty.top/api/v1/app/status` was sent
from one IP — first 120 times sequentially, then 180 more in batches of 10 concurrent requests
(300 in total), stopping at the first 429.

No request got a 429, and no response carried `Retry-After`, `X-RateLimit-*` or `RateLimit-*`
headers. The probe was deliberately not pushed further.

**Conclusion:** the limit for `/app/status`, if there is one, is above that rate; other
endpoints may be limited differently. The shape of a 429 response is still unknown, so the
SDK handles it the generic way:

- 429 is retried up to 3 times for any method (the request wasn't processed). The delay is
  `Retry-After` (seconds or an HTTP date, measured from the response's `Date`), or exponential
  backoff of 1 s, 2 s, 4 s if there's none. A `Retry-After` above 60 s isn't waited out:
  `RateLimitError` is raised at once with that value in `retry_after`.
- 5xx and network errors/timeouts are retried the same way, but only for idempotent methods
  (`GET`, `HEAD`, `OPTIONS`, `PUT`, `DELETE`): after those it's unknown whether a `POST`
  already took effect.
- Besides retries, the client keeps at most 5 requests in flight (`max_concurrency`) and
  starts consecutive requests at least 0.1 s apart, so even a large `asyncio.gather` stays
  around 10 requests per second.

## How the SDK maps responses to exceptions

Derived from the bodies above (404, 422, HTML pages) and the spec; recorded in the
`tests/cassettes/test_*` cassettes of `tests/integration/test_app.py`.

| Response | Exception |
|---|---|
| `text/html` body, status below 500 (including 200) | `AccessBlockedError` — with `Accept: application/json` the API never answers with HTML, so this is the edge in front of it |
| `text/html` body, 5xx | `ServerError` — Cloudflare renders its own origin errors (502, 520, ...) as HTML too, and those are worth retrying |
| 2xx with an invalid JSON body | `ResponseParseError` (body text in `payload`) |
| 404 | `NotFoundError` (`message` is `"Not found"`, the Laravel string stays in `payload`) |
| 422 | `ValidationError` (`errors` from the body) |
| 429 | `RateLimitError` (`retry_after` from `Retry-After` — seconds or an HTTP date — if any) |
| 401, 403 (JSON) | `AuthRequiredError` |
| other 5xx | `ServerError` |
| any other error status | `APIError` |
| no response (connection error, timeout) | `TransportError` |

## Open questions

- **429 response shape.** Not triggered by 300 requests to `/app/status` (see "Rate
  limiting"); body and headers of a real 429 are unknown.
- **5xx body shape.** Not observed.
- **WAF/challenge behaviour.** Not observed from the maintainer's network; Cloudflare is in front.
  What a challenge looks like (status, headers) is unknown.
- **Maximum `limit`** on `/genres/{id}/releases`, `/torrents`, `/franchises/random`,
  `/genres/random`, `/media/videos` (the catalog and the release endpoints: 50).
- **Authentication details** (token lifetime, refresh, 401/403 bodies) — step 4.1.
