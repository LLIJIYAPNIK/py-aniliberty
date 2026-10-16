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

**Conclusion:** URL fields stay `str` holding the raw value; image models get a computed
property that joins the path with the site origin (derived from `base_url` by dropping the
`/api/v1` suffix). HLS URLs are returned untouched — the query string is part of the link.

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
- **Maximum `limit`** on endpoints other than the catalog (`/releases/list`, `/genres/{id}/releases`,
  `/torrents`, `/releases/latest`, `/random`, ...).
- **Authentication details** (token lifetime, refresh, 401/403 bodies) — step 4.1.
