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

## Authentication (checked 2026-10-16)

### What the spec says

The spec defines one security scheme, `sessionToken` (`type: http`, `scheme: bearer`,
"Bearer auth session token"), and sets it as the **global** `security` requirement. 31
operations repeat it explicitly; the other 49 (all public `anime/*`, `app/*`, `media/*`,
`teams/*` operations plus the login/OTP/password endpoints) do not override it. Strictly read,
that would make every operation require a token, but no unauthenticated request in this
document got a 401/403 — the public endpoints answer normally.

**Conclusion:** the global requirement is a spec artefact. "Requires auth" in
`docs/endpoints.md` means the operation declares `security` itself.

### Live checks

Made with a test account created for this research (credentials from environment variables,
never written to the repo or cassettes). Requests are `httpx` with `Accept: application/json`;
the cookie jar was cleared between requests unless the cookie itself was being tested.

**Login** — `POST /accounts/users/auth/login` with `{"login": ..., "password": ...}`:

- Success → 200 `{"token": "<32 characters>"}`. The token is an opaque random string (letters
  and digits) — not a JWT and not the Laravel-encrypted blob of the spec's example, so there is
  no expiry inside it to read.
- The same response sets an `HttpOnly` cookie `_al1` whose value **is the token**, with
  `Max-Age=691200` (8 days), `path=/`, `SameSite=lax`.
- `login` accepts the login (case-insensitively) or the account's e-mail. A form-encoded body
  works the same as JSON.
- Every login creates a **new** token; earlier tokens stay valid (independent sessions).
- Wrong login or password → **401** `{"token": null, "error": "Не удалось авторизоваться.
  Неправильные логин/пароль"}` — note `error`, not Laravel's usual `message`. The same for a
  non-existent account.
- Missing fields → 422 `{"errors": {"login": [...], "password": [...]}}`.

**Using the token:**

- `Authorization: Bearer <token>` works (the scheme name is case-insensitive). The `_al1`
  cookie alone works too, and every request authenticated by it gets a fresh `Set-Cookie` with
  a new 8-day expiry (sliding); requests authenticated by the header get no cookie.
- The bare token in `Authorization` (no `Bearer`) or as `?token=` doesn't authenticate.
- No token, a garbage token, a tampered token, a logged-out token — all the same **403**
  `{"message": "This action is unauthorized."}` on every protected endpoint tried
  (`/accounts/users/me/profile`, `/me/favorites/ids`, `/me/views/history`,
  `/auth/logout`, `/otp/accept`, `/anime/releases/{id}/episodes/timecodes`). The spec promises
  401 for some of them and 404 "user is not authorized" for the profile; neither happens.
  There is no `WWW-Authenticate` header and nothing in the body distinguishes "missing" from
  "expired/invalid".
- An invalid token **does not break public endpoints**: `/app/status` and
  `/anime/releases/latest` with a garbage bearer answer 200 as usual.

**Logout** — `POST /accounts/users/auth/logout` with the token → 200 `{"token": null}` and a
`Set-Cookie` that clears `_al1`. Only that token is revoked (another session's token keeps
working); logging out again with it → 403.

**What a token changes in public responses:**

- HLS URLs of episodes (also those nested in `GET /anime/releases/{idOrAlias}`) switch their
  query string from `isAuthorized=0&isWithVideoAds=1&isWithVideoAdsAlways=1` to
  `isAuthorized=1&...` with the account's ad flags. The URLs are opaque to the SDK either way.
- `magnet` links of torrents get the account's **passkey** in the announce URL
  (`...announce?pk=<passkey>`). The passkey is also `torrents.passkey` of the profile — it's
  the `pk` parameter of the `.torrent`/RSS endpoints. It's a secret: cassettes recorded with a
  token are scrubbed of it.

**Profile** — `GET /accounts/users/me/profile` returns `id`, `login`, `email`, `nickname`,
`avatar` (all paths `null` without an avatar, like other images), `torrents` (`passkey`,
`uploaded`, `downloaded` — the last two `null` on a new account), `is_banned`, `created_at`,
and three undocumented ad flags `is_with_video_ads`, `is_with_content_ads`,
`is_with_video_ads_always`.

Checked again for step 4.3 (`client.me.profile()` → `UserProfile`): the spec's
`is_with_ads` is **not** sent — the three flags above come instead, and the SDK models all
four as optional. `created_at` has a time zone (`+00:00`). Without a valid session the answer
is the usual 403, not the 404 "user is not authorized" of the spec. The spec's `include`/
`exclude` parameters (field selection) aren't exposed: a trimmed response wouldn't fit the
model anyway. `email` and `torrents.passkey` are secrets of the account; the passkey is kept
out of the model's `repr`, and both are scrubbed from cassettes.

**Other account endpoints without a session:**

- `POST /accounts/otp/get` without `device_id` → 422; `POST /accounts/otp/login` with an
  unknown code → JSON 404 "No query results for model [...OneTimePassword]".
- `GET /accounts/users/auth/social/vk/login` → 200 `{"url": "https://oauth.vk.ru/authorize?...",
  "state": "..."}`. An unknown provider → **500** `{"message": "Server Error"}` (the spec says
  404) — the only 5xx body seen so far.
- `GET /accounts/users/auth/social/authenticate` with an unknown `state` → 404 with
  `Content-Type: text/html` and an **empty body**, despite `Accept: application/json`. The
  SDK's "HTML means the edge blocked us" rule used to misreport that as `AccessBlockedError`;
  since step 4.2 an empty HTML body is mapped by its status instead.

### One-time codes, social login, password recovery (checked 2026-10-16, step 4.2)

**OTP** — logging a device in with a code confirmed from another, logged-in device:

1. `POST /accounts/otp/get` `{"device_id": "..."}` (no session needed) → 200
   `{"otp": {"code": "997903", "user_id": null, "device_id": "...", "expired_at": "..."},
   "remaining_time": 299.66}`. The code is a **string** of 6 digits, lives 5 minutes
   (`remaining_time` is fractional), and asking again for the same `device_id` returns the
   same code. `device_id` can be any non-empty string.
2. `POST /accounts/otp/accept` `{"code": ...}` with the session of the confirming account →
   200 with an **empty `text/html` body** (also on repeating it). Without a session → 403;
   an unknown code → JSON 404. `code` must be a number greater than 0 (`"abc"`, `0` → 422);
   the string from step 1 is accepted as is.
3. `POST /accounts/otp/login` `{"code": ..., "device_id": ...}` → 200 `{"token": ...}` plus
   the `_al1` cookie, like a password login. The code is then used up (→ 404). Before step 2
   it answers **500** `{"message": "Server Error"}` (the spec says 401). With a wrong
   `device_id` → 404. And with a **valid session token** it answers **403** — it's for
   guests only (an invalid token is treated as none).

None of the other auth endpoints care about a token: login with a valid or garbage bearer
works, and so do `otp/get` and `social/*/login`.

**Social login** — `GET /accounts/users/auth/social/{provider}/login` works for all four
providers of the spec enum (`vk`, `google`, `patreon`, `discord`) and returns
`{"url": "<OAuth page>", "state": "..."}`, the `state` also being in the `url`. A provider in
other letter case (`VK`) or an unknown one → 500. `GET .../social/authenticate` without
`state` → 422, with an unknown one → the empty `text/html` 404 above. Completing the OAuth
flow in a browser was not tried.

**Password recovery** — `POST /accounts/users/auth/password/forget`: no `email` or a
malformed one → 422; an e-mail of **no account** → 200 with an empty `text/html` body, as the
spec describes for a real one (no account enumeration; not tried with a real address to avoid
sending mail). `POST .../password/reset`: missing fields → 422, `password` ≠
`password_confirmation` → 422, unknown `token` → JSON 404.

### What the SDK does

- `AniLiberty(token=...)` / `client.token` hold the session token; it's sent as
  `Authorization: Bearer <token>` (replacing an `Authorization` header from `headers`).
  `client.auth.login()`, `client.auth.otp.login()` and `client.auth.social.authenticate()`
  store the new token; `client.auth.logout()` clears it (also when the API rejects it with
  403 — the session is over either way; on other errors it's kept).
- The `_al1` cookie is dropped from the httpx cookie jar right after a login, so the token
  is the only credential (`_scrub_response` also drops it from cassettes along with every
  `Set-Cookie`).
- `client.auth.otp.login()` is sent without the token (`HttpClient.request(...,
  with_token=False)`), since the API refuses it from a logged-in caller.
- A `text/html` response with an **empty** body is not treated as an anti-bot page: an empty
  2xx is "no content" (`None`), an empty 404 is `NotFoundError`.
- `client.auth.social.login()` checks `provider` against the spec enum before sending, rather
  than letting the API answer 500.
- There is no refresh endpoint, and the token carries no expiry. The cookie suggests an 8-day
  lifetime, possibly sliding; whether the server-side session itself expires after 8 days
  (and whether bearer use extends it) can only be seen by waiting — unverified. An expired
  session looks like any other 403.
- 401 (wrong credentials at login) and 403 (anything with a missing/invalid/expired session)
  both map to `AuthRequiredError`. Its `message` comes from `message`, or from `error` when
  there's no `message` (the login 401). Protected methods called without a token simply get
  the API's 403 — the SDK doesn't pre-check, so a missing and a stale token behave the same.
- Only the account's own endpoints need the token; passing a stale one to public endpoints is
  harmless.

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

## Schedule (checked 2026-10-16, a Friday)

Requests: `GET /anime/schedule/now`, `GET /anime/schedule/week` (twice, a few minutes apart).

- **`/week` doesn't match the spec:** the spec documents `{"data": [...]}`, the live API returns
  the array itself (37 items). Not ordered by weekday.
- **`/now`** is `{"yesterday": [...], "today": [...], "tomorrow": [...]}` as documented; each list
  holds the releases whose `publish_day` is that weekday (Thursday, Friday, Saturday on a
  Friday). Every release of `/now` is also in `/week`. Whether "today" follows UTC or Moscow
  time is still open — both were Friday at the time.
- **Items:** `{release, published_release_episode, next_release_episode_number,
  full_season_is_released}`; `release` comes with `genres`, and one had the empty
  `{"value": null}` `season` seen before.
- **`published_release_episode`** was `null` on 15 of 37. Every non-null one was dated within
  the current calendar week starting on Monday (2026-10-12 onwards), including one for a
  Saturday release whose episode came out on Tuesday; Sunday releases whose episodes were out
  the previous Sunday had `null`. So it means "the episode published this week", not "the
  episode of this publish day".
- **`next_release_episode_number`** was `null` only for the one release with
  `full_season_is_released: true`.

**Conclusion:** `client.schedule.week()` accepts both the live array and the spec's envelope;
`ScheduledRelease.full_season_is_released` is required (present on all 45 items seen), the
episode and next number are optional.

## Genres (checked 2026-10-16)

Requests: `GET /anime/genres`, `/anime/genres/14`, `/999999`, `/abc`, `/anime/genres/random` with
`limit` 1, 3, 35, 36, 50, 51, 0, `abc`, and `/anime/genres/14/releases` with various `page`/`limit`.

- **List and single genre** match the spec: `{id, name, image, total_releases}`, no `null`s.
  35 genres, in the API's own order (not by name or ID).
- **Missing genre:** `/genres/999999`, `/genres/abc` and `/genres/999999/releases` → the JSON 404.
- **`/random`:** `limit` 1–35 returns that many; **0 or anything above the number of genres
  silently returns all 35**; a non-number is a 422.
- **`/{id}/releases`:**
  - `limit` is **1 to 30** here (`31` → `422 "Поле limit не может быть больше 30."`) —
    unlike 50 in the catalog and the release endpoints; `limit=0` gives the default page
    size, 15;
  - **`page` ≤ 0 is treated as 1** (200, `current_page: 1`), unlike the catalog's 422;
  - `total` equals the catalog's `f[genres]=<id>` total and the genre's `total_releases`
    (699 for genre 14); items come with `genres`, and every item has the genre;
  - the order is the API's own — neither by `fresh_at` nor by `created_at`.
- A release with **`fresh_at: null`** appeared here (the model already allows it).

**Conclusion:** `client.genres` has `list()`, `get()`, `random()`, `releases()`/`iter_releases()`,
accepting a genre ID or a `Genre`. The silent clamping of `random`'s `limit` and of `page` is
harmless and only documented, not validated.

## Franchises (checked 2026-10-16)

Requests: `GET /anime/franchises`, `/anime/franchises/{id}` (existing, all-zero UUID, `abc`),
`/anime/franchises/random` with `limit` omitted, 0, 1, 3, 50, 51, 1000, and
`/anime/franchises/release/{id}` for releases with and without a franchise, by alias and for a
missing release.

- **List:** 271 franchises in one array, in the API's own order, without `franchise_releases`.
- **`rating` is `null` on all 271** (the spec says number). `first_year`, `last_year`,
  `total_episodes`, `total_releases` were `null` on 2, `total_duration` on 4. The two franchises
  with `total_releases: null` still had 2 releases each in `franchise_releases` — the totals are
  precomputed and can be stale. One of them had an image with all paths `null`.
- **Single franchise** adds `franchise_releases: [{id, franchise_id, release_id, sort_order,
  release}]`, ordered by `sort_order` 1, 2, … — chronological in every franchise looked at.
  The embedded `release` has no `genres` or `episodes`.
- **Missing franchise** (unknown UUID or `abc`) → the JSON 404.
- **`/random`:** without `limit`, with `0`, or with more than there are (`1000`) it returns **all
  271**; `50` and `51` return exactly that many — no maximum below the total.
- **`/release/{releaseId}`:** the franchises with `franchise_releases`; **`[]` for a release
  outside any franchise**; **an alias gives the 404 "release not found"** even though the
  release exists (`quan-zhi-gao-shou`); a missing release ID → 404.

**Conclusion:** `Franchise` treats every total and `rating` as optional;
`client.franchises.for_release()` accepts only an `int` or a `Release` and rejects strings, so an
alias fails with a clear `TypeError` instead of the misleading 404. `random()`'s docstring warns
that leaving `limit` out returns everything.

## Torrents (checked 2026-10-16)

Requests: `GET /anime/torrents` (`limit` 20, 50, 51, 100; two pages of 50), `/anime/torrents/{id}`
and `/{hash}` (lower and upper case), a missing ID and hash, `/anime/torrents/release/{id}` (by
ID, by alias, missing), `/anime/torrents/{hash}/file` (by hash and by ID, with
`Accept: application/json` and `*/*`, missing), `/anime/torrents/rss` and `/rss/release/{id}`.

- **List:** paginated (3128 torrents), `limit` **1–50**. Items include `release` (without
  `genres`/`episodes`) and `torrent_members`.
- **Fields over 100 torrents:** `bitrate` was `null` on 87; everything else was always set.
  `codec` is a value + description with `label`, `label_color`, `label_is_visible`
  (`x265/HEVC` → `"HEVC"`, `#FFEB3B`, visible; `x264/AVC` → `"AVC"`, no color, hidden).
  `size` is the size of the video files (e.g. 40535930212), not of the `.torrent` file.
  `torrent_members` was non-empty on 28 of 100, every role `HEVC`; `user` was `null` on 8 and
  `external_url` on 9 of those 28.
- **`/{hashOrId}`** accepts the numeric ID or the info hash in any letter case; unknown → JSON
  404.
- **`/release/{releaseId}`:** **numeric ID only** — an alias (`one-piece`) gives the 404
  "release not found", like the franchises endpoint. A missing release → 404.
- **The file:** `200 application/x-bittorrent` with
  `Content-Disposition: attachment; filename="<label>.torrent"`, **also with
  `Accept: application/json`**, no redirect. Files seen: 22 792 and 388 202 bytes. A missing
  torrent with the JSON `Accept` → JSON 404; with `*/*` → the HTML 404 page (the same Laravel
  behaviour as everywhere).
- **RSS:** `200 application/xml` (also with the JSON `Accept`), RSS 2.0. Each `<item>` has
  `<title>`, `<guid>` (the hash), `<pubDate>`, `<torrentId>`, `<releaseId>`, an HTML
  `<description>` with the poster, and an `<enclosure>` pointing to the `.torrent` file with
  `type="application/x-bittorrent"` and `length` = `size`. `/rss` without `limit` has 10 items.
  A missing release → JSON 404.
- The `pk` (user passkey) parameter of the file and RSS endpoints isn't used: it's for
  authenticated users (phase 4).

**Conclusion:** the SDK reads the file and the feeds through two new low-level calls,
`client.http.request_raw()` (whole body) and `client.http.stream()` (chunks), with the same
limits, retries and error mapping as JSON requests. `torrents.download()` streams to
`<name>.part` and renames it when complete. `for_release()`/`rss_for_release()` accept only an
`int` or a `Release`, like `franchises.for_release()`.

## Teams (checked 2026-10-16)

Requests: `GET /teams/`, `/teams` (no trailing slash), `/teams/roles`, `/teams/users`, all
without parameters; cross-checked with `GET /anime/releases/sousou-no-frieren/members`.

- **Shape:** all three return a bare JSON array, no pagination. 7 teams, 33 roles, 164 members.
- **`/teams/` and `/teams` answer the same** (200, same body, no redirect). The SDK requests
  `/teams/`, as spelled in the spec.
- **Order:** teams and roles come sorted by `sort_order`; **members don't** — teams are
  interleaved, and `sort_order` is the position within the member's team, from 1.
- **Nulls:** `team.description` is `null` on 2 of 7 teams, `role.color` on 20 of 33 roles (the
  spec says string for both). Colors are hex strings in mixed case (`#B523C5` and `#b523c5`).
- **`user`** (the linked site account) is `null` on 139 of 164 members; when present, its
  `nickname` differs from the team nickname on 5 members and is `null` on 1, and 3 avatars have
  all paths `null`. Avatar paths are relative, like other images.
- Every member has a `team` and at least one role; every embedded team and role is also in
  `/teams/` and `/teams/roles`. Nicknames are unique.
- **Release members vs team members:** release credits match team members by nickname, but not
  always — one of Frieren's six credited members (`Neri`) isn't in `/teams/users`.
- `include`/`exclude` query parameters are declared in the spec; the SDK doesn't expose them
  (no other resource does either).

**Conclusion:** `Team.description`, `TeamRole.color`, `TeamMember.user` and the account's
`nickname`/`avatar` are optional; `TeamMember.team` is required. `client.teams.users()`'s
docstring says the list isn't sorted.

## Media (checked 2026-10-16)

Requests: `GET /media/promotions` three times in a row; `GET /media/videos` with `limit`
omitted, 1, 0, -1, 50, 51, 100, 1000 and `abc`.

- **Shape:** both return a **bare JSON array** — the spec documents `{"data": [...]}` for both
  (the same mismatch as `/anime/schedule/week`). The SDK accepts either shape.
- **Promotions:** 8 items, the same set every time but **shuffled on each call** (the spec says
  "in random order"). Three kinds, told apart by which fields are set:
  - featured release (4): `release` is a full release object (with `genres`), `url` and
    `url_label` are `null`;
  - the site's own link (2): `url` + `url_label`, no `release`;
  - a text-only announcement (1): neither `url` nor `release`;
  - a paid ad (1): `is_ad: true`, `url` + `url_label`, `title` and `description` `null`.
  `ad_erid` and `ad_origin` are `null` on all 8 (no type to check against the spec's `string`).
  Image paths are relative (`/storage/media/promotions/images/...`), like other images.
- **Videos:** newest first by `created_at`; without `limit` — **10**; maximum **50** — `51`,
  `100`, `1000` → 422 `{"errors": {"limit": ["Поле limit не может быть больше 50."]}}`,
  `abc` → 422 "должно быть числом". **`limit=0` and `limit=-1` return all 1037 videos**
  (~1.4 MB).
- All 1037 videos are on `www.youtube.com`, every `origin.type.value` is `YOUTUBE_PLAYLIST`
  (the spec's only enum value). `views` is `null` on 49, `comments` on 39, the image paths on 4.
  `is_announce` on a video matches `is_announce` of its playlist (40 videos, all from
  "Анонсы аниме-сезонов").
- `include`/`exclude` are declared in the spec; the SDK doesn't expose them.

**Conclusion:** `client.media.promotions()` and `client.media.videos()` unwrap `data` if it's
there and otherwise take the list as is. `Video.views`/`comments` are optional;
`VideoOrigin.type` is a `ValueDescription[str]` rather than a `Literal`, so a new source type
doesn't break parsing. `videos()`'s docstring warns that `limit` ≤ 0 returns everything.

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

## Unknown routes and methods (checked 2026-10-16)

- **Unknown path** (`GET /no/such/path`) → JSON 404 `{"message": "The route api/v1/no/such/path
  could not be found."}` — a different message from the "No query results for model" 404 of a
  missing record, same `NotFoundError` in the SDK.
- **Wrong method** (`POST /app/status`) → JSON 405 `{"message": "The POST method is not
  supported for route api/v1/app/status. Supported methods: GET, HEAD."}` → plain `APIError`.

## How the SDK maps responses to exceptions

Derived from the bodies above (404, 422, 401/403, HTML pages) and the spec; recorded in the
cassettes of `tests/integration/test_app.py` and `tests/integration/test_auth.py`.

| Response | Exception |
|---|---|
| `text/html` page (non-blank body), status below 500 (including 200) | `AccessBlockedError` — with `Accept: application/json` the API never answers with an HTML page, so this is the edge in front of it |
| `text/html` with an empty body | mapped by status like JSON: `None` for 2xx (OTP accept, password forget), `NotFoundError` for 404 (unknown social-login state) |
| `text/html` body, 5xx | `ServerError` — Cloudflare renders its own origin errors (502, 520, ...) as HTML too, and those are worth retrying |
| 2xx with an invalid JSON body | `ResponseParseError` (body text in `payload`) |
| 404 | `NotFoundError` (`message` is `"Not found"`, the Laravel string stays in `payload`) |
| 422 | `ValidationError` (`errors` from the body) |
| 429 | `RateLimitError` (`retry_after` from `Retry-After` — seconds or an HTTP date — if any) |
| 401, 403 (JSON) | `AuthRequiredError` — 403 for a missing/invalid session, 401 for wrong login credentials (message from `error`, see "Authentication") |
| other 5xx | `ServerError` |
| any other error status (e.g. 405 for `POST /app/status`) | `APIError` |
| no response (connection error, timeout) | `TransportError` |

## Open questions

- **429 response shape.** Not triggered by 300 requests to `/app/status` (see "Rate
  limiting"); body and headers of a real 429 are unknown.
- **5xx body shape.** Seen once: an unknown social provider answers 500
  `{"message": "Server Error"}` (see "Authentication"). Others (overload, maintenance) not
  observed.
- **WAF/challenge behaviour.** Not observed from the maintainer's network; Cloudflare is in front.
  What a challenge looks like (status, headers) is unknown.
- **Maximum `limit`** on `/media/videos` and `/anime/torrents/rss` (known so far: the catalog,
  the release endpoints and `/torrents` 50, `/genres/{id}/releases` 30; `/genres/random` and
  `/franchises/random` return everything when `limit` is out of range).
- **Session lifetime.** No refresh endpoint and no expiry in the token; the `_al1` cookie says
  8 days (sliding). Whether the server-side session really expires then — unverified.
- **Schedule time zone** — whether `/schedule/now`'s "today" is UTC or Moscow time.
