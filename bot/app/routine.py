"""Starts a new Claude research session (Claude Code routine) for a shared reel."""
import logging

import httpx

from . import config

log = logging.getLogger("routine")


async def start_research(caption: str, transcript: str, analysis: str, note: str) -> str | None:
    """Returns the claude.ai session URL, or None if not configured / failed."""
    if not (config.ROUTINE_FIRE_URL and config.ROUTINE_TOKEN):
        return None
    text = (
        f"User's note: {note or '(none)'}\n\n"
        f"Reel caption:\n{caption or '(none)'}\n\n"
        f"Audio transcript:\n{transcript or '(no speech detected)'}\n\n"
        f"Bot's first analysis (based on the video frames):\n{analysis}"
    )[:60000]
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                config.ROUTINE_FIRE_URL,
                headers={
                    "Authorization": f"Bearer {config.ROUTINE_TOKEN}",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            )
        if r.status_code != 200:
            log.error("routine fire failed %s: %s", r.status_code, r.text[:300])
            return None
        return r.json().get("claude_code_session_url")
    except Exception:
        log.exception("routine fire error")
        return None
