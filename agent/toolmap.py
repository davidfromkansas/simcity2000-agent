"""Hard-coded screen coordinates for SimCity 2000 (DOS) at 640x480.

Measured from real screenshots of the game running in DOSBox-X (see README,
"Tuning the toolmap"). The agent refers to everything here by name; only map
placements use raw pixels.

Toolbar buttons open a pop-up of sub-tools while the mouse button is held, so a
sub-tool is selected by pressing its parent button, sliding to the item and
releasing. Menus work the same way (press title, slide, release).
"""

from __future__ import annotations

from typing import Any

Point = tuple[int, int]

SCREEN = (640, 480)

# ---- Toolbar (left palette) -------------------------------------------------
# Parent buttons. Rows are 24-25 px apart, columns 22-23 px apart.
TOOLBAR: dict[str, Point] = {
    "bulldozer": (23, 57),
    "landscape": (46, 57),
    "emergency": (68, 57),
    "power": (23, 81),
    "water": (46, 81),
    "rewards": (68, 81),
    "roads": (23, 106),
    "rails": (46, 106),
    "ports": (68, 106),
    "residential": (23, 130),
    "commercial": (46, 130),
    "industrial": (68, 130),
    "education": (23, 154),
    "services": (46, 154),
    "recreation": (68, 154),
    "signs": (26, 180),
    "query": (60, 180),
    "rotate_ccw": (26, 208),
    "rotate_cw": (60, 208),
    "zoom_out": (23, 230),
    "zoom_in": (46, 230),
    "center": (68, 230),
    "map_window": (23, 255),
    "graphs_window": (46, 255),
    "population_window": (23, 276),
    "industry_window": (46, 276),
    "neighbors_window": (23, 295),
    "budget_window": (46, 295),
}

# Pop-up items: (parent button, index). Item i sits at parent_y + 8 + 16*i.
SUBTOOLS: dict[str, tuple[str, int]] = {
    "demolish": ("bulldozer", 0),
    "level_terrain": ("bulldozer", 1),
    "raise_terrain": ("bulldozer", 2),
    "lower_terrain": ("bulldozer", 3),
    "dezone": ("bulldozer", 4),
    "trees": ("landscape", 0),
    "water_tile": ("landscape", 1),
    "power_lines": ("power", 0),
    "power_plant": ("power", 1),
    "pipes": ("water", 0),
    "water_pump": ("water", 1),
    "water_tower": ("water", 2),
    "road": ("roads", 0),
    "tunnel": ("roads", 1),
    "rail": ("rails", 0),
    "rail_depot": ("rails", 1),
    "seaport": ("ports", 0),
    "light_residential": ("residential", 0),
    "dense_residential": ("residential", 1),
    "light_commercial": ("commercial", 0),
    "dense_commercial": ("commercial", 1),
    "light_industrial": ("industrial", 0),
    "dense_industrial": ("industrial", 1),
    "school": ("education", 0),
    "college": ("education", 1),
    "library": ("education", 2),
    "museum": ("education", 3),
    "police": ("services", 0),
    "fire_station": ("services", 1),
    "hospital": ("services", 2),
    "prison": ("services", 3),
    "small_park": ("recreation", 0),
    "big_park": ("recreation", 1),
    "zoo": ("recreation", 2),
    "stadium": ("recreation", 3),
    "marina": ("recreation", 4),
}
# Plain buttons (no pop-up) that are tools in their own right.
DIRECT_TOOLS = ("signs", "query", "rotate_ccw", "rotate_cw", "zoom_out", "zoom_in", "center",
                "map_window", "graphs_window", "population_window", "industry_window",
                "neighbors_window", "budget_window")
SUBTOOL_DX, SUBTOOL_DY0, SUBTOOL_STEP = 25, 8, 16

# ---- Menu bar ---------------------------------------------------------------
MENU_Y = 7
MENU_TITLES: dict[str, int] = {"file": 24, "speed": 68, "options": 121, "disasters": 185, "windows": 253}
MENU_ITEMS: dict[str, tuple[str, Point]] = {
    "file.load_city": ("file", (60, 23)),
    "file.new_city": ("file", (60, 39)),
    "file.save_city": ("file", (60, 103)),
    "file.save_city_as": ("file", (60, 119)),
    "speed.pause": ("speed", (80, 23)),
    "speed.turtle": ("speed", (80, 39)),
    "speed.llama": ("speed", (80, 55)),
    "speed.cheetah": ("speed", (80, 71)),
    "options.auto_budget": ("options", (156, 23)),
    "options.auto_goto": ("options", (156, 39)),
    "disasters.no_disasters": ("disasters", (191, 166)),
    "windows.budget": ("windows", (250, 23)),
    "windows.ordinances": ("windows", (250, 39)),
    "windows.population": ("windows", (250, 55)),
    "windows.industries": ("windows", (250, 71)),
    "windows.graphs": ("windows", (250, 87)),
    "windows.neighbors": ("windows", (250, 103)),
    "windows.map": ("windows", (250, 119)),
}

# ---- Dialog buttons ---------------------------------------------------------
BUTTONS: dict[str, Point] = {
    # Title screen
    "main.load_saved_city": (320, 175),
    "main.start_new_city": (320, 207),
    "main.edit_new_map": (320, 239),
    "main.load_scenario": (320, 271),
    # New City dialog
    "new_city.name_field": (320, 185),
    "new_city.easy": (268, 211),
    "new_city.medium": (268, 232),
    "new_city.hard": (268, 253),
    "new_city.year_1900": (384, 211),
    "new_city.year_1950": (384, 232),
    "new_city.year_2000": (384, 253),
    "new_city.year_2050": (384, 274),
    "new_city.done": (319, 293),
    # Power plant chooser (after clicking the map with power_plant)
    # Card centres; the gas card (second row) appears once gas is invented (~1951).
    "power_plant.coal": (204, 205),
    "power_plant.hydro": (320, 205),
    "power_plant.oil": (440, 205),
    "power_plant.gas": (200, 300),
    "power_plant.cancel": (459, 191),
    # Budget window
    "budget.done": (458, 123),
    # City Ordinances window (budget.ordinances opens it): checkbox centres.
    "budget.ordinances": (439, 183),
    "ordinance.pro_reading": (264, 212),
    "ordinance.energy_conservation": (264, 312),
    "ordinance.pollution_controls": (264, 363),
    "ordinance.volunteer_fire": (459, 112),
    "ordinance.free_clinics": (459, 146),
    "ordinance.city_beautification": (459, 246),
    "ordinance.done": (175, 390),
    # Bridge prompt when a road crosses water (short span: one option)
    "bridge.none": (346, 185),
    "bridge.causeway": (318, 291),
    # Bridge prompt for a longer span (two options)
    "bridge2.none": (396, 184),
    "bridge2.causeway": (269, 291),
    "bridge2.raising": (369, 291),
    # Newspaper close box (top-left corner of the paper)
    "newspaper.close": (74, 90),
    # File > Save City As dialog
    "save.name_field": (320, 104),
    "save.file_field": (320, 137),
    "save.save": (239, 376),
    "save.cancel": (399, 376),
    "save.overwrite_yes": (279, 259),  # "Overwrite existing file?" prompt
    "save.overwrite_no": (365, 259),
    "save.saved_ok": (320, 235),  # click the "Game Saved As" notice to close it
}

ACTION_TYPES = ("select_tool", "menu", "button", "click", "drag", "key", "type", "wait", "block")
BLOCK_ZONES = tuple(f"{d}_{k}" for k in ("residential", "commercial", "industrial") for d in ("light", "dense"))
# Visible city area (inside the map window) where composite actions may draw.
MAP_VIEW = (90, 130, 548, 390)


def subtool_point(name: str) -> tuple[Point, Point]:
    """(parent button, pop-up item) points for a sub-tool."""
    parent, idx = SUBTOOLS[name]
    px, py = TOOLBAR[parent]
    return (px, py), (px + SUBTOOL_DX, py + SUBTOOL_DY0 + SUBTOOL_STEP * idx)


def tool_names() -> list[str]:
    return sorted(SUBTOOLS) + list(DIRECT_TOOLS)


def describe() -> str:
    return (
        "Toolbar tools (select_tool): " + ", ".join(tool_names()) + "\n"
        "Menu items (menu): " + ", ".join(MENU_ITEMS) + "\n"
        "Dialog buttons (button): " + ", ".join(BUTTONS) + "\n"
        'Composite (block): {"type":"block","x":X,"y":Y,"zone":"light_residential","size":8} '
        "lays a size x size road ring whose WEST corner tile is at screen (X,Y), fills the inside "
        "with the zone (" + ", ".join(BLOCK_ZONES) + ") and runs a power line through the middle that "
        "pokes one tile out of the ring on both sides along the down-right axis. The next block at "
        "(X+8*size, Y+4*size) shares a road and the power line; draw one power_lines drag from a plant "
        "edge to the line stub to power the chain. Assumes 16px-wide tiles (one zoom_in from start)."
    )


class InvalidAction(ValueError):
    pass


def _int(action: dict[str, Any], *keys: str) -> None:
    for k in keys:
        v = action.get(k)
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise InvalidAction(f"{action.get('type')}: '{k}' must be a number")
        limit = SCREEN[0] if k.startswith("x") else SCREEN[1]
        if not 0 <= v < limit:
            raise InvalidAction(f"{action.get('type')}: '{k}'={v} is off screen")


def block_plan(action: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand a ``block`` action into primitive select_tool/drag actions."""
    n = action.get("size", 8)
    if not isinstance(n, int) or isinstance(n, bool) or not 4 <= n <= 14:
        raise InvalidAction("block: 'size' must be an integer 4-14")
    zone = action.get("zone")
    if zone not in BLOCK_ZONES:
        raise InvalidAction(f"block: 'zone' must be one of {BLOCK_ZONES}")
    _int(action, "x", "y")
    x, y = int(action["x"]), int(action["y"])
    half_w, half_h = 8, 4  # screen offset of one tile step along each isometric axis

    def pt(a: int, b: int) -> dict[str, int]:
        # a: down-right (SE) axis, b: up-right (NE) axis
        return {"x": x + (a + b) * half_w, "y": y + (a - b) * half_h}

    def drag(p: dict[str, int], q: dict[str, int]) -> dict[str, Any]:
        return {"type": "drag", "x1": p["x"], "y1": p["y"], "x2": q["x"], "y2": q["y"]}

    m = n // 2
    ring = [pt(0, 0), pt(0, n), pt(n, n), pt(n, 0)]
    pause = {"type": "wait", "seconds": 0.4}
    plan: list[dict[str, Any]] = [{"type": "select_tool", "tool": "road"}, pause]
    for i in range(4):
        plan += [drag(ring[i], ring[(i + 1) % 4]), pause]
    plan += [{"type": "select_tool", "tool": zone}, drag(pt(1, 1), pt(n - 1, m - 1)),
             {"type": "select_tool", "tool": zone}, drag(pt(1, m + 1), pt(n - 1, n - 1)),
             {"type": "select_tool", "tool": "power_lines"}, drag(pt(-1, m), pt(n + 1, m))]
    x0, y0, x1, y1 = MAP_VIEW
    for a in plan:
        if a["type"] == "drag":
            for px, py in ((a["x1"], a["y1"]), (a["x2"], a["y2"])):
                if not (x0 <= px <= x1 and y0 <= py <= y1):
                    raise InvalidAction(f"block: reaches ({px},{py}) outside the visible map {MAP_VIEW}; "
                                        "pick a corner nearer the middle, a smaller size, or scroll")
    return plan


def validate_action(action: dict[str, Any]) -> None:
    t = action.get("type")
    if t not in ACTION_TYPES:
        raise InvalidAction(f"unknown action type {t!r}; expected one of {ACTION_TYPES}")
    if t == "select_tool" and action.get("tool") not in tool_names():
        raise InvalidAction(f"unknown tool {action.get('tool')!r}")
    if t == "menu" and action.get("item") not in MENU_ITEMS:
        raise InvalidAction(f"unknown menu item {action.get('item')!r}")
    if t == "button" and action.get("name") not in BUTTONS:
        raise InvalidAction(f"unknown button {action.get('name')!r}")
    if t == "click":
        _int(action, "x", "y")
    if t == "drag":
        _int(action, "x1", "y1", "x2", "y2")
    if t == "key" and not (isinstance(action.get("key"), str) and action["key"]):
        raise InvalidAction("key: 'key' must be a non-empty string")
    if t == "type" and not isinstance(action.get("text"), str):
        raise InvalidAction("type: 'text' must be a string")
    if t == "block":
        block_plan(action)
    if t == "wait":
        s = action.get("seconds", 2)
        if not isinstance(s, (int, float)) or not 0 <= s <= 60:
            raise InvalidAction("wait: 'seconds' must be 0-60")
