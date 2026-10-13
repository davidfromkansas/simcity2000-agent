"""Fixed-region screenshots of the DOSBox-X display.

The game X server (Xvfb) is exactly 640x480 and DOSBox-X draws the game at
0,0 with no menu bar, so the capture region *is* the game screen and every
coordinate the agent sees maps 1:1 to SimCity 2000's own 640x480 pixels.
"""
from __future__ import annotations

import os
import subprocess
from io import BytesIO

from PIL import Image

GAME_REGION = {
    "left": int(os.environ.get("GAME_X", "0")),
    "top": int(os.environ.get("GAME_Y", "0")),
    "width": int(os.environ.get("GAME_W", "640")),
    "height": int(os.environ.get("GAME_H", "480")),
}


def _grab_mss() -> Image.Image:
    import mss

    with mss.mss(display=os.environ.get("DISPLAY")) as sct:
        shot = sct.grab(GAME_REGION)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


def _grab_pyautogui() -> Image.Image:
    import pyautogui  # optional dependency

    r = GAME_REGION
    return pyautogui.screenshot(region=(r["left"], r["top"], r["width"], r["height"])).convert("RGB")


def _grab_ffmpeg() -> Image.Image:
    r = GAME_REGION
    out = subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-f", "x11grab",
            "-video_size", f"{r['width']}x{r['height']}",
            "-i", f"{os.environ.get('DISPLAY', ':99')}+{r['left']},{r['top']}",
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        check=True, capture_output=True, timeout=20,
    ).stdout
    return Image.open(BytesIO(out)).convert("RGB")


def screenshot() -> Image.Image:
    """Return the current 640x480 game frame (mss → pyautogui → ffmpeg fallback)."""
    errors = []
    for grab in (_grab_mss, _grab_pyautogui, _grab_ffmpeg):
        try:
            return grab()
        except Exception as exc:  # noqa: BLE001 - try the next backend
            errors.append(f"{grab.__name__}: {exc}")
    raise RuntimeError("all screenshot backends failed: " + "; ".join(errors))


def save_png(img: Image.Image, path: str) -> None:
    img.save(path, format="PNG", optimize=True)


def to_png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
