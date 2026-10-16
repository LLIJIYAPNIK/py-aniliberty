# API reference

Everything below is importable from the top-level `aniliberty` package unless noted.

## Client

::: aniliberty.AniLiberty

## Resources

The namespaces of an `AniLiberty` instance: `client.app`, `client.releases`,
`client.releases.ratings`, `client.episodes`, `client.catalog` (with `client.catalog.references`), `client.schedule`, `client.genres`, `client.franchises`, `client.torrents`, `client.teams`, `client.media`, `client.auth` (with `client.auth.otp`, `client.auth.social`, `client.auth.password`), `client.me` (with `client.me.favorites`, `client.me.collections` and their `references`, `client.me.views`). Not meant to be created directly — import from `aniliberty.resources` only
for type annotations.

::: aniliberty.resources.AppResource

::: aniliberty.resources.ReleasesResource

::: aniliberty.resources.RatingsResource

::: aniliberty.resources.EpisodesResource

::: aniliberty.resources.CatalogResource

::: aniliberty.resources.CatalogReferencesResource

::: aniliberty.resources.ScheduleResource

::: aniliberty.resources.GenresResource

::: aniliberty.resources.FranchisesResource

::: aniliberty.resources.TorrentsResource

::: aniliberty.resources.TeamsResource

::: aniliberty.resources.MediaResource

::: aniliberty.resources.AuthResource

::: aniliberty.resources.OtpResource

::: aniliberty.resources.SocialAuthResource

::: aniliberty.resources.PasswordResource

::: aniliberty.resources.MeResource

::: aniliberty.resources.FavoritesResource

::: aniliberty.resources.FavoritesReferencesResource
    options:
      inherited_members: true

::: aniliberty.resources.CollectionsResource

::: aniliberty.resources.CollectionsReferencesResource
    options:
      inherited_members: true

::: aniliberty.resources.ViewsResource

## Pagination

::: aniliberty.Page

## Models

### Releases

::: aniliberty.Release

::: aniliberty.ReleaseName

::: aniliberty.AgeRating

::: aniliberty.ReleaseRating

::: aniliberty.UserRating

::: aniliberty.ExternalRating

::: aniliberty.ReleaseMember

::: aniliberty.Sponsor

::: aniliberty.Genre

### Episodes

::: aniliberty.Episode

::: aniliberty.SkipRange

### Franchises

::: aniliberty.Franchise

::: aniliberty.FranchiseRelease

### Torrents

::: aniliberty.Torrent

::: aniliberty.TorrentCodec

::: aniliberty.TorrentMember

::: aniliberty.TorrentFile

### Teams

::: aniliberty.Team

::: aniliberty.TeamRole

::: aniliberty.TeamMember

### Media

::: aniliberty.Promotion

::: aniliberty.Video

::: aniliberty.VideoOrigin

### Schedule

::: aniliberty.ScheduledRelease

::: aniliberty.ScheduleNow

### Catalog

::: aniliberty.SortingOption

::: aniliberty.models.catalog
    options:
      members:
        - ReleaseType
        - Season
        - AgeRatingValue
        - PublishStatus
        - ProductionStatus
        - CatalogSorting
      show_root_heading: false
      show_root_toc_entry: false

### Common

::: aniliberty.ValueDescription

::: aniliberty.Image

::: aniliberty.ImageSet

::: aniliberty.LinkedAccount

::: aniliberty.models.common
    options:
      members:
        - EMPTY_VALUE_AS_NONE
      show_root_heading: false
      show_root_toc_entry: false

### Service

::: aniliberty.ApiStatus

::: aniliberty.RequestInfo

### Authentication

::: aniliberty.AuthToken

::: aniliberty.IssuedOtp

::: aniliberty.Otp

::: aniliberty.SocialLogin

::: aniliberty.models.auth
    options:
      members:
        - SocialProvider
      show_root_heading: false
      show_root_toc_entry: false

### Account

::: aniliberty.UserProfile

::: aniliberty.TorrentStats

::: aniliberty.CollectionItem

::: aniliberty.models.user
    options:
      members:
        - FavoritesSorting
        - CollectionType
      show_root_heading: false
      show_root_toc_entry: false

### Watch progress

::: aniliberty.Timecode

::: aniliberty.EpisodeView

::: aniliberty.HistoryEntry


## Exceptions

::: aniliberty.AniLibertyError

::: aniliberty.APIError

::: aniliberty.NotFoundError

::: aniliberty.ValidationError

::: aniliberty.RateLimitError

::: aniliberty.AuthRequiredError

::: aniliberty.ServerError

::: aniliberty.AccessBlockedError

::: aniliberty.TransportError

::: aniliberty.ResponseParseError

## Low-level HTTP client

Available as `client.http`; `client.http.request(...)` is the escape hatch for endpoints the
SDK doesn't cover yet.

::: aniliberty.HttpClient
