"""Frame and audio extraction with ffmpeg."""
import glob
import os
import subprocess

from . import config


def duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def extract_frames(path: str, out_dir: str) -> list[str]:
    """Evenly spaced frames across the whole video, capped at MAX_FRAMES."""
    os.makedirs(out_dir, exist_ok=True)
    dur = duration(path) or 30.0
    n = max(1, config.MAX_FRAMES)
    interval = max(dur / n, 0.5)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", path,
         "-vf", f"fps=1/{interval:.3f},scale={config.FRAME_WIDTH}:-2",
         "-q:v", "4", os.path.join(out_dir, "f_%03d.jpg")],
        check=True,
    )
    frames = sorted(glob.glob(os.path.join(out_dir, "f_*.jpg")))
    if len(frames) > n:
        step = len(frames) / n
        frames = [frames[int(i * step)] for i in range(n)]
    return frames


def is_video(path: str) -> bool:
    """True for a real video (has duration > 1s), False for a still image."""
    try:
        return duration(path) > 1.0
    except subprocess.CalledProcessError:
        return False


def image_as_frame(path: str, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, "f_001.jpg")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", path, "-frames:v", "1",
         "-vf", f"scale={config.FRAME_WIDTH}:-2", "-q:v", "4", dest],
        check=True,
    )
    return [dest]


def extract_audio(path: str, dest: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", path, "-vn", "-ac", "1", "-ar", "16000", dest],
        capture_output=True,
    )
    return r.returncode == 0 and os.path.exists(dest) and os.path.getsize(dest) > 1000
