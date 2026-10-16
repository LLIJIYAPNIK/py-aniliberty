"""client.episodes and episodes inside releases, against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Episode, NotFoundError

RELEASE_ID = 10172
EPISODE_ID = "a159552a-9fa7-4737-867b-d22cf7115602"  # episode 1 of RELEASE_ID


@pytest.mark.vcr
async def test_get_episode() -> None:
    async with AniLiberty() as client:
        episode = await client.episodes.get(EPISODE_ID)

    assert isinstance(episode, Episode)
    assert episode.id == EPISODE_ID
    assert episode.release_id == RELEASE_ID
    assert episode.ordinal == 1
    assert episode.duration > 0
    for playlist in (episode.hls_480, episode.hls_720):
        assert playlist is not None
        assert playlist.startswith("https://")
        assert ".m3u8" in playlist
    assert episode.preview is not None
    assert episode.preview.preview_url is not None
    assert episode.preview.preview_url.startswith("https://aniliberty.top/storage/")
    # The episode endpoint embeds its release with all episodes, but without genres.
    assert episode.release is not None
    assert episode.release.id == RELEASE_ID
    assert EPISODE_ID in {e.id for e in episode.release.episodes}
    assert episode.release.genres == []


@pytest.mark.vcr
@pytest.mark.parametrize(
    "episode_id", ["00000000-0000-0000-0000-000000000000", "not-a-uuid"], ids=["unknown", "bad"]
)
async def test_missing_episode_raises_not_found(episode_id: str) -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.episodes.get(episode_id)


@pytest.mark.vcr
async def test_release_page_lists_its_episodes_in_order() -> None:
    async with AniLiberty() as client:
        release = await client.releases.get(RELEASE_ID)

    assert release.episodes
    assert [e.sort_order for e in release.episodes] == sorted(
        e.sort_order for e in release.episodes
    )
    assert all(e.release_id == RELEASE_ID for e in release.episodes)
    assert release.latest_episode is None  # only latest() fills it in


@pytest.mark.vcr
async def test_latest_releases_carry_their_latest_episode() -> None:
    async with AniLiberty() as client:
        releases = await client.releases.latest(limit=3)

    for release in releases:
        assert release.latest_episode is not None
        assert release.latest_episode.release_id == release.id
        assert release.episodes == []  # latest() doesn't send the full list
