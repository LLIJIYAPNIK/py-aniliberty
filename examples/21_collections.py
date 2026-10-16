"""Collections: "planned", "watching", "watched", "postponed", "abandoned".

Every release can be in at most one of the user's five collections — putting it into
another one moves it. client.me.collections.ids() tells where everything is,
releases(collection) lists one collection with the same filters as favorites, and
references.*() covers all collections together.

Run it with an account's credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD. The script
puts the original placement of its releases back at the end, so your collections are left
as they were.

One catch, found by running this very script (docs/api-notes.md): the API also applies
collection changes in the background. A release removed right after it was added can come
back a minute later, and removing a release that has been in a collection for a while can
take minutes to stick. So the cleanup repeats the removal until two checks a minute apart
agree that the releases are gone — the script runs for a few minutes.
"""

import asyncio
import os
from collections import defaultdict

from aniliberty import AniLiberty, ValidationError
from aniliberty.resources import CollectionsResource

ALIASES = ["sousou-no-frieren", "tate-no-yuusha-no-nariagari", "dandadan"]


async def remove_for_good(collections: CollectionsResource, release_ids: set[int]) -> None:
    """Remove releases, and keep removing them until they stay out of the collections."""
    clean_checks = 0
    for _ in range(10):
        present = {item.release_id for item in await collections.ids()} & release_ids
        if present:
            await collections.remove(*present)
            clean_checks = 0
        else:
            clean_checks += 1
            if clean_checks == 2:
                return
        await asyncio.sleep(60)
    raise TimeoutError("the releases kept coming back")


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
            # iter_releases() walks every page of one collection; limit is the page size.
            watched = [r.name.main async for r in collections.iter_releases("WATCHED", limit=10)]
            print("Watched, all pages:", [name for name in watched if name == frieren.name.main])

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
            ratings = {r.value for r in await collections.references.age_ratings()}
            genre_ids = {genre.id for genre in await collections.references.genres()}
            print("Genres in the collections include Adventure (27):", 27 in genre_ids)
            ref_years = await collections.references.years()
            print(
                "Years in the collections, newest first:",
                ref_years == sorted(ref_years, reverse=True),
            )
            print("Age ratings in the collections include 16+:", "R16_PLUS" in ratings)
        finally:
            # Put things back: remove what wasn't in any collection, move the rest back.
            # remove() takes a release out of whatever collection it is in.
            await remove_for_good(collections, ours - set(before))
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
# Watched, all pages: ['Провожающая в последний путь Фрирен']
# Ours per collection: {'PLANNED': 2, 'WATCHED': 1}
# Lowercase collection: Unknown collection value 'watched'; expected one of: PLANNED, WATCHED, WATCHING, POSTPONED, ABANDONED
# limit=100: ['limit']
# Release types in the collections include TV: True
# Genres in the collections include Adventure (27): True
# Years in the collections, newest first: True
# Age ratings in the collections include 16+: True
# Restored: True
