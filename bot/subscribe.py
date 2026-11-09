"""Checks the Instagram token and subscribes the bot account to message webhooks.
Run from the reel-bot folder:  python subscribe.py
"""
import httpx

from app import config

BASE = f"https://graph.instagram.com/{config.IG_API_VERSION}"
token = config.IG_ACCESS_TOKEN

if not token:
    raise SystemExit("IG_ACCESS_TOKEN is empty in .env")

with httpx.Client(timeout=30) as c:
    r = c.get(f"{BASE}/me", params={"fields": "user_id,username", "access_token": token})
    print("1) Token check:", r.status_code, r.text)

    r = c.post(
        f"{BASE}/me/subscribed_apps",
        params={"subscribed_fields": "messages", "access_token": token},
    )
    print("2) Subscribe:", r.status_code, r.text)

    r = c.get(f"{BASE}/me/subscribed_apps", params={"access_token": token})
    print("3) Current subscriptions:", r.status_code, r.text)
