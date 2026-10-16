"""Catalog references: the values the catalog filters accept.

client.catalog.references returns the same lists the site's catalog filters show. Use them
instead of hardcoding genre IDs or type names — and pass their items straight to
client.catalog.releases(): the SDK takes a reference item wherever it takes a value.
"""

import asyncio

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        refs = client.catalog.references

        # Genres: `id` is the filter value, `name` is for display. This list carries only
        # these two fields (image and release count are None here).
        genres = await refs.genres()
        print(f"{len(genres)} genres, e.g.:", ", ".join(f"{g.id}={g.name}" for g in genres[:5]))

        # Value + description lists: `value` goes to the filter, `description` to people.
        for name, items in (
            ("types", await refs.types()),
            ("seasons", await refs.seasons()),
            ("publish statuses", await refs.publish_statuses()),
            ("production statuses", await refs.production_statuses()),
        ):
            print(f"{name}:", ", ".join(f"{i.value} ({i.description})" for i in items))

        # Age ratings also have a short `label`; sorting options have a `label` and a longer
        # description of what the order means.
        print("age ratings:", ", ".join(f"{r.value}={r.label}" for r in await refs.age_ratings()))
        for option in await refs.sorting():
            print(f"sorting {option.value}: {option.label}")

        # Years: only years that have releases — the range can have gaps.
        years = await refs.years()
        gaps = sorted(set(range(years[0], years[-1] + 1)) - set(years))
        print(f"years {years[0]}..{years[-1]}, missing: {gaps}")

        # Putting it together: pick filter values from the references by what a person
        # would choose, and pass the items themselves.
        romance = next(g for g in genres if g.name == "Романтика")
        winter = next(s for s in await refs.seasons() if s.value == "winter")
        newest = next(o for o in await refs.sorting() if o.value == "YEAR_DESC")
        page = await client.catalog.releases(
            genres=[romance], seasons=[winter], year_to=2015, sorting=newest, limit=3
        )
        print(f"{romance.name}, {winter.description}, up to 2015 — {page.total} releases:")
        for release in page.items:
            print(f"  {release.year} {release.name.main}")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 35 genres, e.g.: 15=Боевые искусства, 24=Вампиры, 32=Гарем, 16=Демоны, 25=Детектив
# types: TV (ТВ), ONA (ОNA), WEB (WEB), OVA (OVA), OAD (OAD), MOVIE (Фильм), DORAMA (Дорама), SPECIAL (Спешл)
# seasons: winter (Зима), spring (Весна), summer (Лето), autumn (Осень)
# publish statuses: IS_ONGOING (Онгоинг), IS_NOT_ONGOING (Неонгоинг)
# production statuses: IS_IN_PRODUCTION (Сейчас в озвучке), IS_NOT_IN_PRODUCTION (Озвучка завершена)
# age ratings: R0_PLUS=0+, R6_PLUS=6+, R12_PLUS=12+, R16_PLUS=16+, R18_PLUS=18+
# sorting FRESH_AT_DESC: Обновлены недавно
# sorting FRESH_AT_ASC: Обновлены давно
# sorting RATING_DESC: Самый высокий рейтинг
# sorting RATING_ASC: Самый низкий рейтинг
# sorting YEAR_DESC: Самые новые
# sorting YEAR_ASC: Самые старые
# years 1995..2026, missing: [1997, 2000, 2002]
# Романтика, Зима, up to 2015 — 15 releases:
#   2015 Абсолютный Дуэт
#   2015 Безграничный Фафнир
#   2015 Как воспитать из обычной девушки героиню
