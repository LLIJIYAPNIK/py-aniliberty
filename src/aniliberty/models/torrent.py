"""Torrent models (spec tag ``Аниме.Торренты``).

Required fields follow ``docs/api-notes.md``: the ones non-null in all 100 torrents checked
(2026-10-16) are required, the rest optional.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from aniliberty.models._base import AniLibertyModel
from aniliberty.models.common import EMPTY_VALUE_AS_NONE, LinkedAccount, ValueDescription
from aniliberty.models.release import Release


class TorrentCodec(ValueDescription[str]):
    """Video codec of a torrent, e.g. ``value="x265/HEVC"``, ``label="HEVC"``.

    ``value`` is one of ``AV1``, ``x264/AVC``, ``x265/HEVC``, ``x265hq/HEVC-HQ`` (spec enum
    ``enums.anime.torrents.torrent.codec``).

    Attributes:
        label: Short label the site shows, e.g. ``"HEVC"``.
        label_color: Color of that label as ``#RRGGBB``, if it has one.
        label_is_visible: Whether the site shows the label.
    """

    label: str | None = None
    label_color: str | None = None
    label_is_visible: bool | None = None


class TorrentMember(AniLibertyModel):
    """A person credited on a torrent (e.g. who encoded the HEVC version).

    Attributes:
        id: Member entry ID (a UUID string).
        nickname: The member's nickname.
        role: What they did; ``role.value`` was ``"HEVC"`` on every torrent checked.
        external_url: The member's own link (e.g. a Telegram channel), if any.
        user: Linked site account, if any.
    """

    id: str
    nickname: str
    role: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    external_url: str | None = None
    user: LinkedAccount | None = None


class Torrent(AniLibertyModel):
    """A torrent of a release.

    Spec schema: ``models.anime.torrents.v1.torrent``.

    Attributes:
        id: Torrent ID.
        hash: Info hash (40 hex characters); ``client.torrents.get()`` accepts it as well as
            the ID, in any letter case.
        label: Full title, e.g. ``"One Piece - AniLiberty.TOP [WEBRip 1080p][AVC][1-24]"``.
        filename: Name of the ``.torrent`` file.
        description: Which episodes it contains, e.g. ``"1-24"``.
        magnet: Magnet link.
        size: Total size of the files the torrent downloads, in bytes (not the size of the
            ``.torrent`` file itself).
        type: Source, e.g. ``"WEB-DL"``, ``"BDRip"`` (spec enum
            ``enums.anime.torrents.torrent.type``).
        quality: Resolution, e.g. ``"1080p"`` (spec enum ``enums.anime.torrents.torrent.quality``).
        codec: Video codec.
        color: Color depth, ``"8bit"`` or ``"10Bit"`` (spec enum
            ``enums.anime.torrents.torrent.color``).
        bitrate: Bitrate in kbit/s — usually ``None``.
        is_hardsub: Whether the subtitles are burned into the video.
        seeders: Number of seeders.
        leechers: Number of leechers.
        completed_times: How many times it was downloaded completely.
        sort_order: Position among the release's torrents.
        created_at: When the torrent was added.
        updated_at: When the torrent was last updated.
        release: The release (without ``genres`` and ``episodes``).
        torrent_members: People credited on the torrent; often empty.
    """

    id: int
    hash: str
    label: str
    filename: str
    description: str
    magnet: str
    size: int
    type: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    quality: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    codec: Annotated[TorrentCodec | None, EMPTY_VALUE_AS_NONE] = None
    color: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    bitrate: int | None = None
    is_hardsub: bool
    seeders: int
    leechers: int
    completed_times: int
    sort_order: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    release: Release | None = None
    torrent_members: list[TorrentMember] = Field(default_factory=list)


class TorrentFile(AniLibertyModel):
    """A downloaded ``.torrent`` file, from ``client.torrents.file()``.

    Attributes:
        filename: The file name the API suggests (from ``Content-Disposition``), if it sent one.
        content: The file's bytes.

    Example:
        ```python
        torrent_file = await client.torrents.file(torrent)
        Path(torrent_file.filename or "release.torrent").write_bytes(torrent_file.content)
        ```
    """

    filename: str | None = None
    content: bytes
