"""Read-aloud for AI Teacher answers (the computer's voices, via pyttsx3).

It speaks on the machine running StudyGenie, so it's offered in the
desktop window only, not to phones using the web version."""

import re
import threading

from .deps import pyttsx3

_lock = threading.Lock()
_engine = None


def available():
    return pyttsx3 is not None


def plain_text(markdown):
    """Strips Markdown symbols so the voice doesn't read out '#' and '*'."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    text = re.sub(r"[#*_`>|]+", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 175)
    return _engine


def speak(text):
    """Reads `text` aloud on a background thread. Returns False if it can't."""
    if not available() or not text:
        return False

    def work():
        with _lock:
            try:
                engine = _get_engine()
                engine.say(plain_text(text))
                engine.runAndWait()
            except Exception:
                pass  # no voice installed, audio busy…: reading aloud is a nicety

    threading.Thread(target=work, daemon=True).start()
    return True


def stop():
    if _engine is not None:
        try:
            _engine.stop()
        except Exception:
            pass
