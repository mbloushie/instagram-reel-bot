"""SQLite storage: one ongoing conversation per sender + saved reel summaries."""
import json
import os
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
os.makedirs(config.DATA_DIR, exist_ok=True)
_db = sqlite3.connect(os.path.join(config.DATA_DIR, "bot.db"), check_same_thread=False)
_db.executescript(
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS reels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender TEXT NOT NULL,
        reel_id TEXT,
        title TEXT,
        transcript TEXT,
        summary TEXT,
        created_at REAL NOT NULL
    );
    CREATE TABLE IF NOT EXISTS processed (
        mid TEXT PRIMARY KEY
    );
    """
)
_db.commit()


def already_processed(mid: str) -> bool:
    """Returns True if seen before; otherwise marks it as seen."""
    if not mid:
        return False
    with _lock:
        try:
            _db.execute("INSERT INTO processed (mid) VALUES (?)", (mid,))
            _db.commit()
            return False
        except sqlite3.IntegrityError:
            return True


def add_message(sender: str, role: str, content: str) -> None:
    with _lock:
        _db.execute(
            "INSERT INTO messages (sender, role, content, created_at) VALUES (?, ?, ?, ?)",
            (sender, role, content, time.time()),
        )
        _db.commit()


def history(sender: str) -> list[dict]:
    """Last N messages as Claude-style turns, roles merged so they alternate."""
    with _lock:
        rows = _db.execute(
            "SELECT role, content FROM messages WHERE sender = ? ORDER BY id DESC LIMIT ?",
            (sender, config.HISTORY_LIMIT),
        ).fetchall()
    rows.reverse()
    turns: list[dict] = []
    for role, content in rows:
        if turns and turns[-1]["role"] == role:
            turns[-1]["content"] += "\n\n" + content
        else:
            turns.append({"role": role, "content": content})
    while turns and turns[0]["role"] != "user":
        turns.pop(0)
    return turns


def save_reel(sender: str, reel_id: str, title: str, transcript: str, summary: str) -> None:
    with _lock:
        _db.execute(
            "INSERT INTO reels (sender, reel_id, title, transcript, summary, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (sender, reel_id, title, transcript, summary, time.time()),
        )
        _db.commit()


def append_reel_log(url: str, caption: str, note: str, analysis: str, session_url: str | None) -> None:
    """One running markdown file with every reel, newest at the bottom."""
    entry = (
        f"\n\n---\n\n## {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"- Reel: {url or '(no link)'}\n"
        f"- Claude research session: {session_url or '(none)'}\n"
        f"- Your note: {note or '(none)'}\n"
        f"- Caption: {(caption or '(none)')[:300]}\n\n"
        f"{analysis}\n"
    )
    with _lock, open(os.path.join(config.DATA_DIR, "reels-log.md"), "a", encoding="utf-8") as f:
        f.write(entry)


def reset(sender: str) -> None:
    with _lock:
        _db.execute("DELETE FROM messages WHERE sender = ?", (sender,))
        _db.commit()


def export_reels(sender: str) -> str:
    with _lock:
        rows = _db.execute(
            "SELECT reel_id, title, summary, created_at FROM reels WHERE sender = ? ORDER BY id",
            (sender,),
        ).fetchall()
    return json.dumps(
        [dict(reel_id=r[0], title=r[1], summary=r[2], created_at=r[3]) for r in rows],
        ensure_ascii=False,
        indent=2,
    )
