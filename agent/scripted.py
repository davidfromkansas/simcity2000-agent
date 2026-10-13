"""Deterministic fallback policy used when no LLM API key is configured.

It still goes through the exact same screenshot -> decide -> execute -> log loop as the
LLM brain, so a keyless `docker compose up` demonstrates the whole pipeline: it makes a
flat map in the terrain editor, founds a city, then builds power, roads and RCI zones,
and keeps dismissing modal dialogs (budget, newspaper) based on simple pixel checks.
"""
from __future__ import annotations

from PIL import Image

from . import toolmap
from .brain import Decision


def _frac(img: Image.Image, box, pred) -> float:
    px = img.crop(box).convert("RGB").getdata()
    return sum(1 for p in px if pred(p)) / max(1, len(px))


def _white(p) -> bool:
    return min(p) > 200


def classify(img: Image.Image) -> str:
    """Very small screen classifier: title | editor | budget | newspaper | modal | city."""
    img = img.convert("RGB")
    menubar = img.getpixel((5, 8))
    if max(menubar) < 40:
        return "title"
    city_white = _frac(img, toolmap.CITY_VIEW, _white)
    if img.getpixel((457, 118)) == (158, 158, 158) and city_white > 0.2:
        return "budget"
    if city_white > 0.5:
        return "newspaper"
    # terrain editor: "MAKE" button where the bulldozer/power rows normally are
    if _frac(img, (14, 138, 56, 148), lambda p: abs(p[0] - p[2]) < 10 and 150 < p[0] < 220) > 0.5 \
            and _frac(img, (14, 44, 56, 72), lambda p: abs(p[0] - p[2]) < 10 and p[0] > 150) > 0.5:
        return "editor"
    gray = _frac(img, toolmap.CITY_VIEW, lambda p: p == (158, 158, 158))
    if gray > 0.04 and img.getpixel((346, 185)) != img.getpixel((300, 300)):
        return "select_popup"
    if city_white > 0.12:
        return "modal"
    return "city"


def _d(reason: str, *actions: dict) -> Decision:
    return Decision(observation="", reasoning=reason, actions=list(actions), model="scripted")


def T(name):
    return {"type": "click", "target": name}


def W(s):
    return {"type": "wait", "seconds": s}


def _water(p) -> bool:
    return p[2] > 180 and p[0] < 90


# The starter neighbourhood in tile coordinates (i, j) relative to an anchor tile.
# The plant sits at (0,0); a road runs along j=3; power lines run along j=-3 and i=9.
TILE_PLAN = [
    ("Build a coal power plant on dry land.",
     [{"type": "tool", "name": "power_plant"}, W(1), T("dialog.power_plant.coal"), ("click", (0, 0)), W(1)]),
    ("Lay a main road through the block.", [{"type": "tool", "name": "road"}, ("drag", (-2, 3), (15, 3))]),
    ("Lay a cross street.", [{"type": "tool", "name": "road"}, ("drag", (12, -3), (12, 9))]),
    ("Run power lines from the plant out to the zones.",
     [{"type": "tool", "name": "power_lines"}, ("drag", (-1, -3), (9, -3)), ("drag", (9, -3), (9, 8))]),
    ("Zone light industrial next to the plant (north of the road).",
     [{"type": "tool", "name": "light_industrial"}, ("drag", (3, -1), (8, 2))]),
    ("Zone light residential south of the road.",
     [{"type": "tool", "name": "light_residential"}, ("drag", (0, 4), (8, 7))]),
    ("Zone light commercial across the cross street.",
     [{"type": "tool", "name": "light_commercial"}, ("drag", (10, 4), (11, 7)), ("drag", (13, 4), (15, 7))]),
    ("Zone more residential across the cross street.",
     [{"type": "tool", "name": "light_residential"}, ("drag", (13, -2), (15, 2))]),
]
PLAN_TILES = [(i, j) for i in range(-3, 17) for j in range(-4, 10)]


def find_anchor(img: Image.Image) -> tuple[int, int]:
    """Screen point for tile (0,0) that keeps the whole plan on dry land inside the view."""
    img = img.convert("RGB")
    x1, y1, x2, y2 = toolmap.CITY_VIEW
    (ix, iy), (jx, jy) = toolmap.TILE_I, toolmap.TILE_J
    best, best_score = ((x1 + x2) // 2, (y1 + y2) // 2), 1e9
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    for ay in range(y1, y2, 4):
        for ax in range(x1, x2, 8):
            score = 0.0
            for i, j in PLAN_TILES:
                x, y = ax + i * ix + j * jx, ay + i * iy + j * jy
                if not (x1 + 4 <= x < x2 - 4 and y1 + 4 <= y < y2 - 4):
                    score += 5
                elif _water(img.getpixel((x, y))):
                    score += 3
            score += 0.002 * ((ax - cx) ** 2 + (ay - cy) ** 2)
            if score < best_score:
                best, best_score = (ax, ay), score
    return best


def place(anchor, tile) -> list[int]:
    (ix, iy), (jx, jy) = toolmap.TILE_I, toolmap.TILE_J
    i, j = tile
    return [anchor[0] + i * ix + j * jx, anchor[1] + i * iy + j * jy]


def resolve(anchor, actions) -> list[dict]:
    out = []
    for a in actions:
        if isinstance(a, tuple) and a[0] == "click":
            x, y = place(anchor, a[1])
            out.append({"type": "click", "x": x, "y": y})
        elif isinstance(a, tuple) and a[0] == "drag":
            out.append({"type": "drag", "from": place(anchor, a[1]), "to": place(anchor, a[2])})
        else:
            out.append(a)
    return out


class ScriptedPolicy:
    def __init__(self) -> None:
        self.phase = "boot"
        self.build_i = 0
        self.tries = 0
        self.idle = 0
        self.anchor = None

    def decide(self, png: bytes, history: list[dict], img: Image.Image | None = None) -> Decision:
        screen = classify(img) if img is not None else "city"
        self.tries += 1

        if screen == "budget":
            return _d("Budget window is open; accept it with Done.", T("dialog.budget.done"), W(1))
        if screen == "newspaper":
            return _d("Newspaper is covering the city; close it.", T("dialog.newspaper.close"), W(1))

        if self.phase == "boot":
            if screen == "title":
                self.phase = "menu"
                return _d("Title/registration screen: click to continue.",
                          {"type": "click", "x": 320, "y": 420}, W(3))
            if screen == "editor":
                self.phase = "editor"
            else:
                self.phase = "city" if screen == "city" else "boot"
                return _d("Waiting for the game to boot.", W(3))

        if self.phase == "menu":
            if screen == "title":
                self.phase = "editor"
                return _d("Main menu: open the terrain editor to make a flat map.",
                          T("menu.edit_new_map"), W(4))
            self.phase = "editor" if screen == "editor" else "city"

        if self.phase == "editor":
            if screen == "title":  # still on menu / splash
                self.phase = "boot" if self.tries > 6 else "menu"
                return _d("Still on the title screen; continue.", {"type": "click", "x": 320, "y": 420}, W(3))
            self.phase = "newcity"
            return _d("Terrain editor: flatten hills, reduce water, generate, then Done.",
                      {"type": "drag", "from": [17, 112], "to": [17, 132], "steps": 6},
                      {"type": "drag", "from": [33, 118], "to": [33, 132], "steps": 6},
                      T("terrain.make"), W(3), T("terrain.done"), W(3))

        if self.phase == "newcity":
            self.phase = "setup"
            return _d("New-city dialog: name the city, pick Easy and 1900, Done.",
                      {"type": "type", "text": "Agentville"}, T("newcity.easy"),
                      T("newcity.year_1900"), T("newcity.done"), W(4))

        if self.phase == "setup":
            self.phase = "build"
            return _d("Turn off disasters so the demo city survives.",
                      {"type": "menu", "name": "disasters.no_disasters"}, W(1))

        if screen == "select_popup":
            return _d("A Raised Wires/Select popup is open; choose None.", T("dialog.wires.none"), W(1))
        if screen == "modal":
            return _d("Some dialog is open; press Return to accept it.", {"type": "key", "keys": "Return"}, W(1))

        if self.phase == "build" and self.build_i < len(TILE_PLAN):
            if self.anchor is None:
                self.anchor = find_anchor(img) if img is not None else (320, 230)
            reason, actions = TILE_PLAN[self.build_i]
            self.build_i += 1
            return _d(f"{reason} (anchor tile at screen {self.anchor})", *resolve(self.anchor, actions))

        self.phase = "grow"
        self.idle += 1
        if self.idle % 10 == 0:
            return _d("Periodic save.", {"type": "save"}, W(2))
        return _d("City is built; let time pass and watch for dialogs.", W(10))
