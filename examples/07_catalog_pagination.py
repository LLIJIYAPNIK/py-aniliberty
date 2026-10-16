"""Pages: Page from releases() versus iterating with iter_releases().

releases() returns one Page — you decide which pages to fetch. iter_releases() walks all pages
for you, lazily: the next page is requested only when the loop gets to it. A small logging
handler below counts the HTTP requests, to show what each approach actually costs.
"""

import asyncio
import logging

from aniliberty import AniLiberty, Page, Release


class RequestCounter(logging.Handler):
    """Counts the SDK's "GET <url> -> <status>" debug messages, i.e. HTTP requests made."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        if " -> " in record.getMessage():
            self.count += 1


async def main() -> None:
    # The SDK logs every request to the "aniliberty" logger at DEBUG level.
    counter = RequestCounter()
    logger = logging.getLogger("aniliberty")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(counter)

    async with AniLiberty() as client:
        # All examples below use the same selection: movies released up to 2015, oldest
        # first. Old years don't change, so the numbers in the output stay stable.
        async def old_movies(page: int = 1) -> Page[Release]:
            return await client.catalog.releases(
                types=["MOVIE"], year_to=2015, sorting="YEAR_ASC", page=page, limit=10
            )

        # --- One page ------------------------------------------------------------------
        page = await old_movies()
        print(f"Page {page.page} of {page.total_pages}: {len(page.items)} of {page.total} movies")
        print("has_next_page:", page.has_next_page)

        # --- Walking pages by hand -----------------------------------------------------
        # Useful when you need the page boundaries: a UI, progress, resuming later.
        counter.count = 0
        number, seen = 1, 0
        while True:
            page = await old_movies(number)
            seen += len(page.items)
            if not page.has_next_page:
                break
            number += 1
        print(f"By hand: {seen} movies in {counter.count} requests")

        # --- iter_releases -------------------------------------------------------------
        # Same result, no bookkeeping. `limit` only decides how many requests it takes,
        # not what you get — so use the maximum, 50.
        for limit in (10, 50):
            counter.count = 0
            movies = [
                release
                async for release in client.catalog.iter_releases(
                    types=["MOVIE"], year_to=2015, sorting="YEAR_ASC", limit=limit
                )
            ]
            print(f"iter_releases(limit={limit}): {len(movies)} movies in {counter.count} requests")

        # Breaking out early stops the requests: the 3 oldest releases of the whole catalog
        # (about two thousand) cost a single request.
        counter.count = 0
        oldest = []
        async for release in client.catalog.iter_releases(sorting="YEAR_ASC", limit=50):
            oldest.append(release)
            if len(oldest) == 3:
                break
        print(f"3 oldest in {counter.count} request:", [f"{r.year} {r.name.main}" for r in oldest])

        # --- Pages concurrently ----------------------------------------------------------
        # iter_releases() is sequential. To get everything fast, read total_pages from the
        # first page and fetch the rest together. The client still keeps at most
        # max_concurrency (5) requests in flight, so this is safe even for many pages.
        counter.count = 0
        first = await old_movies()
        rest = await asyncio.gather(*(old_movies(n) for n in range(2, first.total_pages + 1)))
        movies = first.items + [release for page in rest for release in page.items]
        unique = len({movie.id for movie in movies})
        print(f"Concurrently: {len(movies)} movies ({unique} unique) in {counter.count} requests")

        # A page past the end is simply empty — not an exception.
        empty = await old_movies(1000)
        print("Page 1000:", empty.items, "has_next_page:", empty.has_next_page)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Page 1 of 4: 10 of 37 movies
# has_next_page: True
# By hand: 37 movies in 4 requests
# iter_releases(limit=10): 37 movies in 4 requests
# iter_releases(limit=50): 37 movies in 1 requests
# 3 oldest in 1 request: ['1995 Кошки-Оружейницы', '1995 Призрак в Доспехах (1995)', '1996 Легенда об Ангеле']
# Concurrently: 37 movies (37 unique) in 4 requests
# Page 1000: [] has_next_page: False
