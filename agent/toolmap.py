"""Hardcoded 640x480 screen coordinates for SimCity 2000 (DOS, DOSBox-X, VESA 640x480).

Measured from live screenshots of the archive.org build (SC2000.EXE). Every UI element
is referenced by name so the LLM never has to guess pixel positions for chrome.

Toolbar buttons with a sub-menu (power, water, zones, ...) open a popup to the right
while the button is held: the popup's left edge is the button's x and items are stacked
16px apart starting 8px below the button's centre (verified for every popup button).
`TOOLS` entries therefore store (button_xy, popup_item_xy | None).
"""
from __future__ import annotations

# --- toolbar (left palette) -------------------------------------------------
TOOLBAR = {
    "bulldozer": (22, 57), "landscape": (45, 57), "emergency": (68, 57),
    "power": (22, 80), "water": (45, 80), "rewards": (68, 80),
    "roads": (22, 104), "rails": (45, 104), "ports": (68, 104),
    "residential": (22, 129), "commercial": (45, 129), "industrial": (68, 129),
    "education": (22, 154), "services": (45, 154), "parks": (68, 154),
    "signs": (30, 181), "query": (55, 181),
    "rotate_ccw": (30, 207), "rotate_cw": (60, 207),
    "zoom_out": (22, 231), "zoom_in": (47, 231), "center": (70, 231),
    "map_window": (23, 256), "graph_window": (47, 256),
    "population_window": (23, 277), "industry_window": (47, 277),
    "neighbors_window": (23, 297), "budget_window": (47, 297),
    "show_buildings": (28, 324), "show_signs": (63, 324),
    "show_infrastructure": (28, 334), "show_zones": (63, 334),
    "show_underground": (33, 346), "help": (68, 346),
}
RCI_METER = (60, 255, 80, 305)  # x1, y1, x2, y2 of the R/C/I demand bars


def _popup(button: str, index: int) -> tuple[int, int]:
    bx, by = TOOLBAR[button]
    return (bx + 25, by + 7 + 15 * index)


# tool name -> (button, popup item or None for a direct click)
TOOLS: dict[str, tuple[tuple[int, int], tuple[int, int] | None]] = {
    "bulldozer": (TOOLBAR["bulldozer"], _popup("bulldozer", 0)),
    "level_terrain": (TOOLBAR["bulldozer"], _popup("bulldozer", 1)),
    "dezone": (TOOLBAR["bulldozer"], _popup("bulldozer", 4)),
    "power_lines": (TOOLBAR["power"], _popup("power", 0)),
    "power_plant": (TOOLBAR["power"], _popup("power", 1)),
    "water_pipes": (TOOLBAR["water"], _popup("water", 0)),
    "water_pump": (TOOLBAR["water"], _popup("water", 1)),
    "water_tower": (TOOLBAR["water"], _popup("water", 2)),
    "road": (TOOLBAR["roads"], _popup("roads", 0)),
    "rail": (TOOLBAR["rails"], _popup("rails", 0)),
    "light_residential": (TOOLBAR["residential"], _popup("residential", 0)),
    "dense_residential": (TOOLBAR["residential"], _popup("residential", 1)),
    "light_commercial": (TOOLBAR["commercial"], _popup("commercial", 0)),
    "dense_commercial": (TOOLBAR["commercial"], _popup("commercial", 1)),
    "light_industrial": (TOOLBAR["industrial"], _popup("industrial", 0)),
    "dense_industrial": (TOOLBAR["industrial"], _popup("industrial", 1)),
    "school": (TOOLBAR["education"], _popup("education", 0)),
    "college": (TOOLBAR["education"], _popup("education", 1)),
    "library": (TOOLBAR["education"], _popup("education", 2)),
    "police": (TOOLBAR["services"], _popup("services", 0)),
    "fire_station": (TOOLBAR["services"], _popup("services", 1)),
    "hospital": (TOOLBAR["services"], _popup("services", 2)),
    "small_park": (TOOLBAR["parks"], _popup("parks", 0)),
    "big_park": (TOOLBAR["parks"], _popup("parks", 1)),
    "query": (TOOLBAR["query"], None),
    "zoom_in": (TOOLBAR["zoom_in"], None),
    "zoom_out": (TOOLBAR["zoom_out"], None),
    "center": (TOOLBAR["center"], None),
    "rotate_cw": (TOOLBAR["rotate_cw"], None),
    "rotate_ccw": (TOOLBAR["rotate_ccw"], None),
    "budget_window": (TOOLBAR["budget_window"], None),
}

# --- menu bar ---------------------------------------------------------------
MENUS = {"file": (24, 8), "speed": (66, 8), "options": (121, 8),
         "disasters": (185, 8), "windows": (253, 8), "newspaper": (327, 8)}
MENU_ITEMS = {
    "file.load_city": ("file", (50, 24)), "file.new_city": ("file", (50, 40)),
    "file.edit_new_map": ("file", (50, 56)), "file.load_scenario": ("file", (50, 72)),
    "file.save_city": ("file", (50, 104)), "file.save_city_as": ("file", (50, 120)),
    "file.quit": ("file", (50, 184)),
    "speed.pause": ("speed", (80, 24)), "speed.turtle": ("speed", (80, 40)),
    "speed.llama": ("speed", (80, 56)), "speed.cheetah": ("speed", (80, 72)),
    "options.auto_budget": ("options", (140, 24)), "options.auto_goto": ("options", (140, 40)),
    "options.sound_effects": ("options", (140, 56)), "options.music": ("options", (140, 72)),
    "disasters.no_disasters": ("disasters", (200, 168)),
}
HOTKEYS = {"save_city": "alt+s", "edit_new_map": "alt+e", "pause": "alt+p",
           "turtle": "alt+1", "llama": "alt+2", "cheetah": "alt+3"}

# --- full-screen menus and dialogs -----------------------------------------
TARGETS: dict[str, tuple[int, int]] = {
    # title screen (after the registration splash)
    "splash.continue": (320, 260),
    "menu.load_saved_city": (320, 175), "menu.start_new_city": (320, 207),
    "menu.edit_new_map": (320, 239), "menu.load_scenario": (320, 271), "menu.quit": (320, 303),
    # new-city dialog (name / difficulty / year)
    "newcity.name_field": (320, 186),
    "newcity.easy": (266, 211), "newcity.medium": (266, 232), "newcity.hard": (266, 253),
    "newcity.year_1900": (385, 211), "newcity.year_1950": (385, 232),
    "newcity.year_2000": (385, 253), "newcity.year_2050": (385, 274),
    "newcity.done": (320, 294),
    # terrain editor (Edit New Map)
    "terrain.coast_toggle": (34, 53), "terrain.river_toggle": (34, 66),
    "terrain.hills_slider": (17, 100), "terrain.water_slider": (33, 100),
    "terrain.trees_slider": (49, 100), "terrain.make": (34, 143), "terrain.done": (34, 341),
    # dialogs
    "dialog.newspaper.close": (74, 90),           # close box of the newspaper window
    "dialog.budget.done": (457, 123),             # yearly budget window
    "dialog.power_plant.coal": (203, 255), "dialog.power_plant.hydro": (320, 255),
    "dialog.power_plant.oil": (440, 255), "dialog.power_plant.cancel": (460, 191),
    "dialog.save_prompt.yes": (257, 261), "dialog.save_prompt.no": (317, 261),
    "dialog.save_prompt.cancel": (380, 261),
    "dialog.wires.none": (346, 185),              # "Raised Wires" select popup when lines cross water
    "dialog.center_ok": (320, 300),               # generic centered OK button
    # city window
    "city.center": (320, 255),
}
TARGETS.update({f"toolbar.{k}": v for k, v in TOOLBAR.items()})
TARGETS.update({f"menu_bar.{k}": v for k, v in MENUS.items()})

# Visible playfield of the default (unmaximised) city window.
CITY_VIEW = (88, 128, 552, 384)  # x1, y1, x2, y2

# Order matters: the agent tries these when it thinks a modal is open but is unsure.
DISMISS_ORDER = ["dialog.budget.done", "dialog.newspaper.close", "dialog.wires.none", "dialog.center_ok"]


def describe() -> str:
    lines = [f"  {name}: ({x},{y})" for name, (x, y) in TARGETS.items()]
    lines.append(f"  city view rectangle: {CITY_VIEW}")
    return "\n".join(lines)


def tool(name: str) -> tuple[tuple[int, int], tuple[int, int] | None]:
    return TOOLS[name]


def target(name: str) -> tuple[int, int]:
    return TARGETS[name]


# Isometric tile step at the default zoom: +1 along the map's x axis moves (8, 4) on
# screen, +1 along y moves (-8, 4). Used by the scripted policy to lay out a block.
TILE_I = (8, 4)
TILE_J = (-8, 4)
