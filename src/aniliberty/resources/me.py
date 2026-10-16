"""``client.me`` — the ``Аккаунты.Пользователи.Мое.*`` tags of the spec."""

from __future__ import annotations

from aniliberty._http import HttpClient
from aniliberty.models.user import UserProfile
from aniliberty.resources._base import BaseResource
from aniliberty.resources.favorites import FavoritesResource


class MeResource(BaseResource):
    """The logged-in user's own account, available as ``client.me``.

    Every method needs a session: log in with ``client.auth.login()`` or pass
    ``AniLiberty(token=...)``. Without a valid one the API answers 403, raised as
    ``AuthRequiredError``.

    Attributes:
        favorites: The user's favorite releases.
    """

    ENDPOINTS = (("GET", "/accounts/users/me/profile"),)

    def __init__(self, http: HttpClient) -> None:
        super().__init__(http)
        self.favorites = FavoritesResource(http)

    async def profile(self) -> UserProfile:
        """Get the logged-in user's profile.

        Returns:
            The profile, with the account's e-mail and tracker passkey.

        Raises:
            AuthRequiredError: No session token, or the API doesn't accept it (logged out or
                expired).
            APIError: The API answered with another error.
            TransportError: The request failed without a response.
            ResponseParseError: The response didn't match ``UserProfile``.

        Example:
            ```python
            async with AniLiberty(token=saved_token) as client:
                me = await client.me.profile()
                print(me.nickname, me.created_at)
            ```
        """
        return await self._get("/accounts/users/me/profile", UserProfile)
