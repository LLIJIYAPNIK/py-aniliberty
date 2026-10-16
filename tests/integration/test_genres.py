"""client.genres against recorded live responses."""

from __future__ import annotations

import pytest

from aniliberty import AniLiberty, Genre, NotFoundError, Page, ValidationError

ACTION = 14
MARTIAL_ARTS = 15  # a small genre: few pages to iterate


@pytest.mark.vcr
async def test_list() -> None:
    async with AniLiberty() as client:
        genres = await client.genres.list()

    assert len(genres) > 10
    for genre in genres:
        assert isinstance(genre, Genre)
        assert genre.total_releases is not None
        assert genre.image is not None
        assert genre.image.preview_url is not None
        assert genre.image.preview_url.startswith("https://aniliberty.top/storage/")


@pytest.mark.vcr
async def test_get_by_id_and_by_reference_genre() -> None:
    async with AniLiberty() as client:
        [reference] = [g for g in await client.catalog.references.genres() if g.id == ACTION]
        by_id = await client.genres.get(ACTION)
        by_reference = await client.genres.get(reference)

    assert reference.image is None  # the reference list has no images ...
    assert by_reference.image is not None  # ... get() fetches the full genre
    assert by_id == by_reference
    assert by_id.name == "Экшен"


@pytest.mark.vcr
async def test_get_missing_genre_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.genres.get(999999)


@pytest.mark.vcr
async def test_random() -> None:
    async with AniLiberty() as client:
        genres = await client.genres.random(limit=3)

    assert len(genres) == 3
    assert len({g.id for g in genres}) == 3


@pytest.mark.vcr
async def test_releases_of_a_genre() -> None:
    async with AniLiberty() as client:
        genre = await client.genres.get(ACTION)
        page = await client.genres.releases(ACTION, limit=30)

    assert isinstance(page, Page)
    assert len(page.items) == 30
    assert page.total == genre.total_releases
    assert all(ACTION in {g.id for g in release.genres} for release in page.items)


@pytest.mark.vcr
async def test_releases_limit_above_30_is_rejected() -> None:
    async with AniLiberty() as client:
        with pytest.raises(ValidationError) as excinfo:
            await client.genres.releases(ACTION, limit=31)

    assert "limit" in excinfo.value.errors


@pytest.mark.vcr
async def test_releases_of_missing_genre_raise_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.genres.releases(999999)


@pytest.mark.vcr
async def test_iter_releases_walks_all_pages() -> None:
    async with AniLiberty() as client:
        genre = await client.genres.get(MARTIAL_ARTS)
        ids = [r.id async for r in client.genres.iter_releases(genre, limit=10)]

    assert len(ids) == genre.total_releases
    assert len(set(ids)) == len(ids)
