"""Shared pytest fixtures."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

CASSETTE_DIR = Path(__file__).parent / "cassettes"

SCRUBBED_IP = "203.0.113.10"
"""Stand-in for the recording machine's IP (TEST-NET-3, reserved for documentation)."""

_IP_FIELD = re.compile(r'("ip"\s*:\s*)"[^"]*"')
_IP_FIELD_BYTES = re.compile(_IP_FIELD.pattern.encode())


def _scrub_response(response: dict[str, Any]) -> dict[str, Any]:
    """Drop cookies and the caller's IP from a response before it's written to a cassette.

    ``GET /app/status`` echoes the client's IP address back in ``request.ip``; cassettes are
    committed, so it's replaced with ``SCRUBBED_IP``.
    """
    headers = response.get("headers", {})
    for name in list(headers):
        if name.lower() == "set-cookie":
            del headers[name]
    body = response.get("body", {})
    if isinstance(body, dict) and isinstance(body.get("string"), str | bytes):
        body["string"] = _scrub_ip(body["string"])
    return response


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
        "before_record_response": _scrub_response,
    }
