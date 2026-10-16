"""Media: the site's front-page promo banners and AniLibria's YouTube videos.

Promotions are a mix of three kinds — featured releases, the site's own news/links, and paid
ads — told apart by which fields are set. Videos are the latest uploads from the YouTube
playlists AniLibria tracks (trailers, reviews, season announcements), newest first.
"""

import asyncio
from collections import Counter

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        # The API shuffles promotions on every call, so sort them yourself if you need a
        # stable order (here: by title).
        promotions = await client.media.promotions()
        print(f"{len(promotions)} promotions:")
        for promo in sorted(promotions, key=lambda p: p.title or ""):
            # A featured release has .release (a full Release, genres included) and no url;
            # a link or an ad has .url instead; a plain announcement has neither. Paid ads
            # are flagged with is_ad — drop them if you're building your own front page.
            if promo.release:
                kind = f"release {promo.release.alias}"
            elif promo.is_ad:
                kind = f"ad -> {promo.url}"
            elif promo.url:
                kind = f"link -> {promo.url}"
            else:
                # An announcement with just text and an image — nothing to link to.
                kind = "text only"
            print(f"  {promo.title or '(no title)'}: {kind}")

        # Images are relative paths in the API; *_url gives an absolute URL on the host the
        # client talks to (aniliberty.top by default).
        if promotions and promotions[0].image:
            print("Banner image:", promotions[0].image.preview_url)

        # Videos: 10 by default, at most 50 per call (51+ is a ValidationError). Careful:
        # limit=0 or a negative limit returns ALL videos — over a thousand, more than 1 MB.
        videos = await client.media.videos(limit=5)
        print("Latest videos:")
        for video in videos:
            day = video.created_at.date() if video.created_at else "?"
            origin = video.origin.title if video.origin else "?"
            # views/comments are synced from YouTube and can be None for some videos.
            print(f"  {day} [{origin}] {video.title} — {video.views} views")
            print(f"    {video.url}")

        # Season announcements are flagged on the video (and on its playlist).
        recent = await client.media.videos(limit=50)
        announcements = [v for v in recent if v.is_announce]
        print(f"Announcements among the last 50: {len(announcements)}")
        print("Videos per playlist:", Counter(v.origin.title for v in recent if v.origin))


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# 8 promotions:
#   (no title): ad -> https://funpay.com/go/anilib26
#   AniLiberty на YouTube: link -> https://youtube.com/@anilibertytv?si=5VrmzRfJc0GfcS4r
#   AniLiberty — Так звучит аниме!: link -> https://t.me/aniliberty_tv
#   Ван-Пис: release one-piece
#   История о перекуре за супермаркетом: release super-no-ura-de-yani-suu-futari
#   История электричества в двадцатом веке: release nijusseiki-denki-mokuroku-eureka-evrika
#   Необъятный океан 3: release grand-blue-season-3
#   Уважаемые пользователи!: text only
# Banner image: https://aniliberty.top/storage/media/promotions/images/a0b926ae-019a-4ce0-b5ff-e97abc11f503/W5JkXwVwMNzJDdq2OONSMMqpi2wjyiks.jpg
# Latest videos:
#   2026-10-13 [AniLiberty] Аой Ашито 2 — русский трейлер (ОСЕНЬ 2026) — 528 views
#     https://www.youtube.com/watch?v=ZGZIUASKhgo
#   2026-10-08 [AniLiberty] Некий ITEM тёмной стороны — русский трейлер (ОСЕНЬ 2026) — 1403 views
#     https://www.youtube.com/watch?v=aq7EcCD9XAY
#   2026-10-05 [Sharon [AniLibria.TV]] КРИНЖ во время озвучки СЕМЬЯ ШПИНАТА 3 — 45717 views
#     https://www.youtube.com/watch?v=ZXJo4gilNtg
#   2026-10-05 [AniLiberty] Семь рыцарей королевства Марронье — русский трейлер (ОСЕНЬ 2026) — 901 views
#     https://www.youtube.com/watch?v=5J3y_JGadG0
#   2026-10-04 [Sharon [AniLibria.TV]] Я АКТЕР ОЗВУЧКИ ДАНИ В АБДУКЦИИ И МНЕ ЕСТЬ ЧТО РАССКАЗАТЬ — 27751 views
#     https://www.youtube.com/watch?v=LEiriuRPEG8
# Announcements among the last 50: 1
# Videos per playlist: Counter({'AniLiberty': 39, 'Sharon [AniLibria.TV]': 7, 'Ditaro': 2, 'Anilibria.tv': 1, 'Анонсы аниме-сезонов': 1})
