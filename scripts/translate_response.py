#!/usr/bin/env python3
"""Stop hook: translate Claude's final English answer into Korean.

Only runs when the last user prompt was Korean (flag set by the
UserPromptSubmit hook). Shows the translation to the user via
systemMessage without blocking the turn.
"""

import json
import os
import sys

import interpreter_common as ic


def last_assistant_text_from_transcript(path):
    if not path or not os.path.exists(path):
        return ""
    text = ""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content") or []
                parts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                if parts:
                    text = "\n".join(parts)
    except OSError:
        return ""
    return text


def main():
    if ic.is_guarded():
        return
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return

    session_id = data.get("session_id") or "unknown"
    if not ic.is_korean_session(session_id):
        return

    message = data.get("last_assistant_message") or ""
    if not message:
        message = last_assistant_text_from_transcript(data.get("transcript_path"))
    message = message.strip()
    if not message:
        return

    # Already (mostly) Korean — nothing to do.
    if ic.korean_ratio(message) > 0.3:
        return

    translation = ic.translate(message, ic.TO_KOREAN, timeout=110)
    if translation is None:
        return

    print(json.dumps({"systemMessage": "🌐 한국어 번역\n\n" + translation}))


if __name__ == "__main__":
    main()
