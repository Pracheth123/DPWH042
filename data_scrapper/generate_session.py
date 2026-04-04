"""
generate_session.py
-------------------
Run this ONCE locally to generate a Pyrogram session string.
It will prompt you for your phone number and the OTP sent by Telegram.

Usage:
    python generate_session.py

After it prints the session string, copy it into your .env file:
    TELEGRAM_SESSION_STRING=<paste here>

You will never need to log in again after this.
"""

import asyncio
import tempfile
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")

if not API_ID or not API_HASH:
    raise ValueError(
        "Set TELEGRAM_API_ID and TELEGRAM_API_HASH in your .env file first.\n"
        "Get them from https://my.telegram.org/apps"
    )


async def main():
    # Use a temp session file name (workaround for Windows :memory: SQLite bug)
    tmp_session = os.path.join(tempfile.gettempdir(), "ghostgrid_tmp_session")
    try:
        async with Client(
            name=tmp_session,
            api_id=API_ID,
            api_hash=API_HASH,
        ) as app:
            session_string = await app.export_session_string()
            print("\n" + "=" * 60)
            print("YOUR SESSION STRING (keep this secret!):")
            print("=" * 60)
            print(session_string)
            print("=" * 60)
            print(
                "\nAdd this to your .env file as:\n"
                "  TELEGRAM_SESSION_STRING=<the string above>\n"
            )
    finally:
        # Clean up temp session file
        session_file = tmp_session + ".session"
        if os.path.exists(session_file):
            os.remove(session_file)


if __name__ == "__main__":
    asyncio.run(main())
