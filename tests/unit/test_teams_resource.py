"""client.teams: requested paths and models on edge-case JSON."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, TeamMember

TEAM = {"id": "baee450f", "title": "Академия", "sort_order": 6, "description": None}
MEMBER: dict[str, Any] = {
    "id": "4e69cf24",
    "nickname": "TiflonBagdat",
    "is_intern": True,
    "sort_order": 3,
    "is_vacation": False,
    "user": {
        "id": 42,
        "nickname": None,
        "avatar": {"preview": None, "thumbnail": None, "optimized": {"preview": None}},
    },
    "team": TEAM,
    "roles": [{"id": "5abda221", "title": "Актёр", "color": None, "sort_order": 3}],
}


def test_member_with_empty_account_fields() -> None:
    member = TeamMember.model_validate(MEMBER)

    assert member.team.description is None
    assert member.roles[0].color is None
    assert member.user is not None
    assert member.user.nickname is None
    assert member.user.avatar is not None
    assert member.user.avatar.preview_url is None


def test_member_without_account() -> None:
    assert TeamMember.model_validate({**MEMBER, "user": None}).user is None


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("list", "/api/v1/teams/", [TEAM]),
        ("roles", "/api/v1/teams/roles", []),
        ("users", "/api/v1/teams/users", [MEMBER]),
    ],
)
async def test_requested_paths(method: str, path: str, payload: Any) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        result = await getattr(client.teams, method)()
    await http_client.aclose()

    assert seen[0].url.path == path
    assert len(result) == len(payload)
