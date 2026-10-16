# Authentication and account features

Public endpoints — releases, the catalog, the schedule and so on — need no account. The
account features need a **session**:

| Namespace | What it does |
|---|---|
| [`client.auth`][aniliberty.resources.AuthResource] | logging in and out (password, one-time code, social network), password recovery |
| [`client.me.profile()`][aniliberty.resources.MeResource.profile] | the user's profile |
| [`client.me.favorites`][aniliberty.resources.FavoritesResource] | favorite releases |
| [`client.me.collections`][aniliberty.resources.CollectionsResource] | the five collections: planned, watching, watched, postponed, abandoned |
| [`client.me.views`][aniliberty.resources.ViewsResource] | watch progress (timecodes) and history |
| [`client.releases.ratings`][aniliberty.resources.RatingsResource] | the user's own 1–10 scores |
| [`client.releases.timecodes()`][aniliberty.resources.ReleasesResource.timecodes], [`client.episodes.timecode()`][aniliberty.resources.EpisodesResource.timecode] | stored watch records of a release / an episode |

Runnable examples, each a short tutorial:
[`18_authentication.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/18_authentication.py),
[`19_otp_device_login.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/19_otp_device_login.py),
[`20_favorites.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/20_favorites.py),
[`21_collections.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/21_collections.py),
[`22_watch_progress.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/22_watch_progress.py),
[`23_release_ratings.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/examples/23_release_ratings.py).

## Logging in

```python
import os

from aniliberty import AniLiberty

async with AniLiberty() as client:
    await client.auth.login(
        login=os.environ["ANILIBERTY_LOGIN"],  # the login or the account's e-mail
        password=os.environ["ANILIBERTY_PASSWORD"],
    )
    profile = await client.me.profile()
```

[`login()`][aniliberty.resources.AuthResource.login] returns an
[`AuthToken`][aniliberty.AuthToken] and stores its token on the client as
[`client.token`][aniliberty.AniLiberty.token]. From then on every request carries
`Authorization: Bearer <token>`. The login is case-insensitive; an e-mail works in its place.

Wrong credentials raise [`AuthRequiredError`][aniliberty.AuthRequiredError] with HTTP 401
and the API's reason (in Russian) in `error.message`. A login is a `POST`, so it is never
retried.

!!! warning "Keep credentials and the token out of your code"
    Read the login and password from the environment or a secret store. The token gives full
    access to the account: don't log it, don't commit it. The same goes for the tracker
    passkey in `profile.torrents.passkey` — the SDK leaves it out of the model's `repr`.

## Reusing a session

Every login creates a **new, independent session** on the account. A script that logs in on
every run piles them up, so save the token and pass it back next time:

```python
token = client.token  # after client.auth.login(...); store it somewhere private

async with AniLiberty(token=token) as client:  # no login request
    await client.me.favorites.ids()
```

You can also assign `client.token = ...` at any time; `None` stops sending it.

What the API tells about the token (see [API notes](../api-notes.md#authentication-checked-2026-10-16)):

- It's an opaque string (32 characters), not a JWT: there is no expiry inside to read, and
  there is **no refresh endpoint**. The site's cookie for it lasts 8 days; whether the
  session on the server ends then hasn't been verified.
- When a token stops working, you get the same answer as with no token at all — see below.
  Log in again and save the new token.
- Public endpoints don't care: a stale token doesn't break them.

## Logging out

[`logout()`][aniliberty.resources.AuthResource.logout] ends **this** session only — other
logins of the account (other devices, other scripts) stay valid — and clears
`client.token`. It's also cleared when the API answers that the token is already invalid;
after a network error or a 5xx it's kept, since the session may still be alive.

## When a session is missing or invalid

Every account endpoint answers **403** `"This action is unauthorized."`, raised as
`AuthRequiredError`, when the client has no token, a malformed one, a logged-out one or an
expired one — the API doesn't say which. The SDK doesn't check for a token before sending,
so all of these cases look the same:

```python
from aniliberty import AuthRequiredError

try:
    await client.me.profile()
except AuthRequiredError as error:
    if error.status_code == 403:
        ...  # log in again
```

| Status | Meaning |
|---|---|
| 401 | wrong login or password at `client.auth.login()` |
| 403 | no valid session for an account endpoint |

## Logging a device in with a one-time code

For a TV app or anything else without a comfortable keyboard,
[`client.auth.otp`][aniliberty.resources.OtpResource] logs a device in with a code that the
user confirms from a device where they are already logged in:

```python
issued = await tv.auth.otp.get(device_id=device_id)  # no session needed
show_on_screen(issued.otp.code)  # 6 digits, a string; lives ~5 minutes

await phone.auth.otp.accept(issued.otp.code)  # the phone has a session

await tv.auth.otp.login(code=issued.otp.code, device_id=device_id)  # the TV gets its own
```

- `device_id` is any string the device keeps (a UUID, say); `get()` and `login()` must get
  the same one.
- Keep the code a string: it can start with `0`.
- `login()` before the code is accepted fails with a `ServerError` (the API answers 500);
  an unknown, expired or already used code is a `NotFoundError`.
- The API refuses an OTP login from a client that is already logged in, so the SDK sends
  that request without the token; the new token then replaces the old one.

## Social networks

[`client.auth.social`][aniliberty.resources.SocialAuthResource] supports the providers of the
spec: `"vk"`, `"google"`, `"patreon"`, `"discord"`.

```python
start = await client.auth.social.login("discord")
print("Open in a browser:", start.url)  # the user logs in there
...
await client.auth.social.authenticate(start.state)  # then trade the state for a session
```

`authenticate()` raises `NotFoundError` until the user has finished on the OAuth page (or
for an unknown `state`). The full browser round trip wasn't exercised while building the SDK.

## Password recovery

```python
await client.auth.password.forget(email="me@example.com")  # sends a reset link
await client.auth.password.reset(token=token_from_the_email, password=new_password)
```

`forget()` answers the same whether or not the e-mail belongs to an account. `reset()`
doesn't log in — call `login()` with the new password afterwards.

## Things the API does that you should know about

These were found by trying, and are described in detail in the [API notes](../api-notes.md):

- **Favorites and collections accept release IDs that don't exist.** They show up in
  `ids()` but never in `releases()`. Adding something twice or removing what isn't there is a
  silent no-op.
- **A release is in one collection at most**: adding it to another moves it.
- **Collection changes are also applied in the background.** A release removed right
  after it was added can reappear about a minute later, and a removal can take minutes
  to stick. If you need a known state, remove, wait a minute, check `ids()` and repeat
  (see `21_collections.py`).
- **Timecodes are stored in two steps.** `client.me.views.timecodes()` has a saved timecode
  at once; the history, `client.episodes.timecode()` and `client.releases.timecodes()` get it
  about a minute later. Deleting lags the same way, and `timecodes()` can keep listing a
  deleted timecode until it's deleted once more after that minute.
- **Your rating doesn't move `Release.rating` right away**: the overall score is recomputed
  on the API's own schedule.
- **Only numeric release IDs** work for ratings (and for the franchise/torrent lookups by
  release); the SDK rejects an alias with a `TypeError`.

## Testing code that uses an account

The SDK's own tests record live responses with VCR. If you do the same, scrub the secrets
before committing cassettes: the password in the login body, the token in the login
response and the `Authorization` header, the `_al1` cookie (the API sets it to the token
too), and the passkey and e-mail in profile, torrent and release responses. The SDK's
[`tests/conftest.py`](https://github.com/LLIJIYAPNIK/py-aniliberty/blob/main/tests/conftest.py)
is a working example.
