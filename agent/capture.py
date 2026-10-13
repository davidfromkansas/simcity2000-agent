"""Screenshot the DOSBox-X window from the Xvfb display on a fixed crop.

DOSBox-X is pinned to (0, 0) at 640x480 (see games/dosbox-x.conf and
docker/entrypoint.sh), so game pixel (x, y) == screen pixel (x, y) and every
coordinate in toolmap.py stays valid.
"""

from __future__ import annotations

import io
import os

from PIL import Image, ImageDraw

WIDTH = 640
HEIGHT = 480
CROP = {
    "left": int(os.environ.get("CAPTURE_LEFT", "0")),
    "top": int(os.environ.get("CAPTURE_TOP", "0")),
    "width": WIDTH,
    "height": HEIGHT,
}


class Screen:
    def __init__(self, crop: dict[str, int] | None = None):
        import mss

        self.crop = crop or CROP
        self._mss = mss.MSS() if hasattr(mss, "MSS") else mss.mss()

    def grab(self) -> Image.Image:
        shot = self._mss.grab(self.crop)
        return Image.frombytes("RGB", shot.size, shot.rgb)


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def with_grid(img: Image.Image, step: int = 40) -> Image.Image:
    """Copy of `img` with a faint labelled pixel grid so the model can read coordinates."""
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    for x in range(step, w, step):
        draw.line([(x, 0), (x, h)], fill=(255, 0, 255), width=1)
        draw.text((x + 1, h - 11), str(x), fill=(255, 255, 0))
    for y in range(step, h, step):
        draw.line([(0, y), (w, y)], fill=(255, 0, 255), width=1)
        draw.text((w - 24, y + 1), str(y), fill=(255, 255, 0))
    return Image.blend(img.convert("RGB"), out, 0.45)
