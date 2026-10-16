"""Exception hierarchy and messages."""

from __future__ import annotations

import pytest

from aniliberty import (
    AccessBlockedError,
    AniLibertyError,
    APIError,
    AuthRequiredError,
    NotFoundError,
    RateLimitError,
    ResponseParseError,
    ServerError,
    TransportError,
    ValidationError,
)

URL = "https://aniliberty.top/api/v1/x"


@pytest.mark.parametrize(
    "cls",
    [
        NotFoundError,
        ValidationError,
        RateLimitError,
        AuthRequiredError,
        ServerError,
        AccessBlockedError,
    ],
)
def test_api_errors_share_base_and_message_format(cls: type[APIError]) -> None:
    error = cls("Boom", status_code=499, method="GET", url=URL, payload={"a": 1})

    assert isinstance(error, APIError)
    assert isinstance(error, AniLibertyError)
    assert str(error) == f"HTTP 499: Boom (GET {URL})"
    assert error.payload == {"a": 1}


def test_validation_error_defaults_to_no_field_errors() -> None:
    error = ValidationError("Invalid", status_code=422, method="GET", url=URL)
    assert error.errors == {}


def test_rate_limit_error_defaults_to_no_retry_after() -> None:
    error = RateLimitError("Too Many Requests", status_code=429, method="GET", url=URL)
    assert error.retry_after is None


def test_transport_and_parse_errors_are_sdk_errors_but_not_api_errors() -> None:
    transport = TransportError("Request failed", method="GET", url=URL)
    parse = ResponseParseError("Bad JSON", url=URL, payload="{")

    for error in (transport, parse):
        assert isinstance(error, AniLibertyError)
        assert not isinstance(error, APIError)
    assert str(transport) == f"Request failed (GET {URL})"
    assert str(parse) == f"Bad JSON ({URL})"
    assert parse.payload == "{"
