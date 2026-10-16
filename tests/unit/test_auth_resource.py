"""client.auth and the session token: request bodies, token storage, cookies, error paths."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, get_args

import httpx
import pytest

from aniliberty import (
    AniLiberty,
    AuthRequiredError,
    AuthToken,
    IssuedOtp,
    NotFoundError,
    ServerError,
    SocialLogin,
)
from aniliberty.models import SocialProvider

SPEC = json.loads((Path(__file__).parents[2] / "spec" / "openapi.json").read_text("utf-8"))
TOKEN = "s9HYwZ0000000000000000000000000a"
EMPTY_HTML = {"Content-Type": "text/html; charset=UTF-8"}


class FakeApi:
    """Records requests and answers each path with a canned response."""

    def __init__(self, routes: dict[str, httpx.Response]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.routes.get(request.url.path.removeprefix("/api/v1"), httpx.Response(200))

    def body(self, index: int = -1) -> Any:
        return json.loads(self.requests[index].content)


def login_response(token: str = TOKEN) -> httpx.Response:
    # The real login response also sets the token as the _al1 cookie.
    headers = {"Set-Cookie": f"_al1={token}; Max-Age=691200; path=/; HttpOnly; SameSite=lax"}
    return httpx.Response(200, json={"token": token}, headers=headers)


def make_client(api: FakeApi, **kwargs: Any) -> AniLiberty:
    return AniLiberty(http_client=httpx.AsyncClient(transport=httpx.MockTransport(api)), **kwargs)


def test_social_provider_literal_matches_the_spec_enum() -> None:
    schema = SPEC["components"]["schemas"]["enums.accounts.users.user.social.type"]
    assert list(get_args(SocialProvider)) == schema["enum"]


# --- the token on the client ------------------------------------------------------------------


async def test_no_token_by_default_sends_no_authorization() -> None:
    api = FakeApi({})
    async with make_client(api) as client:
        assert client.token is None
        await client.http.request("GET", "/app/status")

    assert "Authorization" not in api.requests[0].headers


async def test_token_from_constructor_is_sent_as_bearer() -> None:
    api = FakeApi({})
    async with make_client(api, token=TOKEN) as client:
        await client.http.request("GET", "/app/status")

    assert api.requests[0].headers["Authorization"] == f"Bearer {TOKEN}"


async def test_token_replaces_an_authorization_header_and_can_be_unset() -> None:
    api = FakeApi({})
    async with make_client(api, headers={"Authorization": "Bearer old"}, token=TOKEN) as client:
        await client.http.request("GET", "/x")
        client.token = None
        await client.http.request("GET", "/x")
        client.token = ""  # empty means no token too
        assert client.token is None

    assert api.requests[0].headers["Authorization"] == f"Bearer {TOKEN}"
    assert api.requests[1].headers["Authorization"] == "Bearer old"


# --- login / logout -------------------------------------------------------------------------


async def test_login_sends_credentials_and_stores_the_token() -> None:
    api = FakeApi({"/accounts/users/auth/login": login_response()})
    async with make_client(api) as client:
        result = await client.auth.login(login="me", password="secret")
        await client.http.request("GET", "/accounts/users/me/profile")

    assert result == AuthToken(token=TOKEN)
    assert client.token == TOKEN
    assert api.requests[0].method == "POST"
    assert api.body(0) == {"login": "me", "password": "secret"}
    profile_request = api.requests[1]
    assert profile_request.headers["Authorization"] == f"Bearer {TOKEN}"
    # The _al1 cookie from the login response isn't kept: the token is the only credential.
    assert "Cookie" not in profile_request.headers


async def test_login_with_wrong_credentials_raises_and_keeps_no_token() -> None:
    body = {"token": None, "error": "Не удалось авторизоваться. Неправильные логин/пароль"}
    api = FakeApi({"/accounts/users/auth/login": httpx.Response(401, json=body)})
    async with make_client(api) as client:
        with pytest.raises(AuthRequiredError) as excinfo:
            await client.auth.login(login="me", password="wrong")

    assert excinfo.value.status_code == 401
    assert excinfo.value.message == body["error"]
    assert client.token is None
    assert len(api.requests) == 1  # a POST isn't retried


async def test_logout_ends_the_session_and_clears_the_token() -> None:
    api = FakeApi({"/accounts/users/auth/logout": httpx.Response(200, json={"token": None})})
    async with make_client(api, token=TOKEN) as client:
        assert await client.auth.logout() is None
        assert client.token is None

    assert api.requests[0].method == "POST"
    assert api.requests[0].headers["Authorization"] == f"Bearer {TOKEN}"


async def test_logout_with_a_rejected_token_clears_it_and_raises() -> None:
    body = {"message": "This action is unauthorized."}
    api = FakeApi({"/accounts/users/auth/logout": httpx.Response(403, json=body)})
    async with make_client(api, token=TOKEN) as client:
        with pytest.raises(AuthRequiredError):
            await client.auth.logout()
        assert client.token is None


async def test_logout_keeps_the_token_when_the_outcome_is_unknown() -> None:
    api = FakeApi({"/accounts/users/auth/logout": httpx.Response(500, json={"message": "x"})})
    async with make_client(api, token=TOKEN) as client:
        with pytest.raises(ServerError):
            await client.auth.logout()
        assert client.token == TOKEN


# --- one-time codes -------------------------------------------------------------------------

ISSUED = {
    "otp": {
        "code": "058701",
        "user_id": None,
        "device_id": "tv-1",
        "expired_at": "2026-10-16T16:50:12+00:00",
    },
    "remaining_time": 299.655569,
}


async def test_otp_get_parses_the_code_keeping_leading_zero() -> None:
    api = FakeApi({"/accounts/otp/get": httpx.Response(200, json=ISSUED)})
    async with make_client(api) as client:
        issued = await client.auth.otp.get(device_id="tv-1")

    assert isinstance(issued, IssuedOtp)
    assert issued.otp.code == "058701"
    assert issued.otp.user_id is None
    assert issued.otp.expired_at.tzinfo is not None
    assert issued.remaining_time == pytest.approx(299.66, abs=0.01)
    assert api.body() == {"device_id": "tv-1"}


async def test_otp_accept_sends_the_code_as_given_and_tolerates_empty_html_200() -> None:
    # The API answers a successful accept with an empty text/html body.
    api = FakeApi({"/accounts/otp/accept": httpx.Response(200, text="", headers=EMPTY_HTML)})
    async with make_client(api, token=TOKEN) as client:
        assert await client.auth.otp.accept("058701") is None

    assert api.body() == {"code": "058701"}
    assert api.requests[0].headers["Authorization"] == f"Bearer {TOKEN}"


async def test_otp_login_is_sent_without_the_current_token_and_replaces_it() -> None:
    # The API answers 403 to an OTP login from a logged-in caller.
    api = FakeApi({"/accounts/otp/login": login_response("otp-token")})
    async with make_client(api, token=TOKEN) as client:
        result = await client.auth.otp.login(code="058701", device_id="tv-1")

    assert result.token == "otp-token"
    assert client.token == "otp-token"
    assert api.body() == {"code": "058701", "device_id": "tv-1"}
    assert "Authorization" not in api.requests[0].headers


# --- social networks ------------------------------------------------------------------------


async def test_social_login_returns_the_oauth_url() -> None:
    body = {"url": "https://oauth.vk.ru/authorize?state=abc", "state": "abc"}
    api = FakeApi({"/accounts/users/auth/social/vk/login": httpx.Response(200, json=body)})
    async with make_client(api) as client:
        start = await client.auth.social.login("vk")

    assert start == SocialLogin(url=body["url"], state="abc")
    assert api.requests[0].method == "GET"


@pytest.mark.parametrize("provider", ["VK", "facebook", "", "vk/../x"])
async def test_social_login_rejects_unknown_providers_before_sending(provider: str) -> None:
    api = FakeApi({})
    async with make_client(api) as client:
        with pytest.raises(ValueError, match="Unknown social provider"):
            await client.auth.social.login(provider)  # type: ignore[arg-type]

    assert api.requests == []


async def test_social_authenticate_stores_the_token() -> None:
    body = {"token": "social-token"}
    api = FakeApi({"/accounts/users/auth/social/authenticate": httpx.Response(200, json=body)})
    async with make_client(api) as client:
        await client.auth.social.authenticate("abc")

    assert client.token == "social-token"
    assert api.requests[0].url.params["state"] == "abc"


async def test_social_authenticate_unknown_state_is_not_found_not_blocked() -> None:
    # Live, an unknown state is a 404 with an empty text/html body.
    route = httpx.Response(404, text="", headers=EMPTY_HTML)
    api = FakeApi({"/accounts/users/auth/social/authenticate": route})
    async with make_client(api) as client:
        with pytest.raises(NotFoundError):
            await client.auth.social.authenticate("unknown")
        assert client.token is None


# --- password -------------------------------------------------------------------------------


async def test_password_forget_sends_the_email() -> None:
    route = httpx.Response(200, text="", headers=EMPTY_HTML)
    api = FakeApi({"/accounts/users/auth/password/forget": route})
    async with make_client(api) as client:
        assert await client.auth.password.forget(email="me@example.com") is None

    assert api.body() == {"email": "me@example.com"}


async def test_password_reset_sends_the_password_with_its_confirmation() -> None:
    api = FakeApi({})
    async with make_client(api) as client:
        await client.auth.password.reset(token="from-email", password="n3w-Password")

    assert api.body() == {
        "token": "from-email",
        "password": "n3w-Password",
        "password_confirmation": "n3w-Password",
    }
