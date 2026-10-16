"""Everything about one release: names, value + description fields, ratings, images, team.

Also shows fetching several releases at once with releases.list() / iter_list().
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # get() accepts the numeric ID or the alias; both return the same release. The
        # release page is the richest response: genres, members, sponsors, episodes and
        # background covers are all filled in.
        release = await client.releases.get("sousou-no-frieren")

        print(f"[{release.id}] {release.alias}")
        print("Names:", release.name.main, "|", release.name.english)
        # `alternative` is often None — most releases have no alternative titles.
        print("Alternative:", release.name.alternative)

        # Enumerations are ValueDescription objects: compare `.value` in code, show
        # `.description` to people. Any of them can be None, so guard before using.
        if release.type and release.season and release.publish_day:
            print("Type:", release.type.value, "/", release.type.description)
            print("Season:", release.season.value, "/", release.season.description)
            # publish_day.value is a weekday number, 1 = Monday ... 7 = Sunday.
            print("Publish day:", release.publish_day.value, "/", release.publish_day.description)
        if release.age_rating:
            # AgeRating adds `label` ("16+") and `is_adult` to value + description.
            print("Age rating:", release.age_rating.value, release.age_rating.label)

        # Three different scores: AniLibria users' own, plus Shikimori and MyAnimeList.
        # All of them may be None/empty for new or obscure releases.
        if release.rating:
            print(f"AniLibria: {release.rating.average} from {release.rating.votes} votes")
        for site, external in (("Shikimori", release.shikimori), ("MAL", release.mal)):
            if external and external.rating is not None:
                print(f"{site}: {external.rating} ({external.votes} votes) {external.url}")

        # The API sends relative image paths; `*_url` properties turn them into absolute
        # URLs on the host the client talks to. The raw path stays in `preview`.
        if release.poster:
            print("Poster path:", release.poster.preview)
            print("Poster URL: ", release.poster.preview_url)
            if release.poster.optimized:
                print("WebP:       ", release.poster.optimized.preview_url)

        # Members are the people who worked on the release (voicing, timing, ...). They're
        # included in get(); releases.members() fetches them alone.
        members = await client.releases.members(release.id)
        by_role: dict[str, list[str]] = {}
        for member in members:
            role = member.role.description if member.role else "?"
            by_role.setdefault(role or "?", []).append(member.nickname)
        for role, nicknames in sorted(by_role.items()):
            print(f"{role}: {', '.join(nicknames)}")

        # Several releases at once, by IDs and/or aliases. list() returns one Page;
        # iter_list() walks all pages for you. Note: the API returns them in its own order,
        # not in the order you asked for, and a release requested twice comes back once.
        page = await client.releases.list(ids=[10172, 10297], aliases=["sousou-no-frieren"])
        print(f"list(): {page.total} releases, page {page.page} of {page.total_pages}")
        # A tiny page size just to make iter_list() fetch more than one page here; in real
        # code use up to 50 to make fewer requests.
        async for item in client.releases.iter_list(ids=[10172, 10297, 9542], limit=2):
            print("  iter_list():", item.id, item.name.main)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# [9542] sousou-no-frieren
# Names: Провожающая в последний путь Фрирен | Sousou no Frieren
# Alternative: None
# Type: TV / ТВ
# Season: autumn / Осень
# Publish day: 6 / Суббота
# Age rating: R16_PLUS 16+
# AniLibria: None from 0 votes
# Shikimori: 8.84 (71529 votes) https://shikimori.io/animes/52991
# MAL: 9.24 (943319 votes) https://myanimelist.net/anime/52991
# Poster path: /storage/releases/posters/9542/PaDTDJMU3ybqwWr5BRXydhSM8qbwIhBd.jpg
# Poster URL:  https://aniliberty.top/storage/releases/posters/9542/PaDTDJMU3ybqwWr5BRXydhSM8qbwIhBd.jpg
# WebP:        https://aniliberty.top/storage/releases/posters/9542/8UGD4dHHp1kdjquBph2CUSk9pLNsGtYw.webp
# Озвучка: Amikiri, Hekomi, Anzen, Arato
# Оформление: Neri
# Работа со звуком: im4x
# list(): 3 releases, page 1 of 1
#   iter_list(): 9542 Провожающая в последний путь Фрирен
#   iter_list(): 10172 Невероятные приключения ДжоДжо: Гонка «Стальной шар»
#   iter_list(): 10297 О моём перерождении в меч 2
