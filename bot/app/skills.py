"""Find, review and install Claude skills from GitHub, driven by Instagram commands.

Safety rules (do not loosen):
- Only the allowed sender can trigger this, and only with a typed command (/find, /review, /install).
  Reel captions or transcripts can never start it.
- Downloads go to a quarantine folder. Nothing downloaded is ever executed here.
- /install copies skill folders (those with a SKILL.md) into ~/.claude/skills, and only for a repo that
  was reviewed first and not rated "avoid".
"""
import io
import json
import os
import re
import shutil
import zipfile

import httpx

from . import config

QUARANTINE = os.path.join(config.DATA_DIR, "quarantine")
STATE = os.path.join(config.DATA_DIR, "skills_state.json")
SKILLS_DIR = os.path.expanduser("~/.claude/skills")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
MAX_ZIP_BYTES = 40 * 1024 * 1024
MAX_FILES = 3000
UA = {"User-Agent": "reel-bot", "Accept": "application/vnd.github+json"}

RISKY = re.compile(
    r"curl |wget |Invoke-WebRequest|Invoke-Expression|\biex\b|\beval\(|child_process|subprocess|os\.system"
    r"|postinstall|preinstall|base64 -d|FromBase64String|\.ssh|\.aws|id_rsa|credentials|api[_-]?key|Set-ExecutionPolicy",
    re.I,
)
BINARY_EXT = {".exe", ".dll", ".bat", ".cmd", ".msi", ".scr", ".vbs", ".jar", ".so", ".dylib"}
SCRIPT_EXT = {".sh", ".ps1", ".py", ".js", ".mjs", ".ts", ".rb"}


def _load() -> dict:
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(state: dict) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _slug(repo: str) -> str:
    return repo.replace("/", "__")


async def search(query: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30, headers=UA) as c:
        r = await c.get(
            "https://api.github.com/search/repositories",
            params={"q": query, "per_page": 5, "sort": "stars"},
        )
        r.raise_for_status()
    items = [
        {
            "repo": i["full_name"],
            "stars": i["stargazers_count"],
            "updated": (i.get("pushed_at") or "")[:10],
            "desc": (i.get("description") or "")[:140],
        }
        for i in r.json().get("items", [])
    ]
    state = _load()
    state["last_find"] = items
    _save(state)
    return items


def resolve(arg: str) -> str | None:
    """Accepts a number from the last /find list, or owner/repo."""
    arg = arg.strip().strip("<>")
    arg = re.sub(r"^https?://github\.com/", "", arg).rstrip("/")
    if arg.isdigit():
        items = _load().get("last_find", [])
        i = int(arg) - 1
        return items[i]["repo"] if 0 <= i < len(items) else None
    return arg if REPO_RE.match(arg) else None


async def download(repo: str) -> str:
    """Download the repo zip into quarantine and extract it safely. Returns the folder."""
    dest = os.path.join(QUARANTINE, _slug(repo))
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    buf = io.BytesIO()
    async with httpx.AsyncClient(timeout=120, headers=UA, follow_redirects=True) as c:
        async with c.stream("GET", f"https://api.github.com/repos/{repo}/zipball") as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():
                buf.write(chunk)
                if buf.tell() > MAX_ZIP_BYTES:
                    raise ValueError("repo is bigger than 40 MB, not downloading")
    with zipfile.ZipFile(buf) as z:
        names = z.namelist()
        if len(names) > MAX_FILES:
            raise ValueError("repo has too many files")
        root = os.path.realpath(dest)
        for info in z.infolist():
            target = os.path.realpath(os.path.join(dest, info.filename))
            if not (target == root or target.startswith(root + os.sep)):
                raise ValueError("zip tries to write outside the folder, refusing")
        z.extractall(dest)
    inner = [d for d in os.listdir(dest) if os.path.isdir(os.path.join(dest, d))]
    return os.path.join(dest, inner[0]) if len(inner) == 1 else dest


def scan(folder: str) -> dict:
    """Static look only: file types, SKILL.md locations, and risky-looking lines. Nothing is run."""
    skill_dirs, binaries, scripts, hits, total = [], [], 0, [], 0
    for base, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for name in files:
            total += 1
            path = os.path.join(base, name)
            rel = os.path.relpath(path, folder)
            ext = os.path.splitext(name)[1].lower()
            if name == "SKILL.md":
                skill_dirs.append(os.path.relpath(base, folder))
            if ext in BINARY_EXT:
                binaries.append(rel)
            if ext in SCRIPT_EXT:
                scripts += 1
            if ext in SCRIPT_EXT | {".json", ".md", ".txt", ".yml", ".yaml", ".toml"} and os.path.getsize(path) < 400_000:
                try:
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        for n, line in enumerate(f, 1):
                            if RISKY.search(line) and len(hits) < 25:
                                hits.append(f"{rel}:{n}: {line.strip()[:110]}")
                except OSError:
                    pass
    return {"files": total, "skill_dirs": skill_dirs, "binaries": binaries[:10], "scripts": scripts, "hits": hits}


def skill_head(folder: str, skill_dir: str) -> str:
    try:
        with open(os.path.join(folder, skill_dir, "SKILL.md"), encoding="utf-8", errors="ignore") as f:
            return f.read(1500)
    except OSError:
        return ""


def mark_reviewed(repo: str, folder: str, verdict: str) -> None:
    state = _load()
    state.setdefault("reviewed", {})[repo] = {"folder": folder, "verdict": verdict}
    _save(state)


def install(repo: str) -> str:
    info = _load().get("reviewed", {}).get(repo)
    if not info:
        return f"Review it first: /review {repo}"
    if info["verdict"] == "avoid":
        return "My review rated this one as avoid, so I won't install it."
    folder = info["folder"]
    if not os.path.isdir(folder):
        return f"Review folder is gone. Run /review {repo} again."
    skills = scan(folder)["skill_dirs"]
    if not skills:
        return "No SKILL.md in this repo, so there is no skill to install."
    os.makedirs(SKILLS_DIR, exist_ok=True)
    done, skipped = [], []
    for rel in skills:
        src = os.path.normpath(os.path.join(folder, rel))
        name = re.sub(r"[^A-Za-z0-9_.-]", "-", os.path.basename(src) if rel != "." else repo.split("/")[1])
        dst = os.path.join(SKILLS_DIR, name)
        if os.path.exists(dst):
            skipped.append(name)
            continue
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "node_modules"))
        done.append(name)
    msg = "Installed: " + (", ".join(done) or "nothing")
    if skipped:
        msg += "\nAlready there, left alone: " + ", ".join(skipped)
    return msg + "\nOpen a new Claude Code session to use them."
