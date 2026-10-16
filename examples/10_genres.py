"""Genres: the full list with images and counts, one genre, random ones, a genre's releases.

client.genres has richer genre data than the catalog reference list (which only has id and
name): every genre here comes with an image and the number of releases in it.
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # All genres. The API returns them in its own order; sort as you need.
        genres = await client.genres.list()
        biggest = sorted(genres, key=lambda g: g.total_releases or 0, reverse=True)
        print(f"{len(genres)} genres, the biggest:")
        for genre in biggest[:5]:
            print(f"  {genre.id:>2} {genre.name}: {genre.total_releases} releases")

        # Images come as relative paths; the *_url properties give absolute URLs.
        action = next(g for g in genres if g.name == "Экшен")
        if action.image:
            print("Image:", action.image.preview_url)

        # get() accepts an ID or a Genre — e.g. one from the catalog references, which has
        # no image, to fetch its full data.
        [reference] = [g for g in await client.catalog.references.genres() if g.id == action.id]
        full = await client.genres.get(reference)
        print(
            f"Reference genre image: {reference.image}; full genre image: {full.image is not None}"
        )

        # Random genres — a different set on every call.
        print("Random:", [g.name for g in await client.genres.random(limit=3)])

        # Releases of one genre, page by page. Note the page size limit here is 30, not 50
        # as in the catalog. For sorting or combining genres with other filters, use
        # client.catalog.releases(genres=[...]) instead.
        page = await client.genres.releases(action, limit=30)
        print(f"{action.name}: {page.total} releases on {page.total_pages} pages of 30")

        # iter_releases() walks all pages. The smallest genre with more than one page of 30
        # keeps this quick while still showing it.
        genre = min(
            (g for g in genres if (g.total_releases or 0) > 30),
            key=lambda g: g.total_releases or 0,
        )
        titles = [r.name.main async for r in client.genres.iter_releases(genre, limit=30)]
        print(f"{genre.name}: iterated {len(titles)} releases of {genre.total_releases}, e.g.:")
        for title in titles[:3]:
            print(f"  {title}")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 35 genres, the biggest:
#   14 Экшен: 699 releases
#    1 Комедия: 685 releases
#   29 Фэнтези: 629 releases
#   11 Романтика: 481 releases
#   27 Приключения: 462 releases
# Image: https://aniliberty.top/storage/anime/genres/images/14/HVxcEvm7oA6JQvnMKKgSdYJ90ab8Zoco.jpg
# Reference genre image: None; full genre image: True
# Random: ['Повседневность', 'Исекай', 'Сёнен']
# Экшен: 699 releases on 24 pages of 30
# Игры: iterated 42 releases of 42, e.g.:
#   Мастера Меча Онлайн: Безответная бабочка
#   Богиня жаждет игр
#   Мастера Меча Онлайн: Альтернативная «Призрачная пуля» 2
