#!/usr/bin/env python3
"""UserPromptSubmit hook: keep Korean out of context, feed Claude English.

Default ("replace" mode) flow:
1. A Korean prompt is translated to English with a small model.
2. The Korean prompt is blocked — Claude Code erases blocked prompts from
   context, so the Korean text never reaches the model.
3. A detached helper types the English translation into the input box and
   submits it (tmux paste, or TIOCSTI tty injection; clipboard as a last
   resort). The re-submitted English prompt matches the pending file and
   passes straight through.

"context" mode (CLAUDE_INTERPRETER_MODE=context) instead lets the Korean
prompt through and attaches the English translation as additionalContext.
"""

import json
import os
import shutil
import subprocess
import sys

import interpreter_common as ic

INJECTOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inject_input.py")


def pick_injection_method():
    if os.environ.get("TMUX") and os.environ.get("TMUX_PANE") and shutil.which("tmux"):
        return "tmux"
    try:
        import termios  # noqa: F401

        if hasattr(termios, "TIOCSTI"):
            fd = os.open("/dev/tty", os.O_RDWR)
            os.close(fd)
            return "tiocsti"
    except OSError:
        pass
    return None


def spawn_injector(method, session_id):
    with open(os.devnull, "r+b") as devnull:
        subprocess.Popen(
            [sys.executable, INJECTOR, method, ic.pending_path(session_id)],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull,
            start_new_session=True,
        )


def copy_to_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def block(reason):
    print(json.dumps({"decision": "block", "reason": reason}))


def main():
    if ic.is_guarded():
        return
    try:
        data = json.load(sys.stdin)
    except (ValueError, OSError):
        return

    prompt = data.get("prompt") or ""
    session_id = data.get("session_id") or "unknown"

    # Leave slash commands alone.
    if prompt.lstrip().startswith("/"):
        return

    # Our own re-injected English prompt: let it through, stay in Korean mode.
    pending = ic.read_pending(session_id)
    if pending is not None and prompt.strip() == pending.strip():
        ic.clear_pending(session_id)
        return

    if not ic.contains_korean(prompt):
        ic.set_korean_session(session_id, False)
        ic.clear_pending(session_id)
        return

    translation = ic.translate(prompt, ic.TO_ENGLISH, timeout=45)
    if translation is None:
        # Fail open: losing the message would be worse than Korean in context.
        return

    ic.set_korean_session(session_id, True)

    if ic.MODE == "context":
        context = (
            "[claude-interpreter] The user's prompt above was written in "
            "Korean. English translation:\n\n<english_translation>\n"
            + translation
            + "\n</english_translation>\n\n"
            "Treat this English translation as the canonical version of the "
            "user's request and work from it. Write your response in "
            "English; a separate hook will show the user a Korean "
            "translation of it."
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": context,
                    }
                }
            )
        )
        return

    ic.write_pending(session_id, translation)
    method = pick_injection_method()
    if method:
        spawn_injector(method, session_id)
        block("🌐 한국어 프롬프트를 지우고 영어 번역으로 다시 제출합니다:\n\n" + translation)
    else:
        copied = copy_to_clipboard(translation)
        hint = (
            "클립보드에 복사했습니다. 붙여넣기(Cmd+V) 후 제출하세요."
            if copied
            else "아래 번역을 직접 붙여넣어 제출하세요."
        )
        block("🌐 영어 번역 (자동 입력 불가 환경) — " + hint + "\n\n" + translation)


if __name__ == "__main__":
    main()
