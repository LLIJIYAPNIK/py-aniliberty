"""Teams: the people behind AniLibria — its teams ("leagues"), roles and members.

Each of the three endpoints returns its whole list in one response, with no pagination or
filters, so the SDK hands you plain lists and you group or filter them in Python. A typical
use is joining them with release members: client.releases.members() tells you who voiced a
release, client.teams.users() tells you which team those people are in and what else they do.
"""

import asyncio
from collections import Counter

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # The three lists are independent, so fetch them concurrently. The SDK still caps
        # how many requests are in flight (max_concurrency, 5 by default).
        teams, roles, members = await asyncio.gather(
            client.teams.list(), client.teams.roles(), client.teams.users()
        )

        # Teams and roles come sorted by sort_order; members do NOT — the API interleaves
        # teams. Count members per team via member.team (a full Team, equal to the one from
        # teams.list(), so it works as a dict/Counter key).
        per_team = Counter(member.team for member in members)
        print(f"{len(teams)} teams, {len(roles)} roles, {len(members)} members")
        for team in teams:
            description = f" — {team.description}" if team.description else ""
            print(f"  {team.title}{description}: {per_team[team]} members")

        # A role's color is a CSS hex string or None (most roles have none).
        colored = [f"{role.title} {role.color}" for role in roles if role.color][:3]
        print("Colored roles:", colored)

        # Most-common roles. A member can have several roles, so the sum exceeds the
        # number of members.
        role_counts = Counter(role.title for member in members for role in member.roles)
        print("Most common roles:", role_counts.most_common(3))

        # Flags for interns and members on vacation.
        on_vacation = sum(member.is_vacation for member in members)
        interns = sum(member.is_intern for member in members)
        print(f"On vacation: {on_vacation}, interns: {interns}")

        # Only some members have a linked site account (member.user); its nickname can
        # differ from the team nickname, or be None.
        accounts = [member for member in members if member.user is not None]
        print(f"With a site account: {len(accounts)}")

        # Join with release members by nickname: who worked on Frieren, and in which team.
        by_nickname = {member.nickname: member for member in members}
        print("Frieren credits:")
        for credit in await client.releases.members("sousou-no-frieren"):
            member = by_nickname.get(credit.nickname)
            # Use .get(): a credited nickname isn't always in the current teams list.
            team = member.team.title if member else "not in teams.users()"
            role = credit.role.description if credit.role else "?"
            print(f"  {credit.nickname} ({role}): {team}")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 7 teams, 33 roles, 164 members
#   0 Лига — Руководство проекта: 1 members
#   I Лига — Совет: 6 members
#   II Лига — Высшая: 20 members
#   III Лига — Мастера: 49 members
#   IV Лига — Основа: 67 members
#   Академия: 13 members
#   Не поддаётся классификации лиговой системы: 8 members
# Colored roles: ['Актёр #339966', 'Звукорежиссёр #800000', 'Переводчик #ebd800']
# Most common roles: [('Актёр', 42), ('Звукорежиссёр', 30), ('Графический локализатор', 27)]
# On vacation: 38, interns: 19
# With a site account: 25
# Frieren credits:
#   Amikiri (Озвучка): II Лига
#   Hekomi (Озвучка): III Лига
#   Anzen (Озвучка): III Лига
#   Arato (Озвучка): IV Лига
#   im4x (Работа со звуком): III Лига
#   Neri (Оформление): not in teams.users()
