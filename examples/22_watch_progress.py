"""Watch progress: saving timecodes, reading them back, the history — and the API's delay.

A timecode is where the user stopped in an episode plus whether they finished it. Players
save it every so often and read it back to offer "continue watching".

The catch, found by trying (docs/api-notes.md): the API stores timecodes in two steps.
client.me.views.timecodes() has a saved timecode at once, but the stored records behind
history(), client.episodes.timecode() and client.releases.timecodes() appear only about a
minute later; deletions lag the same way. This script waits for that, so it runs for a
few minutes.

Run it with an account's credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD. Timecodes you
already had for the two episodes it uses are put back at the end.
"""

import asyncio
import os
import time
from collections.abc import Awaitable, Callable

from aniliberty import AniLiberty, NotFoundError, Timecode


async def wait_for(check: Callable[[], Awaitable[bool]], *, timeout: float = 300) -> float:
    """Poll check() every 10 s until it's true; return the seconds it took."""
    started = time.monotonic()
    while not await check():
        if time.monotonic() - started > timeout:
            raise TimeoutError("the API didn't catch up in time")
        await asyncio.sleep(10)
    return time.monotonic() - started


async def main() -> None:
    async with AniLiberty() as client:
        await client.auth.login(
            login=os.environ["ANILIBERTY_LOGIN"], password=os.environ["ANILIBERTY_PASSWORD"]
        )
        views = client.me.views
        frieren = await client.releases.get("sousou-no-frieren")
        first, second = frieren.episodes[0], frieren.episodes[1]
        ours = {first.id, second.id}
        before = [t for t in await views.timecodes() if t.release_episode_id in ours]

        async def stored(episode_id: str) -> bool:
            try:
                await client.episodes.timecode(episode_id)
            except NotFoundError:
                return False
            return True

        try:
            # Save: episode 1 stopped at 12:23.5, episode 2 finished. time is in seconds from
            # the start of the episode (fractions are kept). save_timecodes() replaces what
            # was saved for those episodes.
            await views.save_timecodes(
                Timecode(release_episode_id=first.id, time=743.5),
                Timecode(release_episode_id=second.id, time=second.duration, is_watched=True),
            )

            # The quick list has them immediately...
            quick = {t.release_episode_id: t for t in await views.timecodes()}
            print("In timecodes() at once:", ours <= set(quick))
            print(f"Episode 1 at {quick[first.id].time} s, watched: {quick[first.id].is_watched}")

            # ... the stored record doesn't yet.
            print("Stored record right away:", await stored(first.id))
            seconds = await wait_for(lambda: stored(first.id))
            print(f"Stored record after waiting: True (within {int(seconds // 60) + 1} min)")

            # Per release: which episodes are done, where to continue.
            records = await client.releases.timecodes(frieren.id)
            watched = {record.release_episode_id for record in records if record.is_watched}
            next_up = next(episode for episode in frieren.episodes if episode.id not in watched)
            print(
                f"Watched episodes of Frieren: {len(watched)}, next up: episode {next_up.ordinal}"
            )

            # The history: one entry per episode, most recently saved first, each with its
            # episode and the episode's release.
            entry = (await views.history(limit=1)).items[0]
            episode = entry.release_episode
            assert episode is not None and episode.release is not None
            print(f"Last in history: {episode.release.name.main}, episode {episode.ordinal}")
        finally:
            # Clean up. A deletion takes about a minute to reach the stored records, and the
            # quick list keeps showing deleted timecodes until it's deleted once more after
            # that — hence the second round.
            new = ours - {t.release_episode_id for t in before}
            if new:
                await views.delete_timecodes(*new)
                await wait_for(lambda: _gone(client, new))
                await views.delete_timecodes(*new)
            if before:
                await views.save_timecodes(*before)
            left = {t.release_episode_id for t in await views.timecodes()} & ours
            print("Cleaned up:", left == {t.release_episode_id for t in before})
            await client.auth.logout()


async def _gone(client: AniLiberty, episode_ids: set[str]) -> bool:
    page = await client.me.views.history(limit=50)
    return not {entry.release_episode_id for entry in page.items} & episode_ids


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# In timecodes() at once: True
# Episode 1 at 743.5 s, watched: False
# Stored record right away: False
# Stored record after waiting: True (within 1 min)
# Watched episodes of Frieren: 1, next up: episode 1
# Last in history: Провожающая в последний путь Фрирен, episode 1
# Cleaned up: True
