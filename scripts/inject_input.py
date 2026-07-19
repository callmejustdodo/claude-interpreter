#!/usr/bin/env python3
"""Type text into the Claude Code input box and submit it.

Usage: inject_input.py <method> <text-file>

Runs detached from the hook so injection lands after the blocked prompt has
been processed and Claude Code is back at (or queues onto) the input box.
Text is wrapped in bracketed-paste markers so multi-line prompts don't
submit line by line; a trailing Enter submits the prompt.
"""

import json
import os
import subprocess
import sys
import time

BRACKETED = "\x1b[200~%s\x1b[201~"


def inject_cmux(text):
    cli = os.environ.get("CMUX_BUNDLED_CLI_PATH", "cmux")
    env = dict(os.environ, CMUX_QUIET="1")
    out = subprocess.run([cli, "identify"], capture_output=True, text=True, env=env)
    caller = (json.loads(out.stdout).get("caller") or {}) if out.returncode == 0 else {}
    target = []
    if caller.get("surface_ref"):
        target += ["--surface", caller["surface_ref"]]
    elif caller.get("workspace_ref"):
        target += ["--workspace", caller["workspace_ref"]]
    if caller.get("window_ref"):
        target += ["--window", caller["window_ref"]]
    subprocess.run([cli, "send", *target, BRACKETED % text], check=True, env=env)
    subprocess.run([cli, "send-key", *target, "enter"], check=True, env=env)


def inject_tmux(text):
    pane = os.environ["TMUX_PANE"]
    subprocess.run(
        ["tmux", "load-buffer", "-b", "tongyeok", "-"],
        input=text.encode("utf-8"),
        check=True,
    )
    subprocess.run(
        ["tmux", "paste-buffer", "-p", "-d", "-b", "tongyeok", "-t", pane],
        check=True,
    )
    subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=True)


def inject_tiocsti(text):
    import fcntl
    import termios

    payload = (BRACKETED % text).encode("utf-8") + b"\r"
    fd = os.open("/dev/tty", os.O_RDWR)
    try:
        for i in range(len(payload)):
            fcntl.ioctl(fd, termios.TIOCSTI, payload[i : i + 1])
    finally:
        os.close(fd)


def inject_osascript(text):
    """Paste via System Events: set clipboard, Cmd+V, Enter, restore clipboard.

    Types into the frontmost window, so this is a last resort before the
    plain-clipboard fallback. If it fails, the translation is left on the
    clipboard, which matches what the hook's fallback message promises.
    """
    old = subprocess.run(["pbpaste"], capture_output=True).stdout
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
        check=True,
        capture_output=True,
    )
    time.sleep(0.4)
    subprocess.run(
        ["osascript", "-e", "tell application \"System Events\" to key code 36"],
        check=True,
        capture_output=True,
    )
    time.sleep(0.2)
    subprocess.run(["pbcopy"], input=old)


METHODS = {
    "cmux": inject_cmux,
    "tmux": inject_tmux,
    "tiocsti": inject_tiocsti,
    "osascript": inject_osascript,
}


def main():
    method, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return
    # Let the hook finish and the blocked turn settle first.
    time.sleep(0.5)
    METHODS[method](text)


if __name__ == "__main__":
    main()
