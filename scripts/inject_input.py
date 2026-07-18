#!/usr/bin/env python3
"""Type text into the Claude Code input box and submit it.

Usage: inject_input.py <method> <text-file>

Runs detached from the hook so injection lands after the blocked prompt has
been processed and Claude Code is back at (or queues onto) the input box.
Text is wrapped in bracketed-paste markers so multi-line prompts don't
submit line by line; a trailing carriage return submits the prompt.
"""

import os
import subprocess
import sys
import time


def inject_tmux(text):
    pane = os.environ["TMUX_PANE"]
    subprocess.run(
        ["tmux", "load-buffer", "-b", "claude-interpreter", "-"],
        input=text.encode("utf-8"),
        check=True,
    )
    subprocess.run(
        ["tmux", "paste-buffer", "-p", "-d", "-b", "claude-interpreter", "-t", pane],
        check=True,
    )
    subprocess.run(["tmux", "send-keys", "-t", pane, "Enter"], check=True)


def inject_tiocsti(text):
    import fcntl
    import termios

    payload = b"\x1b[200~" + text.encode("utf-8") + b"\x1b[201~" + b"\r"
    fd = os.open("/dev/tty", os.O_RDWR)
    try:
        for i in range(len(payload)):
            fcntl.ioctl(fd, termios.TIOCSTI, payload[i : i + 1])
    finally:
        os.close(fd)


def main():
    method, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return
    # Let the hook finish and the blocked turn settle first.
    time.sleep(0.5)
    if method == "tmux":
        inject_tmux(text)
    elif method == "tiocsti":
        inject_tiocsti(text)


if __name__ == "__main__":
    main()
