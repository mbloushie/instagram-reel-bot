"""Instagram API with Instagram Login: signature check, download, send."""
import glob
import hashlib
import hmac
import logging
import os
import subprocess
import sys

import httpx

from . import config

log = logging.getLogger("instagram")
GRAPH = "https://graph.instagram.com"
MAX_CHUNK = 900  # Instagram DM text limit is ~1000 bytes (UTF-8); stay under it


def verify_signature(raw_body: bytes, header: str | None) -> bool:
    if not config.IG_APP_SECRET:
        log.warning("IG_APP_SECRET not set - skipping signature check (dev only)")
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(config.IG_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


async def download(url: str, dest: str) -> None:
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)


def looks_like_html(path: str) -> bool:
    """A shared reel can arrive as its instagram.com page link; the download is then a web page."""
    with open(path, "rb") as f:
        head = f.read(512).lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<head" in head


def download_with_ytdlp(page_url: str, dest: str) -> None:
    """Fetch the actual video behind an instagram.com reel/post link."""
    out_dir = os.path.dirname(dest)
    template = os.path.join(out_dir, "ytdlp.%(ext)s")
    # Instagram blocks anonymous downloads; a cookies.txt from a logged-in account fixes that.
    cookies = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    extra = ["--cookies", cookies] if os.path.exists(cookies) else []
    if not extra:
        log.warning("no cookies.txt found; Instagram may block the download")
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "--no-playlist", *extra,
         "-f", "best[ext=mp4]/best", "-o", template, page_url],
        check=True, capture_output=True, timeout=180,
    )
    found = glob.glob(os.path.join(out_dir, "ytdlp.*"))
    if not found:
        raise RuntimeError("yt-dlp produced no file")
    os.replace(found[0], dest)


def _nbytes(s: str) -> int:
    return len(s.encode("utf-8"))


def _chunks(text: str) -> list[str]:
    # Instagram cuts a DM at about 1000 bytes, not characters: Arabic is 2 bytes per letter,
    # so measure in UTF-8 bytes or the tail of the message gets chopped off.
    parts, buf = [], ""
    for para in text.split("\n"):
        line = para + "\n"
        while _nbytes(line) > MAX_CHUNK:
            if buf:
                parts.append(buf.rstrip())
                buf = ""
            cut = len(line)
            while _nbytes(line[:cut]) > MAX_CHUNK:
                cut -= 1
            space = line.rfind(" ", 0, cut)
            if space > cut // 2:
                cut = space + 1  # break at a word, not mid-word
            parts.append(line[:cut].rstrip())
            line = line[cut:]
        if _nbytes(buf) + _nbytes(line) > MAX_CHUNK:
            parts.append(buf.rstrip())
            buf = ""
        buf += line
    if buf.strip():
        parts.append(buf.rstrip())
    return [p for p in parts if p.strip()]


async def send_text(recipient_id: str, text: str) -> None:
    url = f"{GRAPH}/{config.IG_API_VERSION}/me/messages"
    headers = {"Authorization": f"Bearer {config.IG_ACCESS_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        for part in _chunks(text):
            r = await client.post(
                url,
                headers=headers,
                json={"recipient": {"id": recipient_id}, "message": {"text": part}},
            )
            if r.status_code >= 400:
                log.error("send failed %s: %s", r.status_code, r.text)


async def post_media_urls(media_id: str) -> tuple[list[str], str]:
    """Ask the Graph API for every slide of a shared post. Returns (media urls, permalink).
    Empty list if Instagram won't give us the post (common for other people's posts)."""
    if not media_id:
        return [], ""
    url = f"{GRAPH}/{config.IG_API_VERSION}/{media_id}"
    params = {
        "fields": "permalink,media_type,media_url,children{media_type,media_url}",
        "access_token": config.IG_ACCESS_TOKEN,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url, params=params)
        if r.status_code != 200:
            log.info("graph lookup for post %s refused: %s", media_id, r.text[:200])
            return [], ""
        data = r.json()
        children = (data.get("children") or {}).get("data") or []
        urls = [c["media_url"] for c in children if c.get("media_url")]
        if not urls and data.get("media_url"):
            urls = [data["media_url"]]
        return urls, data.get("permalink", "")
    except Exception:
        log.exception("graph lookup failed")
        return [], ""


def _cookies_file() -> str | None:
    c = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cookies.txt")
    return c if os.path.exists(c) else None


def download_post_with_gallerydl(page_url: str, out_dir: str) -> list[str]:
    """Download every photo/video of an instagram.com post (carousels included)."""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [sys.executable, "-m", "gallery_dl", "-q", "-D", out_dir,
           "-f", "{num:>03}.{extension}"]
    cookies = _cookies_file()
    if cookies:
        cmd += ["--cookies", cookies]
    else:
        log.warning("no cookies.txt found; Instagram may block the download")
    subprocess.run(cmd + [page_url], check=True, capture_output=True, timeout=240)
    files = sorted(f for f in glob.glob(os.path.join(out_dir, "*")) if os.path.isfile(f))
    if not files:
        raise RuntimeError("gallery-dl produced no files")
    return files
