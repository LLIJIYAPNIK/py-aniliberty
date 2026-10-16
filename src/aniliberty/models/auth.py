"""Authentication models (spec tags ``Аккаунты.Пользователи.Авторизация.*`` and
``Аккаунты.ОдноразовыеПароли``)."""

from datetime import datetime
from typing import Literal

from aniliberty.models._base import AniLibertyModel

# Copied from the `enums.accounts.users.user.social.type` schema of spec/openapi.json (the
# spec-sync test in tests/unit/test_auth_resource.py fails if they drift apart). The API
# answers 500 to anything else, including other letter case.
SocialProvider = Literal["vk", "google", "patreon", "discord"]
"""Social networks that can be used to log in."""


class AuthToken(AniLibertyModel):
    """A session token, returned by the login methods of ``client.auth``.

    Spec schemas: ``responses.v1.accounts.users.auth.login``,
    ``responses.api.v1.accounts.otp.login``,
    ``responses.v1.accounts.users.auth.social.authenticate``.

    The token is an opaque string (32 characters at the time of writing) with no expiry
    inside; the API has no refresh endpoint. Every login creates a new, independent session,
    and ``client.auth.logout()`` ends only the client's own.

    Attributes:
        token: The session token. Keep it secret — it gives full access to the account.
    """

    token: str


class Otp(AniLibertyModel):
    """A one-time code for logging in a device without typing the password.

    Spec schema: ``models.accounts.otp.v1.otp``.

    Attributes:
        code: The code to show to the user, as a string — it can start with ``0``.
        device_id: The device the code was issued for.
        user_id: The account that accepted the code; ``None`` until it's accepted.
        expired_at: When the code expires.
    """

    code: str
    device_id: str
    user_id: int | None = None
    expired_at: datetime


class IssuedOtp(AniLibertyModel):
    """A one-time code issued by ``client.auth.otp.issue()``.

    Spec schema: ``responses.api.v1.accounts.otp.get``.

    Attributes:
        otp: The code.
        remaining_time: Seconds until the code expires (fractional; about 300 for a new code).
    """

    otp: Otp
    remaining_time: float


class SocialLogin(AniLibertyModel):
    """Where to send the user to log in with a social network.

    Spec schema: ``responses.v1.accounts.users.auth.social.login``.

    Attributes:
        url: The OAuth page of the social network, to open in a browser.
        state: Key to pass to ``client.auth.social.authenticate()`` once the user has
            logged in there.
    """

    url: str
    state: str
