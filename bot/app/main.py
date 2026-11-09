"""Webhook server for the Instagram reel bot."""
import hmac
import json
import logging
import os
import sqlite3
import time

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from . import config, instagram
from .handler import handle_event

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", force=True)
log = logging.getLogger("main")

app = FastAPI(title="Reel Bot")


@app.get("/")
async def health():
    return {"ok": True}


@app.get("/webhook")
async def verify(request: Request):
    """Meta calls this once when you save the webhook URL."""
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == config.IG_VERIFY_TOKEN:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verification failed")


@app.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()
    log.info("webhook received: %s", raw[:2000].decode(errors="replace"))
    if not instagram.verify_signature(raw, request.headers.get("x-hub-signature-256")):
        log.warning("signature check failed - check IG_APP_SECRET in .env")
        raise HTTPException(status_code=401, detail="bad signature")
    body = json.loads(raw or b"{}")
    for entry in body.get("entry", []):
        events = list(entry.get("messaging", []))
        # The dashboard "Test" button sends the "changes" shape instead
        for change in entry.get("changes", []):
            if change.get("field") == "messages" and isinstance(change.get("value"), dict):
                events.append(change["value"])
        for event in events:
            # Answer Meta fast (it retries slow webhooks); do the heavy work in the background.
            background.add_task(handle_event, event)
    return {"ok": True}


# ---- Live history page (open from the phone): /history?k=<HISTORY_KEY> ----
_PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.html")


def _check_key(k: str) -> None:
    want = os.getenv("HISTORY_KEY", "").strip()
    if not want or not hmac.compare_digest(k or "", want):
        raise HTTPException(status_code=404, detail="not found")


def _history_items() -> list:
    """Archived messages (survive /reset) + anything newer from the bot database."""
    archive = os.path.join(config.DATA_DIR, "history.json")
    items = []
    try:
        with open(archive, encoding="utf-8") as f:
            items = json.load(f).get("items", [])
    except Exception:
        pass
    last = max((x["i"] for x in items), default=0)
    db = sqlite3.connect("file:" + os.path.join(config.DATA_DIR, "bot.db") + "?mode=ro", uri=True)
    try:
        rows = db.execute(
            "SELECT id, role, content, created_at FROM messages WHERE id > ? ORDER BY id", (last,)
        ).fetchall()
    finally:
        db.close()
    new = [{"i": r[0], "r": "u" if r[1] == "user" else "a", "t": r[2], "ts": r[3]} for r in rows]
    if new:
        items += new
        try:
            with open(archive + ".tmp", "w", encoding="utf-8") as f:
                json.dump({"updated_at": time.time(), "items": items}, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(archive + ".tmp", archive)
        except Exception:
            log.exception("could not update history archive")
    return items


@app.get("/history")
async def history_page(k: str = ""):
    _check_key(k)
    with open(_PAGE, encoding="utf-8") as f:
        return HTMLResponse(f.read(), headers={"Cache-Control": "no-store"})


@app.get("/history/data")
async def history_data(k: str = ""):
    _check_key(k)
    items = _history_items()
    updated = max((x["ts"] for x in items), default=0)
    return JSONResponse({"updated_at": updated, "items": items}, headers={"Cache-Control": "no-store"})
