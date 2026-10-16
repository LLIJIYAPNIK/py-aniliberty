"""The smallest useful program: create a client, check the API, fetch a few releases.

Everything in the SDK goes through one AniLiberty instance. Its methods are grouped into
namespaces that follow the API's own structure — client.app, client.releases,
client.episodes — and every call returns a typed, immutable pydantic model, never a raw dict.
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    # AniLiberty is an async context manager: it owns an httpx.AsyncClient (a connection
    # pool) and closes it on exit. Prefer `async with`; without it, remember to call
    # `await client.aclose()` yourself. A closed client can't be reopened.
    #
    # No arguments are needed. The default base_url is the API's main server,
    # https://aniliberty.top/api/v1 — see example 15 (coming later) for mirrors.
    async with AniLiberty() as client:
        # A cheap health check. `available_api_endpoints` lists hosts the API itself
        # advertises — handy if the main one ever becomes unreachable.
        status = await client.app.status()
        print("API alive:", status.is_alive)
        print("Hosts:", status.available_api_endpoints)

        # The releases that got new episodes most recently. `limit` must be 1..50; the API
        # rejects anything else with a 422, raised as aniliberty.ValidationError.
        releases = await client.releases.latest(limit=3)
        for release in releases:
            # `name.main` is the Russian title, `name.english` the English/romanized one.
            print(f"- [{release.id}] {release.name.main} / {release.name.english}")

        # Any release by its numeric ID or by its alias (the slug in site URLs).
        frieren = await client.releases.get("sousou-no-frieren")
        print(frieren.name.main, frieren.year, f"{len(frieren.episodes)} episodes")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# API alive: True
# Hosts: ['https://aniliberty.top']
# - [10297] О моём перерождении в меч 2 / Tensei Shitara Ken Deshita 2nd Season
# - [10324] Во всеоружии: Сила артефактов / Tempal: Item no Chikara
# - [10318] Операция: Семейка Ёдзакура 2. Часть 2 / Yozakura-san Chi no Daisakusen 2nd Season Part 2
# Провожающая в последний путь Фрирен 2023 28 episodes
