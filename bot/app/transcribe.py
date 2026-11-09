"""Local speech-to-text with faster-whisper (no extra API key)."""
import logging

from . import config

log = logging.getLogger("transcribe")
_model = None


def _load_wav(path: str):
    """Read the 16 kHz mono wav ourselves; faster-whisper's own decoder (PyAV) is broken here."""
    import wave

    import numpy as np

    with wave.open(path, "rb") as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(audio_path: str) -> str:
    global _model
    if not config.TRANSCRIBE:
        return ""
    try:
        if _model is None:
            from faster_whisper import WhisperModel
            _model = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
        segments, info = _model.transcribe(_load_wav(audio_path), vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        log.info("transcribed %d chars (lang=%s)", len(text), info.language)
        return text
    except Exception:
        log.exception("transcription failed")
        return ""
