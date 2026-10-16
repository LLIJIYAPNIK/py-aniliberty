"""client.media against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Promotion, ValidationError, Video


@pytest.mark.vcr
async def test_promotions() -> None:
    async with AniLiberty() as client:
        promotions = await client.media.promotions()

    assert promotions
    assert all(isinstance(p, Promotion) and p.id for p in promotions)
    featured = [p for p in promotions if p.release is not None]
    assert featured
    assert all(p.release and p.release.alias for p in featured)
    assert all(p.image and p.image.preview_url for p in promotions)


@pytest.mark.vcr
async def test_videos_default_limit_and_order() -> None:
    async with AniLiberty() as client:
        videos = await client.media.videos()

    assert len(videos) == 10
    assert all(isinstance(v, Video) and v.url.startswith("https://") for v in videos)
    dates = [v.created_at for v in videos]
    assert None not in dates
    assert dates == sorted(dates, reverse=True)  # type: ignore[type-var]
    assert all(v.origin and v.origin.type and v.origin.type.value for v in videos)


@pytest.mark.vcr
async def test_videos_with_limit() -> None:
    async with AniLiberty() as client:
        assert len(await client.media.videos(limit=3)) == 3


@pytest.mark.vcr
async def test_videos_limit_over_50_is_rejected() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError):
            await client.media.videos(limit=51)
