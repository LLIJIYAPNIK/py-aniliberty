"""Team models (spec tag ``Команды``)."""

from __future__ import annotations

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import Image


class Team(AniLibertyModel):
    """An AniLibria team — one of the "leagues" the project's members are grouped into.

    Spec schema: ``models.teams.v1.team``.

    Attributes:
        id: Team ID (a UUID string).
        title: Team name in Russian, e.g. ``"II Лига"``.
        description: Short description in Russian, e.g. ``"Высшая"`` — ``None`` for some
            teams.
        sort_order: Position of the team in the list, from 0 (project leadership) up.
    """

    id: str
    title: str
    description: str | None = None
    sort_order: int


class TeamRole(AniLibertyModel):
    """A role a team member can have: voice actor, translator, timer, ...

    Spec schema: ``models.teams.v1.team.role``.

    Attributes:
        id: Role ID (a UUID string).
        title: Role name in Russian, e.g. ``"Актёр"``.
        color: The role's display color as a CSS hex string, e.g. ``"#339966"`` — ``None``
            for most roles, and not normalized (both ``"#B523C5"`` and ``"#b523c5"`` occur).
        sort_order: Position of the role in the list.
    """

    id: str
    title: str
    color: str | None = None
    sort_order: int


class TeamMemberAccount(AniLibertyModel):
    """The site account linked to a team member.

    Spec schema: ``models.teams.v1.team.user.account``.

    Attributes:
        id: User ID on the site.
        nickname: The account's nickname — can differ from the member's team nickname, or
            be ``None``.
        avatar: The account's avatar (its paths can be ``None``).
    """

    id: int
    nickname: str | None = None
    avatar: Image | None = None


class TeamMember(AniLibertyModel):
    """A member of an AniLibria team, with the team and their roles.

    Spec schema: items of ``responses.api.v1.teams.users`` (``models.teams.v1.team.user``
    with ``team``, ``user`` and ``roles`` added).

    Attributes:
        id: Member ID (a UUID string).
        nickname: The member's nickname in the team — the same name that appears in a
            release's ``members``.
        is_intern: Whether the member is an intern.
        is_vacation: Whether the member is on vacation.
        sort_order: Position of the member within their team, from 1.
        team: The team the member belongs to.
        roles: The member's roles (at least one for every member at the time of writing).
        user: The linked site account — ``None`` for most members.

    Example:
        ```python
        for member in await client.teams.users():
            print(member.nickname, member.team.title, [role.title for role in member.roles])
        ```
    """

    id: str
    nickname: str
    is_intern: bool = False
    is_vacation: bool = False
    sort_order: int
    team: Team
    roles: list[TeamRole] = Field(default_factory=list)
    user: TeamMemberAccount | None = None
