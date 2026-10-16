"""``client.auth`` — the ``Аккаунты.Пользователи.Авторизация.*`` and
``Аккаунты.ОдноразовыеПароли`` tags of the spec."""

from __future__ import annotations

from typing import get_args

from aniliberty._http import HttpClient
from aniliberty.exceptions import AuthRequiredError
from aniliberty.models.auth import AuthToken, IssuedOtp, SocialLogin, SocialProvider
from aniliberty.resources._base import BaseResource

SESSION_COOKIE = "_al1"
"""Cookie the API sets alongside a login response; it holds the same token."""


class _SessionResource(BaseResource):
    """A resource whose methods start a session and store its token on the client."""

    async def _start_session(
        self, path: str, body: dict[str, object], *, with_token: bool = True
    ) -> AuthToken:
        payload = await self._http.request("POST", path, json=body, with_token=with_token)
        return self._store(self._parse(payload, AuthToken, path=path))

    def _store(self, token: AuthToken) -> AuthToken:
        self._http.token = token.token
        self._http.discard_cookie(SESSION_COOKIE)
        return token


class AuthResource(_SessionResource):
    """Logging in and out, available as ``client.auth``.

    A successful login stores the session token on the client (``client.token``), so
    account methods work right after it. To reuse a session across runs, save
    ``client.token`` and pass it back as ``AniLiberty(token=...)`` — logging in on every run
    piles up sessions on the account.

    Attributes:
        otp: Logging a device in with a one-time code.
        social: Logging in with a social network.
        password: Recovering a forgotten password.
    """

    ENDPOINTS = (
        ("POST", "/accounts/users/auth/login"),
        ("POST", "/accounts/users/auth/logout"),
    )

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.otp = OtpResource(http)
        self.social = SocialAuthResource(http)
        self.password = PasswordResource(http)

    async def login(self, *, login: str, password: str) -> AuthToken:
        """Log in with a login (or e-mail) and password, and use the session from now on.

        Args:
            login: The account's login or e-mail; the login is case-insensitive.
            password: The account's password.

        Returns:
            The new session's token, also stored as ``client.token``.

        Raises:
            AuthRequiredError: Wrong login or password (HTTP 401); the API's reason is in
                ``message``.
            ValidationError: ``login`` or ``password`` is empty.
            APIError: The API answered with another error.
            TransportError: The request failed without a response. Not retried: login is a
                ``POST``.
            ResponseParseError: The response didn't match ``AuthToken``.

        Example:
            ```python
            async with AniLiberty() as client:
                await client.auth.login(login="me", password=os.environ["ANILIBERTY_PASSWORD"])
                print(client.token is not None)  # True
            ```
        """
        return await self._start_session(
            "/accounts/users/auth/login", {"login": login, "password": password}
        )

    async def logout(self) -> None:
        """End the client's session and stop sending its token.

        Only this session is ended; other sessions of the account (other devices, other
        logins) stay valid. ``client.token`` is ``None`` afterwards, also when the API
        rejects the token as already invalid.

        Raises:
            AuthRequiredError: The client has no token, or the API no longer accepts it
                (logged out or expired) — the session is over either way (HTTP 403).
            APIError: The API answered with another error; the token is kept.
            TransportError: The request failed without a response; the token is kept.

        Example:
            ```python
            await client.auth.logout()
            print(client.token)  # None
            ```
        """
        try:
            await self._http.request("POST", "/accounts/users/auth/logout")
        except AuthRequiredError:
            self._http.token = None
            raise
        self._http.token = None


class OtpResource(_SessionResource):
    """Logging a device in with a one-time code, available as ``client.auth.otp``.

    Meant for devices where typing a password is awkward (a TV app):

    1. The device calls ``get(device_id=...)`` and shows the code.
    2. The user enters the code on a device where they are logged in, which calls
       ``accept(code)``.
    3. The device calls ``login(code=..., device_id=...)`` and gets its own session.

    A code lives 5 minutes and logs in once.
    """

    ENDPOINTS = (
        ("POST", "/accounts/otp/get"),
        ("POST", "/accounts/otp/accept"),
        ("POST", "/accounts/otp/login"),
    )

    async def get(self, *, device_id: str) -> IssuedOtp:
        """Issue a one-time code for a device. No session needed.

        Asking again for the same ``device_id`` while the code is alive returns the same code.

        Args:
            device_id: Any string identifying the device, e.g. a UUID it keeps; the same
                value must be passed to ``login()``.

        Returns:
            The code and the seconds it has left.

        Raises:
            ValidationError: ``device_id`` is empty.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``IssuedOtp``.

        Example:
            ```python
            issued = await client.auth.otp.get(device_id=str(uuid.uuid4()))
            print(issued.otp.code, issued.remaining_time)
            ```
        """
        payload = await self._http.request(
            "POST", "/accounts/otp/get", json={"device_id": device_id}
        )
        return self._parse(payload, IssuedOtp, path="/accounts/otp/get")

    async def accept(self, code: str | int) -> None:
        """Approve a one-time code with the client's session, letting its device log in.

        Args:
            code: The code the other device shows. Pass it as the string ``get()``
                returned — as an ``int`` a leading ``0`` would be lost.

        Raises:
            AuthRequiredError: The client has no valid session.
            NotFoundError: No live code like that.
            ValidationError: ``code`` is malformed.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            await client.auth.otp.accept("058701")
            ```
        """
        await self._http.request("POST", "/accounts/otp/accept", json={"code": code})

    async def login(self, *, code: str | int, device_id: str) -> AuthToken:
        """Log the device in with an accepted code, and use the session from now on.

        Sent without the client's current token, if it has one: the API refuses this request
        from a logged-in caller (403). The new token replaces the old one.

        Args:
            code: The code from ``get()``, after it was accepted.
            device_id: The same ``device_id`` that was passed to ``get()``.

        Returns:
            The new session's token, also stored as ``client.token``.

        Raises:
            NotFoundError: No live code for this device — wrong code or ``device_id``,
                expired, or already used.
            ServerError: The code hasn't been accepted yet — the API answers 500 to that.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``AuthToken``.

        Example:
            ```python
            await client.auth.otp.login(code=issued.otp.code, device_id=device_id)
            ```
        """
        return await self._start_session(
            "/accounts/otp/login", {"code": code, "device_id": device_id}, with_token=False
        )


class SocialAuthResource(_SessionResource):
    """Logging in with a social network, available as ``client.auth.social``.

    1. ``login(provider)`` returns an OAuth ``url`` and a ``state`` key.
    2. The user opens ``url`` in a browser and logs in with the social network.
    3. ``authenticate(state)`` exchanges the key for a session.
    """

    ENDPOINTS = (
        ("GET", "/accounts/users/auth/social/{provider}/login"),
        ("GET", "/accounts/users/auth/social/authenticate"),
    )

    async def login(self, provider: SocialProvider) -> SocialLogin:
        """Start logging in with a social network.

        Args:
            provider: ``"vk"``, ``"google"``, ``"patreon"`` or ``"discord"``.

        Returns:
            The OAuth page to send the user to, and the key to finish with.

        Raises:
            ValueError: ``provider`` isn't one of the above — checked before sending (the
                API answers 500 to unknown names).
            APIError: The API answered with an error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``SocialLogin``.

        Example:
            ```python
            start = await client.auth.social.login("discord")
            print("Open in a browser:", start.url)
            ```
        """
        if provider not in get_args(SocialProvider):
            allowed = ", ".join(get_args(SocialProvider))
            raise ValueError(f"Unknown social provider {provider!r}; expected one of: {allowed}")
        return await self._get(f"/accounts/users/auth/social/{provider}/login", SocialLogin)

    async def authenticate(self, state: str) -> AuthToken:
        """Finish a social login, and use the session from now on.

        Args:
            state: ``SocialLogin.state`` from ``login()``, after the user logged in on the
                OAuth page.

        Returns:
            The new session's token, also stored as ``client.token``.

        Raises:
            NotFoundError: Unknown ``state``, or the user hasn't finished logging in yet.
            ValidationError: ``state`` is empty.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``AuthToken``.

        Example:
            ```python
            await client.auth.social.authenticate(start.state)
            ```
        """
        token = await self._get(
            "/accounts/users/auth/social/authenticate", AuthToken, params={"state": state}
        )
        return self._store(token)


class PasswordResource(BaseResource):
    """Recovering a forgotten password, available as ``client.auth.password``."""

    ENDPOINTS = (
        ("POST", "/accounts/users/auth/password/forget"),
        ("POST", "/accounts/users/auth/password/reset"),
    )

    async def forget(self, *, email: str) -> None:
        """Ask the API to e-mail a password reset link.

        The answer is the same whether or not an account has this e-mail, so it can't be
        used to check for one.

        Args:
            email: The account's e-mail.

        Raises:
            ValidationError: ``email`` is empty or not an e-mail address.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            await client.auth.password.forget(email="me@example.com")
            ```
        """
        await self._http.request(
            "POST", "/accounts/users/auth/password/forget", json={"email": email}
        )

    async def reset(self, *, token: str, password: str) -> None:
        """Set a new password with the token from the reset e-mail.

        Doesn't log in: call ``client.auth.login()`` with the new password afterwards.

        Args:
            token: The token from the link in the e-mail sent by ``forget()``.
            password: The new password (sent as both ``password`` and its confirmation).

        Raises:
            NotFoundError: Unknown or used ``token``.
            ValidationError: The password doesn't meet the API's rules, or a field is empty.
            APIError: The API answered with another error.
            TransportError: The request failed without a response.

        Example:
            ```python
            await client.auth.password.reset(token=token_from_email, password=new_password)
            ```
        """
        await self._http.request(
            "POST",
            "/accounts/users/auth/password/reset",
            json={"token": token, "password": password, "password_confirmation": password},
        )
