"""client.torrents: arguments, file names, downloads to disk and the RSS calls."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, NotFoundError, Torrent

TORRENT_BYTES = b"d8:announce35:http://tracker.example/announce4:infod4:name3:abcee"
TORRENT: dict[str, Any] = {
    "id": 40407,
    "hash": "17ceda4b3c2b8823b7f1139dca0b49aea5fff933",
    "label": "One Piece - AniLiberty.TOP [WEBRip 1080p][AVC][1-24]",
    "filename": "One Piece.torrent",
    "description": "1-24",
    "magnet": "magnet:?xt=urn:btih:17ceda4b",
    "size": 40535930212,
    "type": {"value": "WEBRip", "description": "WEBRip"},
    "quality": {"value": "1080p", "description": "1080p"},
    "codec": {
        "value": "x264/AVC",
        "label": "AVC",
        "description": "x264/AVC",
        "label_color": None,
        "label_is_visible": False,
    },
    "color": {"value": "8bit", "description": "8bit"},
    "bitrate": None,
    "is_hardsub": False,
    "seeders": 234,
    "leechers": 58,
    "completed_times": 13538,
    "sort_order": 0,
    "torrent_members": [
        {
            "id": "a2e023f6-3e65-4af5-94aa-8ec15395d034",
            "role": {"value": "HEVC", "description": "HEVC"},
            "nickname": "Tuxoid",
            "external_url": None,
            "user": None,
        }
    ],
}


def test_torrent_model() -> None:
    torrent = Torrent.model_validate(TORRENT)

    assert torrent.codec is not None
    assert torrent.codec.label == "AVC"
    assert torrent.bitrate is None
    assert torrent.release is None
    assert torrent.torrent_members[0].role is not None
    assert torrent.torrent_members[0].role.value == "HEVC"


Handler = Callable[[httpx.Request], httpx.Response]


def client_for(handler: Handler) -> tuple[AniLiberty, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(recording))
    return AniLiberty(http_client=http_client), seen


def torrent_file(
    disposition: str | None = 'attachment; filename="One Piece [AVC].torrent"',
) -> Handler:
    headers = {"Content-Type": "application/x-bittorrent"}
    if disposition is not None:
        headers["Content-Disposition"] = disposition
    return lambda request: httpx.Response(200, content=TORRENT_BYTES, headers=headers)


@pytest.mark.parametrize(
    ("disposition", "expected"),
    [
        ('attachment; filename="One Piece [AVC].torrent"', "One Piece [AVC].torrent"),
        (
            "attachment; filename*=UTF-8''%D0%A4%D1%80%D0%B8%D1%80%D0%B5%D0%BD.torrent",
            "Фрирен.torrent",
        ),
        ('attachment; filename="../../etc/passwd"', "_.._etc_passwd"),
        ('attachment; filename="a:b*c?.torrent"', "a_b_c_.torrent"),
        ('attachment; filename=" . "', None),
        ("attachment", None),
        (None, None),
    ],
)
async def test_file_returns_bytes_and_a_safe_suggested_name(
    disposition: str | None, expected: str | None
) -> None:
    client, _ = client_for(torrent_file(disposition))
    async with client:
        result = await client.torrents.file(40407)

    assert result.content == TORRENT_BYTES
    assert result.filename == expected


async def test_download_into_a_directory_uses_the_suggested_name(tmp_path: Path) -> None:
    client, seen = client_for(torrent_file())
    async with client:
        saved = await client.torrents.download(Torrent.model_validate(TORRENT), tmp_path)

    assert saved == tmp_path / "One Piece [AVC].torrent"
    assert saved.read_bytes() == TORRENT_BYTES
    assert seen[0].url.path == "/api/v1/anime/torrents/40407/file"
    assert list(tmp_path.iterdir()) == [saved]  # no .part file left behind


async def test_download_into_a_directory_without_a_suggested_name(tmp_path: Path) -> None:
    client, _ = client_for(torrent_file(None))
    async with client:
        saved = await client.torrents.download("17ceda4b3c2b8823b7f1139dca0b49aea5fff933", tmp_path)

    assert saved.name == "17ceda4b3c2b8823b7f1139dca0b49aea5fff933.torrent"


async def test_download_to_a_file_path_overwrites_it(tmp_path: Path) -> None:
    target = tmp_path / "mine.torrent"
    target.write_bytes(b"old")
    client, _ = client_for(torrent_file())
    async with client:
        saved = await client.torrents.download(40407, str(target))

    assert saved == target
    assert target.read_bytes() == TORRENT_BYTES


class BrokenStream(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield TORRENT_BYTES[:10]
        raise httpx.ReadError("connection reset")


async def test_interrupted_download_leaves_no_files(tmp_path: Path) -> None:
    target = tmp_path / "x.torrent"
    client, _ = client_for(
        lambda request: httpx.Response(
            200, stream=BrokenStream(), headers={"Content-Type": "application/x-bittorrent"}
        )
    )
    async with client:
        with pytest.raises(httpx.ReadError):
            await client.torrents.download(40407, target)

    assert list(tmp_path.iterdir()) == []


async def test_download_of_a_missing_torrent_writes_nothing(tmp_path: Path) -> None:
    client, _ = client_for(lambda request: httpx.Response(404, json={"message": "No query"}))
    async with client:
        with pytest.raises(NotFoundError):
            await client.torrents.download(1, tmp_path)

    assert list(tmp_path.iterdir()) == []


async def test_rss_sends_limit_only_when_given() -> None:
    xml = '<?xml version="1.0"?><rss><channel></channel></rss>'
    client, seen = client_for(
        lambda request: httpx.Response(200, text=xml, headers={"Content-Type": "application/xml"})
    )
    async with client:
        assert await client.torrents.rss() == xml
        await client.torrents.rss(limit=3)
        await client.torrents.rss_for_release(9542)

    assert seen[0].url.query == b""
    assert seen[1].url.params["limit"] == "3"
    assert seen[2].url.path == "/api/v1/anime/torrents/rss/release/9542"


@pytest.mark.parametrize("bad", ["sousou-no-frieren", "9542", True, None])
async def test_release_methods_reject_aliases(bad: Any) -> None:
    async with AniLiberty() as client:
        with pytest.raises(TypeError, match="aliases don't work here"):
            await client.torrents.for_release(bad)
        with pytest.raises(TypeError, match="aliases don't work here"):
            await client.torrents.rss_for_release(bad)


@pytest.mark.parametrize(
    ("bad", "error"), [(None, TypeError), (1.5, TypeError), ("a/b", ValueError)]
)
async def test_torrent_methods_reject_invalid_keys(bad: Any, error: type[Exception]) -> None:
    async with AniLiberty() as client:
        for call in (client.torrents.get, client.torrents.file):
            with pytest.raises(error):
                await call(bad)


async def test_iter_list_walks_all_pages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        ids = [1, 2] if page == 1 else [3]
        return httpx.Response(
            200,
            json={
                "data": [{**TORRENT, "id": i} for i in ids],
                "meta": {
                    "pagination": {
                        "total": 3,
                        "per_page": 2,
                        "current_page": page,
                        "total_pages": 2,
                    }
                },
            },
        )

    client, seen = client_for(handler)
    async with client:
        ids = [t.id async for t in client.torrents.iter_list(limit=2)]

    assert ids == [1, 2, 3]
    assert [r.url.params["page"] for r in seen] == ["1", "2"]
