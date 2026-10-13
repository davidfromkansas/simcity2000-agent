"""Turn a validated JSON action into xdotool input."""

from __future__ import annotations

import time
from pathlib import Path
from types import ModuleType
from typing import Any

from . import input as default_input
from . import toolmap


def execute(action: dict[str, Any], inp: ModuleType = default_input) -> str:
    toolmap.validate_action(action)
    t = action["type"]
    if t == "select_tool":
        name = action["tool"]
        if name in toolmap.SUBTOOLS:
            (px, py), (ix, iy) = toolmap.subtool_point(name)
            inp.hold_and_pick(px, py, ix, iy)
        else:
            inp.click(*toolmap.TOOLBAR[name])
        return f"selected tool {name}"
    if t == "menu":
        title, (ix, iy) = toolmap.MENU_ITEMS[action["item"]]
        inp.hold_and_pick(toolmap.MENU_TITLES[title], toolmap.MENU_Y, ix, iy)
        return f"menu {action['item']}"
    if t == "button":
        inp.click(*toolmap.BUTTONS[action["name"]])
        return f"pressed {action['name']}"
    if t == "click":
        inp.click(int(action["x"]), int(action["y"]))
        return f"clicked ({action['x']},{action['y']})"
    if t == "drag":
        inp.drag(int(action["x1"]), int(action["y1"]), int(action["x2"]), int(action["y2"]))
        return f"dragged ({action['x1']},{action['y1']})->({action['x2']},{action['y2']})"
    if t == "key":
        inp.key(action["key"])
        return f"key {action['key']}"
    if t == "type":
        inp.type(action["text"])
        return f"typed {action['text']!r}"
    if t == "block":
        for step in toolmap.block_plan(action):
            execute(step, inp)
        return f"built {action.get('size', 8)}x{action.get('size', 8)} {action['zone']} block at ({action['x']},{action['y']})"
    seconds = float(action.get("seconds", 2))
    time.sleep(seconds)
    return f"waited {seconds:g}s"


def next_save_name(game_dir: Path, prefix: str = "AGENT") -> str:
    """First unused DOS 8.3 name like AGENT001 so the game never asks to overwrite."""
    prefix = prefix.upper()[:5]
    existing = {p.stem.upper() for p in game_dir.glob("*") if p.suffix.upper() == ".SC2"}
    for n in range(1, 1000):
        name = f"{prefix}{n:03d}"
        if name not in existing:
            return name
    return f"{prefix}999"


def save_city(filename: str, inp: ModuleType = default_input) -> None:
    """File > Save City As..., overwrite the file name field, press Save.

    This is the game's own save (a .SC2 file on the mounted C: drive, i.e.
    games/simcity2000/ on the host), which survives container restarts and can
    be reloaded from the title screen.
    """
    for _ in range(2):  # close any open prompt first; menus are blocked under a modal dialog
        inp.key("Escape")
        time.sleep(0.5)
    title, (ix, iy) = toolmap.MENU_ITEMS["file.save_city_as"]
    inp.hold_and_pick(toolmap.MENU_TITLES[title], toolmap.MENU_Y, ix, iy)
    time.sleep(1.5)
    inp.click(*toolmap.BUTTONS["save.file_field"])
    time.sleep(0.3)
    for _ in range(16):
        inp.key("BackSpace")
    inp.type(filename)
    time.sleep(0.3)
    inp.click(*toolmap.BUTTONS["save.save"])
    time.sleep(2.0)
    inp.click(*toolmap.BUTTONS["save.saved_ok"])  # "Game Saved As: ..." notice
    time.sleep(1.0)
