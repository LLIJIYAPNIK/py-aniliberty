"""Favorites: adding and removing releases, listing them with filters, their references.

client.me.favorites works like a small catalog of the user's own: ids() for a quick
membership check, releases()/iter_releases() with the catalog's filters, references.*() for
the values those filters can take — but only the values that occur in the user's favorites.

Run it with an account's credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD. The script
only touches the releases it adds itself and removes them at the end, so favorites you had
before are left as they were.
"""

import asyncio
import os

from aniliberty import AniLiberty

# Three releases of different years: Frieren (2023) and Shield Hero (2019) are both
# "Приключения" (genre 27) and "Драма" (8), Dandadan (2024) is neither.
ALIASES = ["sousou-no-frieren", "tate-no-yuusha-no-nariagari", "dandadan"]


async def main() -> None:
    async with AniLiberty() as client:
        await client.auth.login(
            login=os.environ["ANILIBERTY_LOGIN"], password=os.environ["ANILIBERTY_PASSWORD"]
        )
        favorites = client.me.favorites
        releases = await asyncio.gather(*(client.releases.get(alias) for alias in ALIASES))
        before = set(await favorites.ids())
        ours = [release for release in releases if release.id not in before]

        try:
            # add() takes IDs or Release objects, as many as you like, and returns the IDs of
            # everything in favorites afterwards. Adding a release that is already there is
            # a no-op — and so, note, is adding the ID of a release that doesn't exist: the
            # API accepts it without complaint, so don't rely on add() to validate IDs.
            ids = await favorites.add(*ours)
            print("Added:", all(release.id in ids for release in releases))

            # releases() is a Page of full releases with genres and episodes. Without
            # sorting, the most recently added come first; "YEAR_DESC" and others work as in
            # the catalog ("RATING_*" sorts by how many users favorited a release).
            page = await favorites.releases(sorting="YEAR_DESC", limit=50)
            ours_ids = {release.id for release in releases}
            mine = [release for release in page.items if release.id in ours_ids]
            print("Newest first:", [(r.year, r.name.main) for r in mine])

            # Filters as in the catalog, except years: here it's a list of years (a range
            # works), not year_from/year_to. Genres must ALL match, the other lists ANY.
            years = [r.year for r in releases if r.year is not None]
            by_year = await favorites.releases(years=[min(years)])
            print("From the oldest year:", [r.name.main for r in by_year.items if r.id in ours_ids])
            both_genres = await favorites.releases(genres=[27, 8])
            print(
                "Adventure AND drama:", [r.name.main for r in both_genres.items if r.id in ours_ids]
            )

            # iter_releases() walks every page for you; limit only changes the page size.
            count = 0
            async for release in favorites.iter_releases(limit=1):
                count += release.id in ours_ids
            print("Walked page by page, found ours:", count)

            # The references list only what's in favorites (unlike catalog.references),
            # except sorting(), which is always complete.
            ref_years = await favorites.references.years()
            print("Years in favorites include ours:", set(years) <= set(ref_years))
            ratings = await favorites.references.age_ratings()
            genre_ids = {genre.id for genre in await favorites.references.genres()}
            types = {t.value for t in await favorites.references.types()}
            print(
                "Genres and types in favorites include ours:", {27, 8} <= genre_ids, "TV" in types
            )
            print("Age ratings in favorites include 16+:", "R16_PLUS" in {r.value for r in ratings})
            print(
                "Sorting options:",
                [option.value for option in await favorites.references.sorting()],
            )
        finally:
            # remove() also takes IDs or Release objects; removing what isn't there is a
            # no-op. Only the releases this script added are removed.
            if ours:
                left = await favorites.remove(*ours)
                print("Cleaned up:", set(left) == before)
            await client.auth.logout()


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Added: True
# Newest first: [(2024, 'Дандадан'), (2023, 'Провожающая в последний путь Фрирен'), (2019, 'Восхождение героя щита')]
# From the oldest year: ['Восхождение героя щита']
# Adventure AND drama: ['Провожающая в последний путь Фрирен', 'Восхождение героя щита']
# Walked page by page, found ours: 3
# Years in favorites include ours: True
# Genres and types in favorites include ours: True True
# Age ratings in favorites include 16+: True
# Sorting options: ['CREATED_AT_DESC', 'CREATED_AT_ASC', 'FRESH_AT_DESC', 'FRESH_AT_ASC', 'RATING_DESC', 'RATING_ASC', 'YEAR_DESC', 'YEAR_ASC']
# Cleaned up: True
