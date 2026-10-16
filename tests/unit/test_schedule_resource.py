"""client.schedule: response shapes, including the spec's {"data": [...]} envelope."""

from __future__ import annotations

from typing import Any

import httpx
import pydantic
import pytest

from aniliberty import AniLiberty, ScheduledRelease

RELEASE: dict[str, Any] = {
    "id": 1,
    "alias": "a",
    "name": {"main": "Название"},
    "publish_day": {"value": 5, "description": "Пятница"},
    "season": {"value": None, "description": None},
    "is_ongoing": True,
    "is_in_production": True,
    "is_blocked_by_geo": False,
    "is_blocked_by_copyrights": False,
    "added_in_users_favorites": 0,
    "added_in_planned_collection": 0,
    "added_in_watched_collection": 0,
    "added_in_watching_collection": 0,
    "added_in_postponed_collection": 0,
    "added_in_abandoned_collection": 0,
}
ITEM = {
    "release": RELEASE,
    "full_season_is_released": False,
    "next_release_episode_number": 15,
    "published_release_episode": None,
}


async def call(payload: Any, method: str) -> Any:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    async with AniLiberty(http_client=http_client) as client:
        result = await getattr(client.schedule, method)()
    await http_client.aclose()
    return result


@pytest.mark.parametrize("payload", [[ITEM], {"data": [ITEM]}], ids=["live", "spec"])
async def test_week_accepts_the_live_list_and_the_spec_envelope(payload: Any) -> None:
    [item] = await call(payload, "week")

    assert isinstance(item, ScheduledRelease)
    assert item.release.season is None  # {"value": null} in the schedule
    assert item.published_release_episode is None
    assert item.next_release_episode_number == 15


async def test_now_with_missing_days_gives_empty_lists() -> None:
    schedule = await call({"today": [ITEM]}, "now")

    assert len(schedule.today) == 1
    assert schedule.yesterday == []
    assert schedule.tomorrow == []


def test_full_season_flag_is_required() -> None:
    data = {k: v for k, v in ITEM.items() if k != "full_season_is_released"}
    with pytest.raises(pydantic.ValidationError, match="full_season_is_released"):
        ScheduledRelease.model_validate(data)
