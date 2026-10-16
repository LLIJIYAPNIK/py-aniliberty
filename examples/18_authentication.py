"""Authentication: logging in, reusing the session token, logging out.

The account endpoints (client.me.*, client.releases.ratings, timecodes) need a session. You
get one by logging in; the SDK keeps its token on the client (client.token) and sends it as
"Authorization: Bearer <token>" with every request.

Run it with the credentials of an AniLibria account in the environment:

    ANILIBERTY_LOGIN=... ANILIBERTY_PASSWORD=... python examples/18_authentication.py

The token is a secret that gives full access to the account, so this script never prints it
(nor the login or e-mail) — only its length.
"""

import asyncio
import os

from aniliberty import AniLiberty, AuthRequiredError


async def main() -> None:
    login = os.environ["ANILIBERTY_LOGIN"]  # the login or the account's e-mail
    password = os.environ["ANILIBERTY_PASSWORD"]

    # 1. Wrong credentials are a 401, raised as AuthRequiredError; the API's reason (in
    #    Russian) is in .message. Nothing is retried: a login is a POST.
    async with AniLiberty() as client:
        try:
            await client.auth.login(login=login, password="definitely-not-the-password")
        except AuthRequiredError as error:
            print(f"Wrong password: HTTP {error.status_code}, {error.message!r}")

    # 2. A successful login returns an AuthToken and stores the token on the client, so the
    #    account endpoints work right away.
    async with AniLiberty() as client:
        session = await client.auth.login(login=login, password=password)
        assert client.token == session.token
        print(f"Logged in, token of {len(session.token)} characters")

        profile = await client.me.profile()
        created = f"{profile.created_at:%Y-%m-%d}"
        print(f"Account #{profile.id}, created {created}, banned: {profile.is_banned}")
        # The tracker passkey is a secret too: it's left out of the model's repr.
        assert profile.torrents is not None
        print("Passkey in repr:", "passkey=" in repr(profile.torrents))

        # Save the token to reuse the session later instead of logging in on every run —
        # every login creates a new session on the account. Keep it somewhere private
        # (a keyring, an env var), never in code or logs.
        saved_token = client.token

    # 3. Reuse the saved token: no login request at all. The token has no expiry inside it
    #    and the API has no refresh endpoint; when it stops working you get a 403 and log in
    #    again.
    async with AniLiberty(token=saved_token) as client:
        profile_again = await client.me.profile()
        print("Same account with the saved token:", profile_again.id == profile.id)

        # Public endpoints work with or without a token (even with a stale one).
        status = await client.app.status()
        print("Public endpoint with a token:", status.is_alive)

        # 4. Logging out ends this session only (other logins of the account stay valid) and
        #    clears client.token.
        await client.auth.logout()
        print("After logout, client.token is", client.token)

        # The logged-out token is rejected like a missing one: 403 "This action is
        # unauthorized." — the API doesn't tell a missing, invalid or expired token apart.
        client.token = saved_token
        try:
            await client.me.profile()
        except AuthRequiredError as error:
            print(f"Logged-out token: HTTP {error.status_code}, {error.message!r}")


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Wrong password: HTTP 401, 'Не удалось авторизоваться. Неправильные логин/пароль'
# Logged in, token of 32 characters
# Account #799331, created 2026-10-16, banned: False
# Passkey in repr: False
# Same account with the saved token: True
# Public endpoint with a token: True
# After logout, client.token is None
# Logged-out token: HTTP 403, 'This action is unauthorized.'
