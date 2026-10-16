"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from vcr.request import Request

CASSETTE_DIR = Path(__file__).parent / "cassettes"

SCRUBBED_IP = "203.0.113.10"
"""Stand-in for the recording machine's IP (TEST-NET-3, reserved for documentation)."""

_IP_FIELD = re.compile(r'("ip"\s*:\s*)"[^"]*"')
_IP_FIELD_BYTES = re.compile(_IP_FIELD.pattern.encode())

SCRUBBED_CREDENTIALS = {
    "login": "test-login",
    "password": "test-password",
    "password_confirmation": "test-password",
}
"""Stand-ins for credentials in recorded request bodies (login, password reset).

Empty values are kept as they are, so a cassette of a validation error still shows what was
sent.
"""

SCRUBBED_SECRETS = {
    "login": SCRUBBED_CREDENTIALS["login"],
    "token": "scrubbed-session-token",
    "passkey": "scrubbed-passkey",
    "email": "user@example.com",
}
"""Stand-ins for account secrets in recorded response bodies, by JSON field name.

``token`` is the session token returned by login/OTP; ``login`` (half of the credentials),
``passkey`` and ``email`` are in the profile. Public responses have no ``login`` field —
users there have a ``nickname``, which is kept. The token also comes as the ``_al1`` cookie,
which ``_scrub_response`` drops with every other ``Set-Cookie``.
"""

SCRUBBED_PK = "scrubbed-passkey"
"""Stand-in for the torrent passkey that authenticated responses put into ``?pk=`` of URLs."""

_SECRET_FIELDS = re.compile(r'("(' + "|".join(SCRUBBED_SECRETS) + r')"\s*:\s*)"(?:[^"\\]|\\.)*"')
_PK_PARAM = re.compile(r'([?&]pk=)[^&"\s\\]+')


def _scrub_response(response: dict[str, Any]) -> dict[str, Any]:
    """Drop cookies, the caller's IP and account secrets from a response before recording.

    ``GET /app/status`` echoes the client's IP address back in ``request.ip``; cassettes are
    committed, so it's replaced with ``SCRUBBED_IP``. Secrets are replaced by
    ``_scrub_secrets``.
    """
    headers = response.get("headers", {})
    for name in list(headers):
        if name.lower() == "set-cookie":
            del headers[name]
    body = response.get("body", {})
    if isinstance(body, dict) and isinstance(body.get("string"), str | bytes):
        body["string"] = _scrub_secrets(_scrub_ip(body["string"]))
    return response


def _scrub_request(request: Request) -> Request:
    """Replace credentials in a login body and the passkey in the URL of a recorded request.

    The ``Authorization`` header (the session token) is dropped by ``filter_headers``. vcrpy
    runs this filter on replayed requests too, so matching isn't affected.
    """
    request = copy.copy(request)
    request.uri = _PK_PARAM.sub(rf"\g<1>{SCRUBBED_PK}", request.uri)
    if request.body:
        try:
            payload = json.loads(request.body)
        except ValueError:
            return request
        if isinstance(payload, dict) and SCRUBBED_CREDENTIALS.keys() & payload.keys():
            for field, stand_in in SCRUBBED_CREDENTIALS.items():
                if payload.get(field):
                    payload[field] = stand_in
            request.body = json.dumps(payload).encode()
    return request


def _scrub_secrets(body: str | bytes) -> str | bytes:
    """Replace the account's login, session token, passkey and e-mail with stand-ins."""
    is_bytes = isinstance(body, bytes)
    text = body.decode("utf-8", errors="surrogateescape") if is_bytes else body
    text = _SECRET_FIELDS.sub(lambda m: f'{m[1]}"{SCRUBBED_SECRETS[m[2]]}"', text)
    text = _PK_PARAM.sub(rf"\g<1>{SCRUBBED_PK}", text)
    # The account's own values wherever else they show up — e.g. the profile's nickname,
    # which defaults to the login.
    for variable, field in (("ANILIBERTY_LOGIN", "login"), ("ANILIBERTY_PASSWORD", "password")):
        value = os.environ.get(variable)
        if value:
            text = re.sub(re.escape(value), SCRUBBED_CREDENTIALS[field], text, flags=re.IGNORECASE)
    return text.encode("utf-8", errors="surrogateescape") if is_bytes else text


def _scrub_ip(body: str | bytes) -> str | bytes:
    # vcrpy hands the body over as bytes while recording; it's str in loaded cassettes.
    if isinstance(body, bytes):
        return _IP_FIELD_BYTES.sub(rf'\1"{SCRUBBED_IP}"'.encode(), body)
    return _IP_FIELD.sub(rf'\1"{SCRUBBED_IP}"', body)


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest) -> str:
    """One cassette directory per test module: tests/cassettes/<module>/<test>.yaml.

    Cassettes are named after the test function, so a flat directory would let two modules
    with a same-named test (``test_random`` in releases and genres) share — and clobber — one
    cassette.
    """
    return str(CASSETTE_DIR / request.module.__name__.rsplit(".", 1)[-1])


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    return {
        "record_mode": "once",
        "filter_headers": ["authorization", "cookie"],
        "decode_compressed_response": True,
        "before_record_request": _scrub_request,
        "before_record_response": _scrub_response,
    }


@dataclass(frozen=True)
class Credentials:
    login: str
    password: str


@pytest.fixture
def credentials(request: pytest.FixtureRequest, vcr_cassette_dir: str) -> Credentials:
    """The test account's login and password, from ``ANILIBERTY_LOGIN``/``ANILIBERTY_PASSWORD``.

    Only needed to record a cassette: when it already exists, the requests are replayed and the
    stand-ins of ``SCRUBBED_CREDENTIALS`` are used (request bodies aren't matched). Without the
    variables and without a cassette the test is skipped instead of failing against the API.
    """
    login = os.environ.get("ANILIBERTY_LOGIN")
    password = os.environ.get("ANILIBERTY_PASSWORD")
    if login and password:
        return Credentials(login, password)
    cassette = Path(vcr_cassette_dir) / f"{request.node.name}.yaml"
    if cassette.exists():
        return Credentials(SCRUBBED_CREDENTIALS["login"], SCRUBBED_CREDENTIALS["password"])
    pytest.skip("set ANILIBERTY_LOGIN and ANILIBERTY_PASSWORD to record this test's cassette")


@pytest.fixture
def live_wait(
    request: pytest.FixtureRequest, vcr_cassette_dir: str
) -> Callable[[float], Awaitable[None]]:
    """``await live_wait(seconds)`` sleeps while the test's cassette is being recorded only.

    For endpoints whose effect shows up with a delay (timecodes reach the history about a
    minute after they are saved), a test polls with waits in between. Replaying the cassette
    gives back the same sequence of responses, so the waits are skipped then.
    """
    recording = not (Path(vcr_cassette_dir) / f"{request.node.name}.yaml").exists()

    async def wait(seconds: float) -> None:
        if recording:
            await asyncio.sleep(seconds)

    return wait
