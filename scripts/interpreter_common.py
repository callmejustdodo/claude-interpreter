"""Shared helpers for the tongyeok hooks."""

import os
import re
import subprocess
import tempfile

# Set on child `claude -p` calls so our own hooks never fire recursively.
GUARD_ENV = "TONGYEOK_ACTIVE"

MODEL = os.environ.get("TONGYEOK_MODEL", "claude-haiku-4-5-20251001")

# "replace": block the Korean prompt (erasing it from context) and re-inject
#            the English translation into the input box.
# "context": keep the Korean prompt and inject the English translation as
#            additionalContext (Korean stays in context; no injection hacks).
MODE = os.environ.get("TONGYEOK_MODE", "replace")

HANGUL_RE = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")

# Keep hook latency and translation cost bounded.
MAX_CHARS = 12000

TO_ENGLISH = (
    "You are a professional Korean-to-English translator for software "
    "engineering conversations. Translate the following Korean text into "
    "natural English. Keep code blocks, commands, file paths, identifiers, "
    "URLs, and already-English words exactly as they are. Output ONLY the "
    "translation, with no commentary.\n\n"
)

TO_KOREAN = (
    "You are a professional English-to-Korean translator for software "
    "engineering conversations. Translate the following English text into "
    "natural Korean, keeping the original markdown structure. Keep code "
    "blocks, commands, file paths, identifiers, and URLs exactly as they "
    "are; keep common technical terms in English where Korean developers "
    "normally would. Output ONLY the translation, with no commentary.\n\n"
)


def is_guarded():
    return os.environ.get(GUARD_ENV) == "1"


def contains_korean(text):
    return bool(HANGUL_RE.search(text))


def korean_ratio(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    hangul = sum(1 for c in letters if HANGUL_RE.match(c))
    return hangul / len(letters)


def translate(text, instruction, timeout=90):
    """Translate via `claude -p` on a small model. Returns None on failure."""
    text = text[:MAX_CHARS]
    env = dict(os.environ)
    env[GUARD_ENV] = "1"
    try:
        result = subprocess.run(
            [
                "claude",
                "-p",
                instruction + text,
                "--model",
                MODEL,
                "--settings",
                '{"disableAllHooks": true}',
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    return out or None


def state_dir():
    d = os.path.join(tempfile.gettempdir(), "tongyeok")
    os.makedirs(d, exist_ok=True)
    return d


def session_flag_path(session_id):
    return os.path.join(state_dir(), "%s.ko" % session_id)


def pending_path(session_id):
    return os.path.join(state_dir(), "%s.pending" % session_id)


def set_korean_session(session_id, on):
    path = session_flag_path(session_id)
    if on:
        with open(path, "w") as f:
            f.write("1")
    else:
        _remove(path)


def is_korean_session(session_id):
    return os.path.exists(session_flag_path(session_id))


def write_pending(session_id, text):
    with open(pending_path(session_id), "w", encoding="utf-8") as f:
        f.write(text)


def read_pending(session_id):
    try:
        with open(pending_path(session_id), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def clear_pending(session_id):
    _remove(pending_path(session_id))


def _remove(path):
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
