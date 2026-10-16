"""ValueDescription, EMPTY_VALUE_AS_NONE, Image/ImageSet URL resolution, LinkedAccount."""

from __future__ import annotations

from typing import Annotated, Any

import pydantic
import pytest

from aniliberty import (
    HttpClient,
    Image,
    LinkedAccount,
    ReleaseMember,
    TeamMember,
    TorrentMember,
    ValueDescription,
)
from aniliberty.models import EMPTY_VALUE_AS_NONE
from aniliberty.models._base import AniLibertyModel

# Shapes copied from live responses (docs/api-notes.md, "Image and video URLs").
POSTER = {
    "src": "/storage/releases/posters/10297/Bcvffb9gHRoFRFhSD5SxAW7Ls3Ru5GjI.jpg",
    "preview": "/storage/releases/posters/10297/Bcvffb9gHRoFRFhSD5SxAW7Ls3Ru5GjI.jpg",
    "thumbnail": "/storage/releases/posters/10297/Le7zWNDpiKn5Srpx1xW3SF0cQyuRZ0j1.jpg",
    "optimized": {
        "src": "/storage/releases/posters/10297/h059GsXAePn1jZDjqH7Ngjt858c1kjKM.webp",
        "preview": "/storage/releases/posters/10297/h059GsXAePn1jZDjqH7Ngjt858c1kjKM.webp",
        "thumbnail": "/storage/releases/posters/10297/xFJRGAPhAA7BGTldYxNIAQ80fK6KZCd9.webp",
    },
}
EMPTY_AVATAR = {
    "preview": None,
    "thumbnail": None,
    "optimized": {"preview": None, "thumbnail": None},
}


class Release(AniLibertyModel):
    type: ValueDescription[str]
    publish_day: ValueDescription[int]
    season: Annotated[ValueDescription[str] | None, EMPTY_VALUE_AS_NONE] = None
    poster: Image


def validate(data: dict[str, Any], **context: str) -> Release:
    return pydantic.TypeAdapter(Release).validate_python(data, context=context or None)


RELEASE = {
    "type": {"value": "TV", "description": "ТВ"},
    "publish_day": {"value": 5, "description": "Пятница"},
    "season": {"value": "autumn", "description": "Осень"},
    "poster": POSTER,
}


def test_value_description_keeps_value_type() -> None:
    release = validate(RELEASE)

    assert release.type == ValueDescription[str](value="TV", description="ТВ")
    assert release.publish_day.value == 5
    assert release.season is not None
    assert release.season.description == "Осень"


@pytest.mark.parametrize("season", [{"value": None, "description": None}, None, {"value": None}])
def test_empty_value_description_becomes_none(season: object) -> None:
    assert validate({**RELEASE, "season": season}).season is None


def test_value_description_without_description() -> None:
    assert ValueDescription[str].model_validate({"value": "TV"}).description is None


def test_image_urls_resolve_against_the_default_site() -> None:
    poster = validate(RELEASE).poster

    assert poster.src == POSTER["src"]  # the raw path stays available
    assert poster.src_url == f"https://aniliberty.top{POSTER['src']}"
    assert poster.preview_url == f"https://aniliberty.top{POSTER['preview']}"
    assert poster.thumbnail_url == f"https://aniliberty.top{POSTER['thumbnail']}"
    assert poster.optimized is not None
    assert poster.optimized.preview_url is not None
    assert poster.optimized.preview_url.endswith(".webp")


def test_image_urls_resolve_against_the_site_url_from_context() -> None:
    poster = validate(RELEASE, site_url="https://anilibria.top").poster

    assert poster.preview_url == f"https://anilibria.top{POSTER['preview']}"
    assert poster.optimized is not None
    assert poster.optimized.thumbnail_url == (
        f"https://anilibria.top{POSTER['optimized']['thumbnail']}"  # type: ignore[index]
    )


def test_image_with_all_paths_null() -> None:
    avatar = Image.model_validate(EMPTY_AVATAR)

    assert avatar.preview is None
    assert avatar.preview_url is None
    assert avatar.src_url is None
    assert avatar.optimized is not None
    assert avatar.optimized.thumbnail_url is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("https://cdn.example/a.jpg", "https://cdn.example/a.jpg"),
        ("http://cdn.example/a.jpg", "http://cdn.example/a.jpg"),
        ("//cdn.example/a.jpg", "https://cdn.example/a.jpg"),
        ("storage/a.jpg", "https://aniliberty.top/storage/a.jpg"),
        ("", None),
    ],
)
def test_image_url_forms(path: str, expected: str | None) -> None:
    assert Image(preview=path).preview_url == expected


def test_context_without_site_url_keeps_the_default() -> None:
    image = pydantic.TypeAdapter(Image).validate_python({"preview": "/a.jpg"}, context={"x": 1})
    assert image.preview_url == "https://aniliberty.top/a.jpg"


def test_models_are_frozen() -> None:
    poster = Image.model_validate(POSTER)
    with pytest.raises(pydantic.ValidationError, match="frozen"):
        poster.preview = "/other.jpg"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("base_url", "site_url"),
    [
        ("https://aniliberty.top/api/v1", "https://aniliberty.top"),
        ("https://anilibria.top/api/v1/", "https://anilibria.top"),
        ("http://localhost:8080/api/v1", "http://localhost:8080"),
    ],
)
def test_http_client_site_url_is_the_origin_of_base_url(base_url: str, site_url: str) -> None:
    assert HttpClient(base_url=base_url).site_url == site_url


def test_members_of_releases_torrents_and_teams_share_the_linked_account_model() -> None:
    user = {"id": 7, "avatar": {"preview": "/storage/users/avatars/7/a.jpg"}}
    release_member = ReleaseMember.model_validate({"id": "m1", "nickname": "Amikiri", "user": user})
    torrent_member = TorrentMember.model_validate({"id": "m2", "nickname": "Amikiri", "user": user})
    team_member = TeamMember.model_validate(
        {
            "id": "m3",
            "nickname": "Amikiri",
            "sort_order": 1,
            "team": {"id": "t", "title": "II Лига", "sort_order": 2},
            "user": {**user, "nickname": "amikiri-site"},
        }
    )

    accounts = [release_member.user, torrent_member.user, team_member.user]
    assert all(isinstance(account, LinkedAccount) for account in accounts)
    assert release_member.user is not None and release_member.user.nickname is None
    assert team_member.user is not None and team_member.user.nickname == "amikiri-site"
    assert release_member.user.avatar is not None
    assert release_member.user.avatar.preview_url == (
        "https://aniliberty.top/storage/users/avatars/7/a.jpg"
    )
