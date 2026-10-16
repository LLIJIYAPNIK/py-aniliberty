"""Franchises: groups of related releases — seasons, movies, spin-offs — in watch order.

Typical use: from one release, find its franchise and list everything else in it. The
franchise's totals (releases, episodes, watch time) are precomputed by the API and can be
missing or stale, so count franchise_releases when the exact number matters.
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # All franchises come in one response (a few hundred), without their releases.
        franchises = await client.franchises.list()
        print(f"{len(franchises)} franchises")
        biggest = max(franchises, key=lambda f: f.total_releases or 0)
        print(f"Biggest: {biggest.name} — {biggest.total_releases} releases, ", end="")
        print(f"{biggest.total_episodes} episodes, {biggest.total_duration}")

        # get() adds the releases, in franchise order (chronological in every check so far).
        # It takes an ID or a Franchise object from list()/random().
        full = await client.franchises.get(biggest)
        print(f"{full.name} ({full.first_year}–{full.last_year}), first five:")
        for item in full.franchise_releases[:5]:
            release = item.release
            kind = release.type.description if release.type else "?"
            print(f"  {item.sort_order}. {release.year} [{kind}] {release.name.main}")

        # From a release to its franchise. Only a numeric ID or a Release object works here:
        # the API answers an alias with "release not found" even if the release exists, so
        # the SDK rejects a string right away instead of letting that confusing 404 through.
        release = await client.releases.get("sousou-no-frieren")
        for franchise in await client.franchises.for_release(release):
            titles = [item.release.name.main for item in franchise.franchise_releases]
            print(f"{release.name.main} belongs to «{franchise.name}»: {titles}")
        try:
            await client.franchises.for_release("sousou-no-frieren")  # type: ignore[arg-type]
        except TypeError as error:
            print("TypeError:", str(error).split(";")[0])

        # A release outside any franchise gives an empty list, not an error.
        print("Release 10324 franchises:", await client.franchises.for_release(10324))

        # random() without a limit returns ALL franchises — always pass one.
        print("Random:", [f.name for f in await client.franchises.random(limit=3)])


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 271 franchises
# Biggest: Моя геройская академия — 15 releases, 204 episodes, 3 дня 13 часов 12 минут
# Моя геройская академия (2016–2026), first five:
#   1. 2016 [ТВ] Моя геройская академия
#   2. 2017 [ТВ] Моя геройская академия 2
#   3. 2018 [ТВ] Моя геройская академия 3
#   4. 2018 [Фильм] Моя геройская академия: Два героя
#   5. 2019 [ТВ] Моя геройская академия 4
# Провожающая в последний путь Фрирен belongs to «Провожающая в последний путь Фрирен»: ['Провожающая в последний путь Фрирен', 'Провожающая в последний путь Фрирен 2']
# TypeError: Expected a release ID (int) or a Release, got 'sousou-no-frieren'
# Release 10324 franchises: []
# Random: ['Мой счастливый брак', 'Юно: Девушка, что воспевает любовь на грани этого мира', 'Клинок, рассекающий демонов']
