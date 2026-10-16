# Upgrading to 1.0

Before `1.0.0` the public API was reviewed for consistent names and signatures (roadmap step
5.1). The changes below break code written for `0.x`; everything else keeps working. Each
one is a single search-and-replace.

## Identifier parameters are named after what they identify

Methods that take a release or an episode now call the parameter `release` / `episode`,
like `genres.get(genre)`, `franchises.get(franchise)` and `torrents.get(torrent)` already
did — and, like those, they accept the model object as well as its ID.

| 0.x | 1.0 |
|---|---|
| `client.releases.get(id_or_alias=...)` | `client.releases.get(release=...)` |
| `client.releases.members(id_or_alias=...)` | `client.releases.members(release=...)` |
| `client.releases.timecodes(id_or_alias=...)` | `client.releases.timecodes(release=...)` |
| `client.releases.recommended(release_id=...)` | `client.releases.recommended(release=...)` |
| `client.episodes.get(episode_id=...)` | `client.episodes.get(episode=...)` |
| `client.episodes.timecode(episode_id=...)` | `client.episodes.timecode(episode=...)` |

Positional calls — `client.releases.get("sousou-no-frieren")` — are unaffected. New in 1.0:
these methods also take a `Release` / `Episode`, so `client.releases.get(release)` fetches
the full details of a release from a list, and `client.episodes.get(release.episodes[0])`
an episode with its release.

## `torrents.download()`: `path` is keyword-only

Arguments after the identifier are keyword-only everywhere in the SDK; `download()` was the
exception.

```python
# 0.x
await client.torrents.download(torrent, "downloads/")
# 1.0
await client.torrents.download(torrent, path="downloads/")
```

## Renamed methods

| 0.x | 1.0 | Why |
|---|---|---|
| `client.auth.otp.get(device_id=...)` | `client.auth.otp.issue(device_id=...)` | everywhere else `get()` fetches something that exists; this one issues a new code |
| `client.me.views.delete_timecodes(...)` | `client.me.views.remove_timecodes(...)` | favorites, collections and ratings call it `remove()` |

## One model for a linked site account

`ReleaseMemberUser` and `TeamMemberAccount` described the same thing — the site account of a
person in the credits or in a team — and are replaced by
[`LinkedAccount`][aniliberty.LinkedAccount]. The attributes that hold it
(`ReleaseMember.user`, `TorrentMember.user`, `TeamMember.user`) and its fields (`id`,
`nickname`, `avatar`) are unchanged; only imports and type annotations need updating:

```python
# 0.x
from aniliberty import ReleaseMemberUser, TeamMemberAccount

# 1.0
from aniliberty import LinkedAccount
```

## `HttpClient.discard_cookie()` is private

It only exists so that `client.auth` can drop the session cookie after a login. If you
called it yourself, call `client.http._discard_cookie(name)` — or better, don't keep the
cookie: the SDK authenticates with `client.token`.

## Not breaking, but new

- The `Literal` types — `ReleaseType`, `Season`, `AgeRatingValue`, `PublishStatus`,
  `ProductionStatus`, `CatalogSorting`, `FavoritesSorting`, `CollectionType`,
  `SocialProvider` — can be imported from `aniliberty` directly, not only from
  `aniliberty.models`.
- Every public method's docstring now has an example.
