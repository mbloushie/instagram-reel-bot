"""Makes one real API call per Instagram permission so Meta counts them as tested.
Run from the reel-bot folder:  python test_calls.py
"""
import httpx

from app import config

BASE = f"https://graph.instagram.com/{config.IG_API_VERSION}"
P = {"access_token": config.IG_ACCESS_TOKEN}


def show(label, r):
    print(f"{label}: {r.status_code} {r.text[:300]}")


with httpx.Client(timeout=30) as c:
    # instagram_business_basic
    show("basic /me", c.get(f"{BASE}/me", params={**P, "fields": "user_id,username"}))
    media = c.get(f"{BASE}/me/media", params={**P, "fields": "id"})
    show("basic /me/media", media)

    # instagram_business_manage_messages
    convs = c.get(f"{BASE}/me/conversations", params={**P, "platform": "instagram"})
    show("messages /me/conversations", convs)
    try:
        conv_id = convs.json()["data"][0]["id"]
        show("messages conversation detail",
             c.get(f"{BASE}/{conv_id}", params={**P, "fields": "messages{from,message}"}))
    except Exception:
        print("messages: no conversation found")

    # instagram_business_manage_comments
    try:
        media_id = media.json()["data"][0]["id"]
        show("comments /media/comments", c.get(f"{BASE}/{media_id}/comments", params=P))
    except Exception:
        print("comments: account has no posts, skipped")
