"""client.torrents against recorded live responses (including the binary .torrent file)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aniliberty import AniLiberty, NotFoundError, Page, Torrent

FRIEREN = "sousou-no-frieren"


@pytest.mark.vcr
async def test_list() -> None:
    async with AniLiberty() as client:
        page = await client.torrents.list(limit=5)

    assert isinstance(page, Page)
    assert len(page.items) == 5
    assert page.total > 1000
    for torrent in page.items:
        assert isinstance(torrent, Torrent)
        assert len(torrent.hash) == 40
        assert torrent.magnet.startswith("magnet:?")
        assert torrent.release is not None


@pytest.mark.vcr
async def test_get_by_id_and_by_hash_in_any_case() -> None:
    async with AniLiberty() as client:
        [listed] = (await client.torrents.list(limit=1)).items
        by_id = await client.torrents.get(listed.id)
        by_hash = await client.torrents.get(listed.hash.upper())

    assert by_id.id == by_hash.id == listed.id
    assert by_id.hash == listed.hash


@pytest.mark.vcr
async def test_get_missing_torrent_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.torrents.get(999999999)


@pytest.mark.vcr
async def test_for_release() -> None:
    async with AniLiberty() as client:
        release = await client.releases.get(FRIEREN)
        torrents = await client.torrents.for_release(release)

    assert torrents
    assert all(t.release is not None and t.release.id == release.id for t in torrents)
    assert {t.codec.value for t in torrents if t.codec} <= {"x264/AVC", "x265/HEVC"}


@pytest.mark.vcr
async def test_for_missing_release_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.torrents.for_release(999999999)


@pytest.mark.vcr
async def test_file_and_download(tmp_path: Path) -> None:
    async with AniLiberty() as client:
        release = await client.releases.get(FRIEREN)
        [torrent, *_] = await client.torrents.for_release(release)
        in_memory = await client.torrents.file(torrent)
        saved = await client.torrents.download(torrent, tmp_path)

    assert in_memory.content.startswith(b"d8:announce")  # a bencoded dictionary
    assert in_memory.filename is not None
    assert in_memory.filename.endswith(".torrent")
    assert saved == tmp_path / in_memory.filename
    assert saved.read_bytes() == in_memory.content


@pytest.mark.vcr
async def test_file_of_missing_torrent_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.torrents.file(999999999)


@pytest.mark.vcr
async def test_rss() -> None:
    async with AniLiberty() as client:
        latest = await client.torrents.rss(limit=3)
        release = await client.releases.get(FRIEREN)
        of_release = await client.torrents.rss_for_release(release)

    assert latest.lstrip().startswith("<?xml")
    assert latest.count("<item>") == 3
    assert of_release.count("<item>") >= 1
    assert f"<releaseId>{release.id}</releaseId>" in of_release


@pytest.mark.vcr
async def test_rss_of_missing_release_raises_not_found() -> None:
    async with AniLiberty() as client:
        with pytest.raises(NotFoundError):
            await client.torrents.rss_for_release(999999999)
