# API reference

Everything below is importable from the top-level `aniliberty` package unless noted.

## Client

::: aniliberty.AniLiberty

## Resources

The namespaces of an `AniLiberty` instance: `client.app`, `client.releases`,
`client.episodes`. Not meant to be created directly — import from `aniliberty.resources` only
for type annotations.

::: aniliberty.resources.AppResource

::: aniliberty.resources.ReleasesResource

::: aniliberty.resources.EpisodesResource

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
