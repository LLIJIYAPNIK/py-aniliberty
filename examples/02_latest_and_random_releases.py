"""Ready-made selections of releases: latest, random and recommended.

All three return a plain list[Release] (no pagination) and take `limit` from 1 to 50. They
differ in which optional parts of Release the API fills in — worth knowing, because a field
the endpoint doesn't send is simply empty, not an error:

    latest()       genres, latest_episode
    random()       genres, background_covers
    recommended()  genres
"""

import asyncio

from aniliberty import AniLiberty, ValidationError


async def main() -> None:
    async with AniLiberty() as client:
        # --- latest -------------------------------------------------------------------
        # Only latest() fills in `latest_episode` — the newest episode of each release, so
        # a "new episodes" feed needs a single request.
        print("Latest:")
        for release in await client.releases.latest(limit=3):
            episode = release.latest_episode
            # `fresh_at` is when the release was last bumped (usually: a new episode came
            # out). Dates are timezone-aware datetimes, as the API sends them in UTC.
            print(f"  {release.fresh_at:%Y-%m-%d %H:%M} {release.name.main}", end="")
            print(f" — episode {episode.ordinal}" if episode else "")

        # --- random -------------------------------------------------------------------
        # Every call returns a different set, so this part of the output below will never
        # match a re-run.
        print("Random:")
        for release in await client.releases.random(limit=2):
            # Genres come as a list of Genre models; their `id` is what catalog filters
            # take, `name` is for display.
            genres = ", ".join(genre.name for genre in release.genres[:3])
            print(f"  {release.name.main} ({release.year}) [{genres}]")

        # --- recommended --------------------------------------------------------------
        # With release=..., the API recommends releases similar to that one; without it,
        # general recommendations. (In the runs checked, the release itself was never
        # among its own recommendations.)
        frieren = await client.releases.get("sousou-no-frieren")
        print(f"Similar to {frieren.name.main}:")
        for release in await client.releases.recommended(release=frieren, limit=3):
            print(f"  {release.name.main}")

        # --- limits -------------------------------------------------------------------
        # The SDK doesn't pre-check ranges the API already validates: a bad `limit` reaches
        # the API and comes back as ValidationError, with the API's own messages per
        # parameter (in Russian) in `.errors`.
        try:
            await client.releases.latest(limit=100)
        except ValidationError as error:
            print("limit=100 rejected:", error.errors)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Latest:
#   2026-10-15 22:02 О моём перерождении в меч 2 — episode 3
#   2026-10-15 13:48 Во всеоружии: Сила артефактов — episode 3
#   2026-10-14 17:30 Операция: Семейка Ёдзакура 2. Часть 2 — episode 1
# Random:
#   Ди-сайд: Грёзы (2021) [Экшен, Фэнтези, Приключения]
#   Страж перерождения (2017) [Фэнтези, Приключения, Романтика]
# Similar to Провожающая в последний путь Фрирен:
#   Ди-сайд: Грёзы
#   Волчица и пряности: Торговец встречает мудрую волчицу
#   Жизнь девушки-карателя
# limit=100 rejected: {'limit': ['Поле limit не может быть больше 50.']}
