import os
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# Instagram / Meta
IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
IG_APP_SECRET = os.getenv("IG_APP_SECRET", "")
IG_VERIFY_TOKEN = os.getenv("IG_VERIFY_TOKEN", "")
IG_API_VERSION = os.getenv("IG_API_VERSION", "v25.0")
# Your personal account's Instagram-scoped ID. Leave empty on first run,
# send the bot a message, and copy the ID it prints in the logs.
ALLOWED_SENDER_ID = os.getenv("ALLOWED_SENDER_ID", "")

# Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1500"))
WEB_SEARCH = _bool("WEB_SEARCH", False)
WEB_SEARCH_TOOL_TYPE = os.getenv("WEB_SEARCH_TOOL_TYPE", "web_search_20250305")
REPLY_LANGUAGE = os.getenv("REPLY_LANGUAGE", "Arabic")

# Claude Code routine that opens a new research session per reel
ROUTINE_FIRE_URL = os.getenv("ROUTINE_FIRE_URL", "").strip()
ROUTINE_TOKEN = os.getenv("ROUTINE_TOKEN", "").strip()

# Video processing
MAX_FRAMES = int(os.getenv("MAX_FRAMES", "16"))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "768"))
TRANSCRIBE = _bool("TRANSCRIBE", True)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# Storage
DATA_DIR = os.getenv("DATA_DIR", "./data")
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "30"))
