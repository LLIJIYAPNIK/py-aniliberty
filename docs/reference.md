# API reference

Everything below is importable from the top-level `aniliberty` package unless noted.

## Client

::: aniliberty.AniLiberty

## Resources

The namespaces of an `AniLiberty` instance: `client.app`, `client.releases`,
`client.episodes`, `client.catalog` (with `client.catalog.references`), `client.schedule`. Not meant to be created directly — import from `aniliberty.resources` only
for type annotations.

::: aniliberty.resources.AppResource

::: aniliberty.resources.ReleasesResource

::: aniliberty.resources.EpisodesResource

::: aniliberty.resources.CatalogResource

::: aniliberty.resources.CatalogReferencesResource

::: aniliberty.resources.ScheduleResource

## Pagination

::: aniliberty.Page

## Models

### Releases

::: aniliberty.Release

::: aniliberty.ReleaseName

::: aniliberty.AgeRating

::: aniliberty.ReleaseRating

::: aniliberty.ExternalRating

::: aniliberty.ReleaseMember

::: aniliberty.ReleaseMemberUser

::: aniliberty.Sponsor

::: aniliberty.Genre

### Episodes

::: aniliberty.Episode

::: aniliberty.SkipRange

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

### Service

::: aniliberty.ApiStatus

::: aniliberty.RequestInfo

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
