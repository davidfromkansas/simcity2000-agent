"""xdotool wrappers for mouse and keyboard input into DOSBox-X.

SimCity 2000 polls the DOS mouse driver, so instantaneous X clicks are easy to
miss: every press is held for a short moment and every move is followed by a
settle delay. DOSBox-X runs with `mouse_emulation = never`, which makes the
DOS cursor sit exactly where the X pointer is.
"""
from __future__ import annotations

import os
import subprocess
import time

HOLD = float(os.environ.get("INPUT_HOLD_SECONDS", "0.15"))
SETTLE = float(os.environ.get("INPUT_SETTLE_SECONDS", "0.2"))
W, H = 640, 480


def _xdo(*args: str) -> None:
    subprocess.run(["xdotool", *args], check=True, timeout=15)


def _clamp(x: float, y: float) -> tuple[int, int]:
    return max(0, min(W - 1, int(round(x)))), max(0, min(H - 1, int(round(y))))


def window_id() -> str | None:
    out = subprocess.run(
        ["xdotool", "search", "--class", "dosbox"], capture_output=True, text=True, timeout=10
    ).stdout.split()
    return out[0] if out else None


def focus() -> None:
    wid = window_id()
    if wid:
        subprocess.run(["xdotool", "windowfocus", "--sync", wid], timeout=10, check=False)


def move(x: float, y: float) -> None:
    x, y = _clamp(x, y)
    _xdo("mousemove", str(x), str(y))
    time.sleep(SETTLE)


def click(x: float, y: float, button: int = 1, double: bool = False) -> None:
    move(x, y)
    for _ in range(2 if double else 1):
        _xdo("mousedown", str(button))
        time.sleep(HOLD)
        _xdo("mouseup", str(button))
        time.sleep(0.1)


def drag(x1: float, y1: float, x2: float, y2: float, steps: int = 20, button: int = 1) -> None:
    """Press at (x1,y1), glide to (x2,y2), release. Used for roads/zones/power lines."""
    move(x1, y1)
    _xdo("mousedown", str(button))
    time.sleep(HOLD)
    for i in range(1, steps + 1):
        x, y = _clamp(x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
        _xdo("mousemove", str(x), str(y))
        time.sleep(0.04)
    time.sleep(HOLD)
    _xdo("mouseup", str(button))
    time.sleep(SETTLE)


def press_and_pick(x1: float, y1: float, x2: float, y2: float) -> None:
    """Hold on a toolbar button until its popup opens, then release on a popup item."""
    move(x1, y1)
    _xdo("mousedown", "1")
    time.sleep(0.4)
    _xdo("mousemove", str(int((x1 + x2) / 2)), str(int(y2)))
    time.sleep(0.1)
    _xdo("mousemove", str(int(x2)), str(int(y2)))
    time.sleep(0.3)
    _xdo("mouseup", "1")
    time.sleep(SETTLE)


def key(keys: str) -> None:
    """xdotool key syntax, e.g. 'Return', 'Escape', 'alt+s'. Space separated for sequences."""
    focus()
    for k in keys.split():
        _xdo("key", "--delay", "120", k)
        time.sleep(0.15)


def type_text(text: str) -> None:
    focus()
    _xdo("type", "--delay", "120", text)
    time.sleep(SETTLE)
