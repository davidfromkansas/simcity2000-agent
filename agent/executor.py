"""Turns validated JSON actions into xdotool input."""
from __future__ import annotations

import time

from . import input as inp
from . import toolmap


def run(action: dict, save_fn=None) -> dict:
    t = action["type"]
    try:
        if t == "click":
            if "target" in action:
                x, y = toolmap.target(action["target"])
            else:
                x, y = action["x"], action["y"]
            inp.click(x, y, button=int(action.get("button", 1)), double=bool(action.get("double")))
        elif t == "drag":
            (x1, y1), (x2, y2) = action["from"], action["to"]
            inp.drag(x1, y1, x2, y2, steps=int(action.get("steps", 20)))
        elif t == "tool":
            button, item = toolmap.tool(action["name"])
            if item is None:
                inp.click(*button)
            else:
                inp.press_and_pick(*button, *item)
        elif t == "menu":
            menu, item = toolmap.MENU_ITEMS[action["name"]]
            inp.press_and_pick(*toolmap.MENUS[menu], *item)
        elif t == "key":
            inp.key(str(action["keys"]))
        elif t == "type":
            inp.type_text(str(action["text"])[:64])
        elif t == "wait":
            time.sleep(max(0.0, min(30.0, float(action.get("seconds", 1)))))
        elif t == "save":
            return {"ok": True, "saved": save_fn() if save_fn else None}
        else:
            return {"ok": False, "error": f"unknown action type {t}"}
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001 - log and keep playing
        return {"ok": False, "error": str(exc)}
