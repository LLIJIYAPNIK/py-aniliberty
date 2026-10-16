"""Collections: "planned", "watching", "watched", "postponed", "abandoned".

Every release can be in at most one of the user's five collections — putting it into
another one moves it. client.me.collections.ids() tells where everything is,
releases(collection) lists one collection with the same filters as favorites, and
references.*() covers all collections together.

Run it with an account's credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD. The script
puts the original placement of its releases back at the end, so your collections are left
as they were.
"""

import asyncio
import os
from collections import defaultdict

from aniliberty import AniLiberty, ValidationError

ALIASES = ["sousou-no-frieren", "tate-no-yuusha-no-nariagari", "dandadan"]


async def main() -> None:
    async with AniLiberty() as client:
        await client.auth.login(
            login=os.environ["ANILIBERTY_LOGIN"], password=os.environ["ANILIBERTY_PASSWORD"]
        )
        collections = client.me.collections
        frieren, shield_hero, dandadan = await asyncio.gather(
            *(client.releases.get(alias) for alias in ALIASES)
        )
        ours = {frieren.id, shield_hero.id, dandadan.id}
        # ids() returns CollectionItem(release_id, collection) — remember where our releases
        # were, to restore it afterwards.
        before = {item.release_id: item.collection for item in await collections.ids()}

        try:
            # add() puts releases into the collection given as to=...
            await collections.add(frieren, shield_hero, dandadan, to="PLANNED")
            # ... and moves a release that is in another collection.
            items = await collections.add(frieren, to="WATCHED")
            where = {item.release_id: item.collection for item in items if item.release_id in ours}
            print(
                "Placement:",
                {
                    release.name.main: where[release.id]
                    for release in (frieren, shield_hero, dandadan)
                },
            )

            # releases() takes the collection first — it's required, the API answers 422
            # without one — and the favorites' filters. Collections can't be sorted: the most
            # recently added come first.
            planned = await collections.releases("PLANNED", limit=50)
            print("Planned:", sorted(r.name.main for r in planned.items if r.id in ours))
            older = await collections.releases("PLANNED", years=range(2015, 2020))
            print("Planned, 2015–2019:", [r.name.main for r in older.items if r.id in ours])

            # A typical use: group the user's collections by type.
            grouped: dict[str, list[int]] = defaultdict(list)
            for item in await collections.ids():
                grouped[item.collection].append(item.release_id)
            print(
                "Ours per collection:",
                {name: len(set(ids) & ours) for name, ids in sorted(grouped.items())},
            )

            # The collection name is checked before sending (as is any filter value).
            try:
                await collections.releases("watched")  # type: ignore[arg-type]
            except ValueError as error:
                print("Lowercase collection:", error)
            # limit is checked by the API: 1..50.
            try:
                await collections.releases("WATCHED", limit=100)
            except ValidationError as error:
                print("limit=100:", list(error.errors))

            # The references cover all five collections at once.
            types = [t.value for t in await collections.references.types()]
            print("Release types in the collections include TV:", "TV" in types)
        finally:
            # Put things back: remove what wasn't in any collection, move the rest back.
            # remove() takes a release out of whatever collection it is in.
            new = [release_id for release_id in ours if release_id not in before]
            if new:
                await collections.remove(*new)
            for release_id, collection in before.items():
                if release_id in ours:
                    await collections.add(release_id, to=collection)
            after = {item.release_id: item.collection for item in await collections.ids()}
            print("Restored:", after == before)
            await client.auth.logout()


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Placement: {'Провожающая в последний путь Фрирен': 'WATCHED', 'Восхождение героя щита': 'PLANNED', 'Дандадан': 'PLANNED'}
# Planned: ['Восхождение героя щита', 'Дандадан']
# Planned, 2015–2019: ['Восхождение героя щита']
# Ours per collection: {'PLANNED': 2, 'WATCHED': 1}
# Lowercase collection: Unknown collection value 'watched'; expected one of: PLANNED, WATCHED, WATCHING, POSTPONED, ABANDONED
# limit=100: ['limit']
# Release types in the collections include TV: True
# Restored: True
