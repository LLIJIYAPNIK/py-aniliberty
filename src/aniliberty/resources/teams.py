"""``client.teams`` — the ``Команды`` tag of the spec."""

from __future__ import annotations

import builtins

from aniliberty.models.team import Team, TeamMember, TeamRole
from aniliberty.resources._base import BaseResource


class TeamsResource(BaseResource):
    """AniLibria's own teams, roles and members, available as ``client.teams``.

    Each endpoint returns its whole list in one response (a few dozen teams and roles, a
    couple of hundred members); there is no pagination or filtering, so filter in Python.
    """

    ENDPOINTS = (
        ("GET", "/teams/"),
        ("GET", "/teams/roles"),
        ("GET", "/teams/users"),
    )

    async def list(self) -> builtins.list[Team]:
        """Get all teams.

        Returns:
            Every team, ordered by ``sort_order``.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``Team``.

        Example:
            ```python
            for team in await client.teams.list():
                print(team.title, team.description)
            ```
        """
        # The spec spells this path with a trailing slash; both forms answer the same.
        return await self._get("/teams/", builtins.list[Team])

    async def roles(self) -> builtins.list[TeamRole]:
        """Get all roles team members can have.

        Returns:
            Every role, ordered by ``sort_order``.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``TeamRole``.

        Example:
            ```python
            for role in await client.teams.roles():
                print(role.title, role.color)
            ```
        """
        return await self._get("/teams/roles", builtins.list[TeamRole])

    async def users(self) -> builtins.list[TeamMember]:
        """Get all team members, each with their team and roles.

        Returns:
            Every member. **Not sorted** by team: the API interleaves teams, so group by
            ``member.team`` and sort by ``member.sort_order`` yourself if order matters.

        Raises:
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``TeamMember``.

        Example:
            ```python
            members = await client.teams.users()
            actors = [m.nickname for m in members if any(r.title == "Актёр" for r in m.roles)]
            ```
        """
        return await self._get("/teams/users", builtins.list[TeamMember])
