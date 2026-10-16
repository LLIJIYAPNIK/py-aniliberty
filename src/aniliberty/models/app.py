"""Models of the ``Приложение.*`` tags of the spec."""

from pydantic import Field

from aniliberty.models._base import AniLibertyModel


class RequestInfo(AniLibertyModel):
    """What the API knows about the client that sent the request (geolocated by IP).

    Spec schema: ``responses.v1.app.status`` → ``request``. All fields are optional: the spec
    marks none of them required, and geolocation can fail.

    Attributes:
        ip: The client's IP address as seen by the API.
        country: Country name, in English (e.g. ``"The Netherlands"``).
        iso_code: ISO 3166-1 alpha-2 country code (e.g. ``"NL"``).
        timezone: IANA time zone name (e.g. ``"Europe/Amsterdam"``).
    """

    ip: str | None = None
    country: str | None = None
    iso_code: str | None = None
    timezone: str | None = None


class ApiStatus(AniLibertyModel):
    """Status of the API, returned by ``client.app.status()``.

    Spec schema: ``responses.v1.app.status``.

    Attributes:
        is_alive: Whether the API reports itself as working.
        available_api_endpoints: Hosts the API can be reached at, e.g.
            ``["https://aniliberty.top"]`` — origins without the ``/api/v1`` suffix.
        request: What the API knows about the caller, if it sent that.
    """

    is_alive: bool
    available_api_endpoints: list[str] = Field(default_factory=list)
    request: RequestInfo | None = None
