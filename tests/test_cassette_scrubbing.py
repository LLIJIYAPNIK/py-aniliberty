"""Cassettes are committed, so the recording filters in conftest must strip account secrets.

What is secret comes from the auth research in docs/api-notes.md ("Authentication"): the
login body carries the password, login/OTP responses the session token, the profile the
login, passkey and e-mail, and authenticated release/torrent responses put the passkey into magnet
and announce URLs.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from conftest import (
    SCRUBBED_CREDENTIALS,
    SCRUBBED_IP,
    SCRUBBED_PK,
    SCRUBBED_SECRETS,
    _scrub_request,
    _scrub_response,
)
from vcr.request import Request

URL = "https://aniliberty.top/api/v1/accounts/users/auth/login"


def recorded_body(payload: str | bytes) -> str | bytes:
    response = {"headers": {}, "body": {"string": payload}}
    return _scrub_response(response)["body"]["string"]


def test_vcr_config_wires_both_filters(vcr_config: dict[str, Any]) -> None:
    assert vcr_config["before_record_request"] is _scrub_request
    assert vcr_config["before_record_response"] is _scrub_response
    assert {"authorization", "cookie"} <= set(vcr_config["filter_headers"])


def test_login_credentials_are_replaced_in_request_body() -> None:
    body = json.dumps({"login": "real-user", "password": "s3cr3t!"}).encode()
    original = Request("POST", URL, body, {"Content-Type": "application/json"})

    scrubbed = _scrub_request(original)

    assert json.loads(scrubbed.body) == {
        "login": SCRUBBED_CREDENTIALS["login"],
        "password": SCRUBBED_CREDENTIALS["password"],
    }
    assert b"s3cr3t" not in scrubbed.body
    assert original.body == body  # the live request isn't touched


def test_password_reset_body_is_scrubbed_but_empty_values_are_kept() -> None:
    body = json.dumps(
        {"token": "t", "password": "n3w!", "password_confirmation": "n3w!", "login": ""}
    ).encode()

    scrubbed = json.loads(_scrub_request(Request("POST", URL, body, {})).body)

    assert scrubbed == {
        "token": "t",
        "password": SCRUBBED_CREDENTIALS["password"],
        "password_confirmation": SCRUBBED_CREDENTIALS["password_confirmation"],
        "login": "",
    }


def test_other_request_bodies_are_kept() -> None:
    for body in (b'{"device_id": "abc"}', b"[1, 2]", b"not json", None):
        request = Request("POST", URL, body, {})
        assert _scrub_request(request).body == body


def test_passkey_in_request_url_is_replaced() -> None:
    url = "https://aniliberty.top/api/v1/anime/torrents/rss?pk=abc123&x=1"
    request = Request("GET", url, None, {})

    assert _scrub_request(request).uri.endswith(f"?pk={SCRUBBED_PK}&x=1")


def test_token_passkey_and_email_are_replaced_in_response_body() -> None:
    body = json.dumps(
        {
            "token": "s9HYwZrealtoken",
            "login": "RealUser",
            "email": "me@example.org",
            "torrents": {"passkey": "deadbeef", "uploaded": None},
        }
    )

    scrubbed = json.loads(recorded_body(body))

    assert scrubbed["token"] == SCRUBBED_SECRETS["token"]
    assert scrubbed["login"] == SCRUBBED_CREDENTIALS["login"]
    assert scrubbed["email"] == SCRUBBED_SECRETS["email"]
    assert scrubbed["torrents"] == {"passkey": SCRUBBED_SECRETS["passkey"], "uploaded": None}


def test_null_token_after_logout_stays_null() -> None:
    assert recorded_body(b'{"token":null}') == b'{"token":null}'


def test_passkey_in_magnet_urls_is_replaced_in_bytes_body() -> None:
    # vcrpy hands bodies over as bytes while recording; the API escapes the slashes.
    body = (
        rb'{"magnet":"magnet:?xt=urn:btih:17ce&tr=http:\/\/tr.libria.fun:2710\/announce'
        rb'?pk=deadbeef&tr=x","ip":"198.51.100.7"}'
    )

    scrubbed = recorded_body(body)

    assert isinstance(scrubbed, bytes)
    assert b"deadbeef" not in scrubbed
    assert f"announce?pk={SCRUBBED_PK}&tr=x".encode() in scrubbed
    assert SCRUBBED_IP.encode() in scrubbed


def test_escaped_quotes_inside_secret_values_are_consumed() -> None:
    body = r'{"token": "a\"b", "next": "kept"}'

    assert json.loads(recorded_body(body)) == {"token": SCRUBBED_SECRETS["token"], "next": "kept"}


def test_set_cookie_with_session_token_is_dropped() -> None:
    response = {
        "headers": {"Set-Cookie": ["_al1=s9HYwZrealtoken; path=/; HttpOnly"], "Server": ["x"]},
        "body": {"string": b""},
    }

    assert _scrub_response(response)["headers"] == {"Server": ["x"]}


def test_recording_account_values_are_replaced_anywhere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANILIBERTY_LOGIN", "RealUser")
    monkeypatch.setenv("ANILIBERTY_PASSWORD", "s3cr3t!")
    body = b'{"nickname":"realuser","note":"s3cr3t!","other":"kept"}'

    assert json.loads(recorded_body(body)) == {
        "nickname": SCRUBBED_CREDENTIALS["login"],
        "note": SCRUBBED_CREDENTIALS["password"],
        "other": "kept",
    }
