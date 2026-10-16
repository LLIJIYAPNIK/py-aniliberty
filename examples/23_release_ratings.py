"""Release ratings: the user's own 1–10 score of a release.

client.releases.ratings reads, sets and withdraws the logged-in user's score. It is separate
from Release.rating, the overall score of all users: the API recomputes that on its own
schedule (it didn't change within minutes of a vote when this was tested), so don't expect
your vote to show up there right away.

Run it with an account's credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD. A score you
already had for the release is put back at the end.
"""

import asyncio
import os

from aniliberty import AniLiberty


async def main() -> None:
    async with AniLiberty() as client:
        await client.auth.login(
            login=os.environ["ANILIBERTY_LOGIN"], password=os.environ["ANILIBERTY_PASSWORD"]
        )
        ratings = client.releases.ratings
        frieren = await client.releases.get("sousou-no-frieren")

        # get() returns a UserRating; score is None when the user hasn't rated the release.
        before = (await ratings.get(frieren)).score
        try:
            # set() takes a whole number from 1 to 10 and replaces any earlier score.
            print("Set:", (await ratings.set(frieren, score=8)).score)
            print("Changed:", (await ratings.set(frieren, score=10)).score)
            print("Read back:", (await ratings.get(frieren.id)).score)

            # The score is checked before sending.
            for bad in (0, 7.5):
                try:
                    await ratings.set(frieren, score=bad)  # type: ignore[arg-type]
                except (ValueError, TypeError) as error:
                    print(f"score={bad!r}: {type(error).__name__}: {error}")

            # Only numeric IDs (or Release objects) work: the API doesn't route aliases here.
            try:
                await ratings.get("sousou-no-frieren")  # type: ignore[arg-type]
            except TypeError:
                print("An alias is rejected: TypeError")

            # The overall rating is a different thing — average, number of votes and the
            # distribution per score, for all users.
            overall = frieren.rating
            if overall is not None:
                print(f"Overall: average {overall.average}, {overall.votes} votes")
        finally:
            # remove() withdraws the score (a no-op if there's none); restore the old one.
            if before is None:
                print("Removed:", (await ratings.remove(frieren)).score)
            else:
                await ratings.set(frieren, score=before)
            await client.auth.logout()


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Set: 8
# Changed: 10
# Read back: 10
# score=0: ValueError: score must be from 1 to 10, got 0
# score=7.5: TypeError: score must be an int from 1 to 10, got 7.5
# An alias is rejected: TypeError
# Overall: average None, 0 votes
# Removed: None
