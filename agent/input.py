"""xdotool wrapper that drives the DOSBox-X window on the Xvfb display.

SimCity 2000 polls the mouse, so a bare `xdotool click` is sometimes missed;
every press is held briefly and drags move in small steps.
"""

from __future__ import annotations

import os
import subprocess
import time

from .capture import CROP

DISPLAY = os.environ.get("DISPLAY", ":1")
HOLD = float(os.environ.get("CLICK_HOLD", "0.12"))
DRY_RUN = os.environ.get("INPUT_DRY_RUN") == "1"


def _xdo(*args: str) -> None:
    if DRY_RUN:
        print("[xdotool]", *args)
        return
    subprocess.run(["xdotool", *args], check=True, env={**os.environ, "DISPLAY": DISPLAY})


def _abs(x: int, y: int) -> tuple[str, str]:
    return str(CROP["left"] + int(x)), str(CROP["top"] + int(y))


def move(x: int, y: int) -> None:
    _xdo("mousemove", *_abs(x, y))


def mouse_down(button: int = 1) -> None:
    _xdo("mousedown", str(button))


def mouse_up(button: int = 1) -> None:
    _xdo("mouseup", str(button))


def click(x: int, y: int, button: int = 1, hold: float = HOLD) -> None:
    move(x, y)
    time.sleep(0.05)
    mouse_down(button)
    time.sleep(hold)
    mouse_up(button)


def drag(x1: int, y1: int, x2: int, y2: int, steps: int = 12, button: int = 1) -> None:
    move(x1, y1)
    time.sleep(0.05)
    mouse_down(button)
    time.sleep(HOLD)
    for i in range(1, steps + 1):
        move(x1 + (x2 - x1) * i // steps, y1 + (y2 - y1) * i // steps)
        time.sleep(0.03)
    time.sleep(HOLD)
    mouse_up(button)


def hold_and_pick(x1: int, y1: int, x2: int, y2: int) -> None:
    """Press on a toolbar button / menu title, slide to a pop-up item, release."""
    move(x1, y1)
    time.sleep(0.05)
    mouse_down()
    time.sleep(0.5)
    for i in range(1, 5):
        move(x1 + (x2 - x1) * i // 4, y1 + (y2 - y1) * i // 4)
        time.sleep(0.05)
    time.sleep(0.25)
    mouse_up()


def type(text: str, delay_ms: int = 80) -> None:
    _xdo("type", "--delay", str(delay_ms), text)


def key(k: str) -> None:
    _xdo("key", "--delay", "80", k)
