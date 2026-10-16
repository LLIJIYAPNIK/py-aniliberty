"""client.media: response envelopes, query parameters and models on edge-case JSON."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from aniliberty import AniLiberty, Promotion, Video

VIDEO: dict[str, Any] = {
    "id": 57,
    "url": "https://www.youtube.com/watch?v=8f6FpV4sB0I",
    "title": "ТОП 10",
    "video_id": "8f6FpV4sB0I",
    "views": None,
    "comments": None,
    "image": {"preview": None, "thumbnail": None, "optimized": {"preview": None}},
    "created_at": "2021-09-22T16:20:38+00:00",
    "updated_at": "2021-09-28T19:40:26+00:00",
    "is_announce": True,
    "origin": {
        "id": "e8fd32be",
        "url": "https://www.youtube.com/playlist?list=PL8",
        "type": {"value": "YOUTUBE_PLAYLIST", "description": "Youtube плейлист"},
        "title": "Анонсы аниме-сезонов",
        "description": "Плейлист с анонсами",
        "is_announce": True,
    },
}
AD: dict[str, Any] = {
    "id": "a0b926ae",
    "url": "https://example.com/go",
    "title": None,
    "description": None,
    "url_label": "Залетай!",
    "image": {"preview": "/storage/media/promotions/images/a.jpg"},
    "is_ad": True,
    "has_overlay": False,
    "ad_erid": None,
    "ad_origin": None,
    "release": None,
}


def test_video_without_counts_and_preview() -> None:
    video = Video.model_validate(VIDEO)

    assert video.views is None
    assert video.comments is None
    assert video.image is not None
    assert video.image.preview_url is None
    assert video.origin is not None
    assert video.origin.type is not None
    assert video.origin.type.value == "YOUTUBE_PLAYLIST"


def test_ad_promotion_without_release() -> None:
    promo = Promotion.model_validate(AD)

    assert promo.is_ad
    assert promo.release is None
    assert promo.title is None


async def requested(method: str, payload: Any, **kwargs: Any) -> tuple[httpx.Request, Any]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=payload)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        result = await getattr(client.media, method)(**kwargs)
    await http_client.aclose()
    return seen[0], result


@pytest.mark.parametrize("envelope", [False, True], ids=["bare-list", "data-envelope"])
async def test_promotions_accepts_both_response_shapes(envelope: bool) -> None:
    payload = {"data": [AD]} if envelope else [AD]
    request, result = await requested("promotions", payload)

    assert request.url.path == "/api/v1/media/promotions"
    assert [p.id for p in result] == [AD["id"]]


@pytest.mark.parametrize("envelope", [False, True], ids=["bare-list", "data-envelope"])
async def test_videos_accepts_both_response_shapes(envelope: bool) -> None:
    payload = {"data": [VIDEO]} if envelope else [VIDEO]
    _, result = await requested("videos", payload)

    assert [v.id for v in result] == [VIDEO["id"]]


async def test_videos_sends_limit_only_when_given() -> None:
    request, _ = await requested("videos", [])
    assert "limit" not in request.url.params

    request, _ = await requested("videos", [], limit=5)
    assert request.url.path == "/api/v1/media/videos"
    assert request.url.params["limit"] == "5"
