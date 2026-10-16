"""Episodes: where their IDs come from, HLS playlists, opening/ending timings, previews.

The SDK gives you links to HLS playlists (.m3u8). It doesn't download or convert video —
hand a playlist to a player (mpv, VLC) or to ffmpeg, e.g.:

    ffmpeg -i "<playlist url>" -c copy episode.mp4
"""

import asyncio

from aniliberty import AniLiberty, NotFoundError


async def main() -> None:
    async with AniLiberty() as client:
        # Episode IDs (UUID strings) come from a release: get() and list() include all
        # episodes, latest() includes only `latest_episode`.
        release = await client.releases.get("sousou-no-frieren")
        print(f"{release.name.main}: {len(release.episodes)} episodes")
        first = release.episodes[0]
        print("First episode ID:", first.id)

        # episodes.get() returns the same Episode plus `release` — the release with all
        # its episodes (but without genres, the API doesn't send them here).
        episode = await client.episodes.get(first.id)
        # `ordinal` is the episode number; usually an int, but the spec allows fractions
        # such as 12.5 for recaps, which come as a float.
        print(f"Episode {episode.ordinal}: {episode.name or '(no title)'}")
        print(f"Duration: {episode.duration // 60} min {episode.duration % 60} s")

        # Quality availability varies: 480p and 720p were present on every episode checked,
        # 1080p is missing on some. Pick the best one that exists.
        playlist = episode.hls_1080 or episode.hls_720 or episode.hls_480
        print("Best playlist:", playlist)
        # The links are absolute and include a query string (country, ads flags, ...).
        # Use them exactly as given — the query string is part of the link.

        # Opening/ending timings, in seconds from the start of the episode, for a "skip"
        # button. None when the episode isn't marked up — common, so always check.
        for label, skip in (("Opening", episode.opening), ("Ending", episode.ending)):
            print(f"{label}:", f"{skip.start}-{skip.stop} s" if skip else "not marked")
        # The episodes inside a release carry the same timings, no extra request needed.
        marked = [e for e in release.episodes if e.opening or e.ending]
        print(f"Episodes with marked opening/ending: {len(marked)} of {len(release.episodes)}")
        if marked:
            sample = marked[0]
            print(
                f"  e.g. episode {sample.ordinal}: opening={sample.opening} ending={sample.ending}"
            )

        # Episode still image; often present but with all paths None, so check the URL.
        if episode.preview and episode.preview.preview_url:
            print("Preview:", episode.preview.preview_url)

        # Some episodes are also published on Rutube/YouTube; usually both IDs are None.
        print("Rutube / YouTube:", episode.rutube_id, "/", episode.youtube_id)

        # An unknown (or malformed) ID is a 404 from the API -> NotFoundError.
        try:
            await client.episodes.get("00000000-0000-0000-0000-000000000000")
        except NotFoundError as error:
            print("Unknown episode:", error.status_code, error.message)


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Провожающая в последний путь Фрирен: 28 episodes
# First episode ID: 9a416b99-4487-4d8a-960a-461089d36cad
# Episode 1: «Конец приключений»
# Duration: 26 min 0 s
# Best playlist: https://cache.libria.fun/videos/media/ts/9542/1/1080/aa675e5f3fe5b528517d812182344011.m3u8?countryIso=NL&isAuthorized=0&isWithVideoAds=1&isWithVideoAdsAlways=1
# Opening: not marked
# Ending: not marked
# Episodes with marked opening/ending: 27 of 28
#   e.g. episode 2: opening=start=1 stop=89 ending=None
# Preview: https://aniliberty.top/storage/releases/episodes/previews/9542/1/DMzcnlKyg89dRv5f.jpg
# Rutube / YouTube: None / None
# Unknown episode: 404 Not found
