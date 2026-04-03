import json
import re
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel
from schema import create_record

# Setup Telegram client
api_id = 31965153
api_hash = 'eb263f0e7e78b0a83a7a06d686ed2b89'
session_name = 'session'

client = TelegramClient(session_name, api_id, api_hash)

# 1. Define strong keywords (must indicate supply chain)
valid_keywords = [
    "shortage",
    "price increase",
    "fuel shortage",
    "diesel shortage",
    "petrol shortage",
    "export ban",
    "import restriction",
    "supply disruption",
    "delivery delay",
    "stock shortage",
    "crisis"
]

# 2. Define strict ignore list
ignore_words = [
    "job",
    "internship",
    "apply",
    "offer",
    "discount",
    "voucher",
    "gift",
    "bootcamp",
    "course",
    "join now",
    "limited time",
    "sale",
    "cashback",
    "credit card"
]

async def main():
    await client.start()
    print("Connected to Telegram.\n")

    # Auto-discover channels the user has joined
    print("Discovering your joined channels...")
    channels = []
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            channels.append(dialog)

    if not channels:
        print("[WARNING] No channels found. Make sure you have joined some Telegram channels.")
        return

    print(f"Found {len(channels)} joined channel(s):\n")
    for ch in channels:
        print(f"  - {ch.name}")
    print()

    print("Attempting to fetch messages from joined channels...\n")

    records_count = 0

    for dialog in channels:
        try:
            print(f"Resolving channel: {dialog.name}")
            entity = await client.get_entity(dialog.id)

            print(f"Fetching messages from {dialog.name}...")
            async for message in client.iter_messages(entity, limit=50):
                # Skip if message text is None
                if message.text is None:
                    continue

                text_lower = message.text.lower()

                # 3. Ignore junk first
                if any(word in text_lower for word in ignore_words):
                    continue

                # 4. Only allow strong signals
                if not any(keyword in text_lower for keyword in valid_keywords):
                    continue

                text = text_lower

                # Detect commodity
                if any(c in text for c in ["fuel", "petrol", "diesel"]):
                    commodity = "fuel"
                elif "rice" in text:
                    commodity = "rice"
                else:
                    commodity = "unknown"

                # Extract price using regex (optional)
                price = None
                price_match = re.search(r'\d+(\.\d+)?', text)
                if price_match:
                    try:
                        price = float(price_match.group())
                    except ValueError:
                        price = None

                # Create structured record using schema
                try:
                    record = create_record(
                        source="telegram",
                        commodity=commodity,
                        location="unknown",
                        text=message.text,
                        price=price,
                        signal_type="behavior",
                        confidence=0.6
                    )

                    # Print each record
                    print(json.dumps(record, indent=2))

                    # Save to data/telegram_data.json (append mode)
                    with open("data/telegram_data.json", "a", encoding="utf-8") as f:
                        f.write(json.dumps(record) + "\n")

                    records_count += 1

                except Exception as e:
                    print(f"[Schema/Save Error] {e}")

        except Exception as e:
            print(f"[Channel Error] Failed to scrape '{dialog.name}': {e}")
            print("[ERROR] Make sure you are a member of this channel.")
            continue

    print(f"\nScraping completed successfully. Total records: {records_count}")

if __name__ == "__main__":
    try:
        with client:
            client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Scraper stopped by user.")
