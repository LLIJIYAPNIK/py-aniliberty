"""client.teams against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Team, TeamMember, TeamRole


@pytest.mark.vcr
async def test_list() -> None:
    async with AniLiberty() as client:
        teams = await client.teams.list()

    assert teams
    assert all(isinstance(t, Team) and t.id and t.title for t in teams)
    orders = [t.sort_order for t in teams]
    assert orders == sorted(orders)


@pytest.mark.vcr
async def test_roles() -> None:
    async with AniLiberty() as client:
        roles = await client.teams.roles()

    assert len(roles) > 10
    assert all(isinstance(r, TeamRole) and r.id and r.title for r in roles)
    assert any(r.color is None for r in roles)
    assert all(r.color.startswith("#") for r in roles if r.color is not None)


@pytest.mark.vcr
async def test_users_reference_teams_and_roles() -> None:
    async with AniLiberty() as client:
        teams = await client.teams.list()
        roles = await client.teams.roles()
        members = await client.teams.users()

    assert len(members) > 100
    assert all(isinstance(m, TeamMember) and m.nickname and m.roles for m in members)
    assert len({m.id for m in members}) == len(members)
    # Every member's team and roles are the same objects the other two endpoints return.
    assert {m.team for m in members} <= set(teams)
    assert {r for m in members for r in m.roles} <= set(roles)

    with_account = [m for m in members if m.user is not None]
    assert with_account
    assert with_account != members  # most members have no linked account
    avatar = next(m.user.avatar for m in with_account if m.user and m.user.avatar)
    assert avatar.preview_url is None or avatar.preview_url.startswith("https://")
