"""Quick search by name — the search box of the site.

app.search_releases() is meant for "find this title": it matches Russian and English names
and aliases, returns at most ~20 releases, and has no paging, filters or sorting. For
browsing with filters, use the catalog (coming in a later version).
"""

import asyncio

from aniliberty import AniLiberty, ValidationError


async def main() -> None:
    async with AniLiberty() as client:
        # The same release is found by its Russian name, English name or alias.
        for query in ("Фрирен", "frieren", "sousou-no-frieren"):
            found = await client.app.search_releases(query)
            print(f"{query!r}: {[r.name.main for r in found]}")

        # Matching is fuzzy but punctuation-sensitive: with a space after the colon the
        # title is found, without it — nothing. If a query finds nothing, try variants.
        for query in ("Re: Zero", "Re:Zero"):
            found = await client.app.search_releases(query)
            print(f"{query!r}: {len(found)} results")

        # No matches is an empty list, not an error.
        print("Nonsense:", await client.app.search_releases("zzzzqqqxx"))

        # Search results are "bare" releases: no genres, members or episodes. Fetch the one
        # you need with releases.get() to get the full picture.
        [first, *_] = await client.app.search_releases("frieren")
        print("Search result has episodes:", len(first.episodes))
        full = await client.releases.get(first.id)
        print("Full release has episodes:", len(full.episodes))

        # An empty query is rejected by the API (422 -> ValidationError).
        try:
            await client.app.search_releases("")
        except ValidationError as error:
            print("Empty query:", error.errors)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 'Фрирен': ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
# 'frieren': ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
# 'sousou-no-frieren': ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
# 'Re: Zero': 6 results
# 'Re:Zero': 0 results
# Nonsense: []
# Search result has episodes: 0
# Full release has episodes: 28
# Empty query: {'query': ['Поле query обязательно для заполнения.']}
