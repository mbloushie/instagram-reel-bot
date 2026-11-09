"""Calls to the Claude API."""
import base64
import os

import anthropic

from . import config

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY or None)

SYSTEM = f"""You are the user's personal research buddy, reached through Instagram DMs.
The user is a solo app developer. He shares Instagram reels, mostly about AI tools,
plugins, connectors, MCP servers and new releases, then chats with you about them.

When a reel arrives you get sampled frames, the audio transcript and the caption.
Reply with exactly two parts:
1. Explanation: what the video is about and the tools/products it names (exact names), in 3-5 short lines.
2. Verdict: is it useful for him or not. Use the project list below: if it genuinely helps
   one or more of his projects, say which and how in one short line each (max 3);
   otherwise write "Not useful for your projects." Do not stretch to force a match.
Do not add anything else: no accuracy check, no hook analysis, no extra tips.
Rules: reply in {config.REPLY_LANGUAGE}. Keep it short; this is a phone DM.
Plain text only - no markdown, no tables, no asterisks.
Never mix Arabic and English words on the same line; put English tool names on their own line.
For normal chat messages, just continue the conversation naturally."""


def _system() -> str:
    """SYSTEM plus the user's project list, re-read each call so edits apply without a restart."""
    try:
        with open(os.path.join(config.DATA_DIR, "projects.md"), encoding="utf-8") as f:
            projects = f.read().strip()
    except OSError:
        return SYSTEM
    return f"{SYSTEM}\n\nProject list:\n{projects}" if projects else SYSTEM


def _tools() -> list[dict] | None:
    if not config.WEB_SEARCH:
        return None
    return [{"type": config.WEB_SEARCH_TOOL_TYPE, "name": "web_search", "max_uses": 3}]


def _text_of(resp) -> str:
    return "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()


async def _create(messages: list[dict]) -> str:
    kwargs = dict(
        model=config.CLAUDE_MODEL,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=_system(),
        messages=messages,
    )
    tools = _tools()
    if tools:
        kwargs["tools"] = tools
    resp = await _client.messages.create(**kwargs)
    text = _text_of(resp) or "..."
    if resp.stop_reason == "max_tokens":
        # Never end mid-word: cut back to the last full line or sentence.
        cut = max(text.rfind("\n"), text.rfind(". "), text.rfind("؟"), text.rfind("."))
        if cut > len(text) // 2:
            text = text[: cut + 1].rstrip()
        text += "\n(cut short, ask me to continue)"
    return text


async def ask(system: str, prompt: str, max_tokens: int = 1200) -> str:
    """One-off question with its own system prompt and no chat history."""
    resp = await _client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_of(resp) or "..."


async def analyze_reel(history: list[dict], frames: list[str], transcript: str, caption: str) -> str:
    content: list[dict] = []
    for i, path in enumerate(frames):
        with open(path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        content.append({"type": "text", "text": f"Frame {i + 1}/{len(frames)}"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}})
    content.append({
        "type": "text",
        "text": (
            "New reel shared.\n"
            f"Caption/title: {caption or '(none)'}\n"
            f"Audio transcript: {transcript or '(no speech detected)'}"
        ),
    })
    msgs = list(history)
    if msgs and msgs[-1]["role"] == "user":  # keep roles alternating
        last = msgs.pop()
        content = [{"type": "text", "text": last["content"]}] + content
    return await _create(msgs + [{"role": "user", "content": content}])


async def chat(history: list[dict]) -> str:
    return await _create(history)
