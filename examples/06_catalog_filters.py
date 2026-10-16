"""Browsing the catalog with filters and sorting: client.catalog.releases().

The catalog is the whole release library (about two thousand releases) with the filters of
the site's "Catalog" page. Every filter is optional; how they combine matters:

    genres                         ALL of the given genres must be present (AND)
    types, seasons, age_ratings,   ANY of the given values is enough (OR)
    publish/production_statuses
    different filters              all of them must match (AND)
    year_from / year_to            inclusive on both ends

See docs/guides/catalog-filters.md for the full story.
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # Genre IDs aren't something to hardcode: take them from the catalog references by
        # name. The Genre objects themselves can be passed as filter values, too.
        genres = {genre.name: genre for genre in await client.catalog.references.genres()}
        action, fantasy = genres["Экшен"], genres["Фэнтези"]

        # `limit=1` is the cheapest way to learn how many releases match: `total` comes with
        # every page. Here it shows that genres are combined with AND — fewer releases have
        # both genres than either one alone.
        for selection in ([action], [fantasy], [action, fantasy]):
            page = await client.catalog.releases(genres=selection, limit=1)
            names = " + ".join(genre.name for genre in selection)
            print(f"{names}: {page.total}")

        # Lists of other filters are combined with OR: TV or ONA.
        tv = await client.catalog.releases(types=["TV"], limit=1)
        ona = await client.catalog.releases(types=["ONA"], limit=1)
        both = await client.catalog.releases(types=["TV", "ONA"], limit=1)
        print(f"TV {tv.total} + ONA {ona.total} = TV or ONA {both.total}")

        # Several filters together, sorted by year. Old, finished years keep this list (and
        # the output below) stable over time. Year bounds are inclusive.
        page = await client.catalog.releases(
            genres=[action],
            types=["TV"],
            year_from=2000,
            year_to=2009,
            sorting="YEAR_ASC",
            limit=5,
        )
        print(f"Action TV series of the 2000s: {page.total}, the first five by year:")
        for release in page.items:
            print(f"  {release.year} {release.name.main}")

        # `search` matches names like the quick search does, and is capped the same way
        # (about 20 results) — use it to narrow down a title, combined with other filters.
        page = await client.catalog.releases(search="frieren", types=["TV"])
        print("Search + type:", [release.name.main for release in page.items])

        # The API silently returns nothing for an unknown filter value (or ignores it), so
        # the SDK checks values before sending — a typo fails loudly instead. The parameters
        # are typed with the allowed values, so mypy/pyright flag this line even before it
        # runs; the ignore comment is only there because the mistake is deliberate.
        try:
            await client.catalog.releases(types=["tv"])  # type: ignore[list-item]
        except ValueError as error:
            print("ValueError:", error)
        try:
            await client.catalog.releases(year_from=2020, year_to=2010)
        except ValueError as error:
            print("ValueError:", error)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Экшен: 699
# Фэнтези: 629
# Экшен + Фэнтези: 314
# TV 1533 + ONA 92 = TV or ONA 1625
# Action TV series of the 2000s: 18, the first five by year:
#   2003 Крестовый поход Хроно
#   2003 Технолайз
#   2004 Блич
#   2004 Девы Розена
#   2006 Сильнейший в истории ученик Кейчи
# Search + type: ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
# ValueError: Unknown types value 'tv'; expected one of: TV, ONA, WEB, OVA, OAD, MOVIE, DORAMA, SPECIAL
# ValueError: year_from (2020) is after year_to (2010)
