"""Logging a device in with a one-time code (OTP) — the "enter this code on the site" flow.

Typing a password on a TV or a console is painful, so the API lets such a device log in with
a short code instead:

1. the device asks for a code (no session needed) and shows it;
2. the user enters it on a device where they are already logged in, which accepts it;
3. the device exchanges the accepted code for its own session.

Here both "devices" are AniLiberty clients in one script. Run it with an account's
credentials in ANILIBERTY_LOGIN / ANILIBERTY_PASSWORD (the "phone" logs in with them).
"""

import asyncio
import os
import uuid

from aniliberty import AniLiberty, NotFoundError, ServerError


async def main() -> None:
    # A device keeps one ID of its own (any string; a UUID it stores is a good choice) and
    # passes the same value to otp.get() and otp.login().
    device_id = str(uuid.uuid4())

    async with AniLiberty() as tv, AniLiberty() as phone:
        # 1. The TV gets a code. It's a string of 6 digits — keep it a string, it can start
        #    with 0 — and lives about 5 minutes. Asking again for the same device_id while
        #    it's alive returns the same code.
        issued = await tv.auth.otp.get(device_id=device_id)
        code = issued.otp.code
        print(f"Code: {len(code)} digits, expires in about {issued.remaining_time:.0f} s")
        print("Accepted by anyone yet:", issued.otp.user_id is not None)

        # Trying to log in before the code is accepted fails — with a 500 from the API
        # (the spec promises a 401). It's a POST, so the SDK doesn't retry it.
        try:
            await tv.auth.otp.login(code=code, device_id=device_id)
        except ServerError as error:
            print(f"Before accepting: HTTP {error.status_code}")

        # 2. The user enters the code on the phone, which has a session.
        await phone.auth.login(
            login=os.environ["ANILIBERTY_LOGIN"], password=os.environ["ANILIBERTY_PASSWORD"]
        )
        await phone.auth.otp.accept(code)
        print("Phone accepted the code")

        # 3. The TV logs in with the accepted code and gets its own session token, stored on
        #    the TV client. The SDK sends this request without a token: the API refuses an
        #    OTP login from a client that is already logged in.
        await tv.auth.otp.login(code=code, device_id=device_id)
        tv_profile = await tv.me.profile()
        phone_profile = await phone.me.profile()
        print("TV is logged in to the phone's account:", tv_profile.id == phone_profile.id)
        print("Separate sessions:", tv.token != phone.token)

        # A code logs in only once.
        async with AniLiberty() as another:
            try:
                await another.auth.otp.login(code=code, device_id=device_id)
            except NotFoundError:
                print("Second login with the same code: NotFoundError")

        # Each device logs out of its own session; the other one stays logged in until it
        # does too.
        await tv.auth.logout()
        print("Phone still logged in after the TV logged out:", (await phone.me.profile()).id > 0)
        await phone.auth.logout()


if __name__ == "__main__":
    asyncio.run(main())

# Expected output (real run against the live API, 2026-10-16):
#
# Code: 6 digits, expires in about 299 s
# Accepted by anyone yet: False
# Before accepting: HTTP 500
# Phone accepted the code
# TV is logged in to the phone's account: True
# Separate sessions: True
# Second login with the same code: NotFoundError
# Phone still logged in after the TV logged out: True
