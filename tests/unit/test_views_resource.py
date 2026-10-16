"""client.me.views, client.episodes.timecode(), client.releases.timecodes()."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import httpx
import pydantic
import pytest

from aniliberty import AniLiberty, Episode, EpisodeView, HistoryEntry, Timecode

VIEWS = "/api/v1/accounts/users/me/views"
E1 = "9de3db5c-5d36-4fc7-909a-ca0d613bd17c"
E2 = "9df201c3-7f9b-4ceb-9cc1-d62fad18d71e"
VIEW = {
    "id": 253284725,
    "time": 743.5,
    "user_id": 799331,
    "is_watched": False,
    "updated_at": "2026-10-16T17:30:02+00:00",
    "release_episode_id": E1,
}
RELEASE = {
    "id": 9839,
    "alias": "r9839",
    "name": {"main": "Релиз"},
    "is_ongoing": False,
    "is_in_production": False,
    "is_blocked_by_geo": False,
    "is_blocked_by_copyrights": False,
    "added_in_users_favorites": 10,
    "added_in_planned_collection": 1,
    "added_in_watched_collection": 2,
    "added_in_watching_collection": 3,
    "added_in_postponed_collection": 4,
    "added_in_abandoned_collection": 5,
}
EPISODE = {"id": E1, "release_id": 9839, "ordinal": 1, "sort_order": 1, "duration": 1420}


class FakeApi:
    def __init__(self, body: Any = None, respond: Any = None) -> None:
        self.requests: list[httpx.Request] = []
        self.respond = respond or (lambda request: httpx.Response(200, json=body))

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response: httpx.Response = self.respond(request)
        return response


async def call(api: FakeApi, method: str, *args: Any, **kwargs: Any) -> Any:
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        target: Any = client
        for name in method.split("."):
            target = getattr(target, name)
        result = await target(*args, **kwargs)
    await http_client.aclose()
    return result


def empty_html(request: httpx.Request) -> httpx.Response:
    # Saving and deleting timecodes answer 200 with an empty text/html body.
    return httpx.Response(200, text="", headers={"Content-Type": "text/html; charset=UTF-8"})


# --- models ---------------------------------------------------------------------------------


def test_timecode_is_validated_from_the_api_triple_or_a_dict() -> None:
    from_triple = Timecode.model_validate([E1, 743.5, False])
    from_dict = Timecode.model_validate({"release_episode_id": E1, "time": 743.5})

    assert from_triple == from_dict == Timecode(release_episode_id=E1, time=743.5)
    assert Timecode.model_validate([E2, 12, True]).time == 12.0


@pytest.mark.parametrize("bad", [[E1, -1, False], [E1, 1], [E1, "x", False]])
def test_malformed_timecodes_are_rejected(bad: Any) -> None:
    with pytest.raises(pydantic.ValidationError):
        Timecode.model_validate(bad)


def test_history_entry_carries_the_episode_and_its_release() -> None:
    entry = HistoryEntry.model_validate(
        {**VIEW, "release_episode": {**EPISODE, "release": RELEASE}}
    )

    assert isinstance(entry, EpisodeView)
    assert entry.release_episode is not None
    assert entry.release_episode.release is not None
    assert entry.release_episode.release.id == 9839
    assert entry.updated_at == datetime(2026, 10, 16, 17, 30, 2, tzinfo=UTC)


# --- timecodes ------------------------------------------------------------------------------


async def test_timecodes_parses_the_triples() -> None:
    api = FakeApi([[E2, 12, False], [E1, 743.5, True]])

    timecodes = await call(api, "me.views.timecodes")

    assert timecodes == [
        Timecode(release_episode_id=E2, time=12, is_watched=False),
        Timecode(release_episode_id=E1, time=743.5, is_watched=True),
    ]
    assert api.requests[0].url.path == f"{VIEWS}/timecodes"
    assert "since" not in api.requests[0].url.params
    assert api.requests[0].headers["Authorization"] == "Bearer t0k3n"


@pytest.mark.parametrize(
    ("since", "sent"),
    [
        (datetime(2026, 10, 16, 17, 34, 17, tzinfo=UTC), "2026-10-16T17:34:17+00:00"),
        (
            datetime(2026, 10, 16, 20, 34, tzinfo=timezone(timedelta(hours=3))),
            "2026-10-16T20:34:00+03:00",
        ),
    ],
)
async def test_timecodes_since_is_sent_in_iso_format(since: datetime, sent: str) -> None:
    api = FakeApi([])

    await call(api, "me.views.timecodes", since=since)

    assert api.requests[0].url.params["since"] == sent


async def test_timecodes_since_must_be_timezone_aware() -> None:
    api = FakeApi([])
    with pytest.raises(ValueError, match="timezone-aware"):
        await call(api, "me.views.timecodes", since=datetime(2026, 10, 16))

    assert api.requests == []


async def test_save_timecodes_sends_them_as_a_json_array() -> None:
    api = FakeApi(respond=empty_html)

    result = await call(
        api,
        "me.views.save_timecodes",
        Timecode(release_episode_id=E1, time=743.5),
        Timecode(release_episode_id=E2, time=1420, is_watched=True),
    )

    assert result is None
    request = api.requests[0]
    assert request.method == "POST"
    assert request.url.path == f"{VIEWS}/timecodes"
    assert json.loads(request.content) == [
        {"release_episode_id": E1, "time": 743.5, "is_watched": False},
        {"release_episode_id": E2, "time": 1420.0, "is_watched": True},
    ]


@pytest.mark.parametrize(
    ("args", "error", "match"),
    [
        ((), ValueError, "at least one Timecode"),
        (([E1, 1, False],), TypeError, "Expected a Timecode"),
        (({"release_episode_id": E1, "time": 1},), TypeError, "Expected a Timecode"),
    ],
)
async def test_save_timecodes_checks_arguments_before_sending(
    args: tuple[Any, ...], error: type[Exception], match: str
) -> None:
    api = FakeApi(respond=empty_html)
    with pytest.raises(error, match=match):
        await call(api, "me.views.save_timecodes", *args)

    assert api.requests == []


async def test_remove_timecodes_takes_ids_episodes_and_timecodes() -> None:
    api = FakeApi(respond=empty_html)
    episode = Episode.model_validate({**EPISODE, "id": E2})

    await call(
        api,
        "me.views.remove_timecodes",
        E1,
        episode,
        Timecode(release_episode_id="c83264c3-0000-0000-0000-000000000000", time=1),
    )

    request = api.requests[0]
    assert request.method == "DELETE"
    assert json.loads(request.content) == [
        {"release_episode_id": E1},
        {"release_episode_id": E2},
        {"release_episode_id": "c83264c3-0000-0000-0000-000000000000"},
    ]


@pytest.mark.parametrize(
    ("args", "error", "match"),
    [
        ((), ValueError, "at least one episode"),
        ((E1, 5), TypeError, "Expected an episode ID"),
        (("",), TypeError, "Expected an episode ID"),
    ],
)
async def test_remove_timecodes_checks_arguments_before_sending(
    args: tuple[Any, ...], error: type[Exception], match: str
) -> None:
    api = FakeApi(respond=empty_html)
    with pytest.raises(error, match=match):
        await call(api, "me.views.remove_timecodes", *args)

    assert api.requests == []


# --- history --------------------------------------------------------------------------------


def history_page(entries: list[dict[str, Any]], *, current: int, pages: int) -> dict[str, Any]:
    pagination = {"total": 3, "per_page": 2, "current_page": current, "total_pages": pages}
    return {"data": entries, "meta": {"pagination": pagination}}


def entry(view_id: int) -> dict[str, Any]:
    return {**VIEW, "id": view_id, "release_episode": {**EPISODE, "release": RELEASE}}


async def test_history_returns_a_page_of_entries() -> None:
    api = FakeApi(history_page([entry(1), entry(2)], current=2, pages=2))

    page = await call(api, "me.views.history", page=2, limit=2)

    assert [e.id for e in page.items] == [1, 2]
    assert all(isinstance(e, HistoryEntry) for e in page.items)
    assert api.requests[0].url.path == f"{VIEWS}/history"
    assert dict(api.requests[0].url.params) == {"page": "2", "limit": "2"}


async def test_iter_history_walks_all_pages() -> None:
    pages = {
        "1": history_page([entry(1), entry(2)], current=1, pages=2),
        "2": history_page([entry(3)], current=2, pages=2),
    }
    api = FakeApi(respond=lambda r: httpx.Response(200, json=pages[r.url.params["page"]]))
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    async with AniLiberty(http_client=http_client, token="t0k3n") as client:
        ids = [e.id async for e in client.me.views.iter_history(limit=2)]
    await http_client.aclose()

    assert ids == [1, 2, 3]


# --- the anime-namespace timecode endpoints -------------------------------------------------


async def test_episode_timecode() -> None:
    api = FakeApi(VIEW)

    view = await call(api, "episodes.timecode", E1)

    assert view == EpisodeView.model_validate(VIEW)
    assert api.requests[0].url.path == f"/api/v1/anime/releases/episodes/{E1}/timecode"


async def test_release_timecodes_by_id_or_alias() -> None:
    api = FakeApi([VIEW])

    views = await call(api, "releases.timecodes", "some-alias")

    assert [v.release_episode_id for v in views] == [E1]
    assert api.requests[0].url.path == "/api/v1/anime/releases/some-alias/episodes/timecodes"


@pytest.mark.parametrize(
    ("method", "value"), [("episodes.timecode", "../x"), ("releases.timecodes", "a/b")]
)
async def test_path_arguments_are_checked(method: str, value: str) -> None:
    api = FakeApi([])
    with pytest.raises(ValueError, match="Invalid"):
        await call(api, method, value)

    assert api.requests == []
