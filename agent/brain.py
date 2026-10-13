"""Vision LLM policy: screenshot + recent actions + state summary -> one JSON action."""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

import requests
from PIL import Image

from . import toolmap
from .capture import to_png, with_grid

SYSTEM_PROMPT = """You are an expert SimCity 2000 (MS-DOS, 1993) player controlling the game
through a mouse and keyboard. Each turn you get a 640x480 screenshot (a faint magenta
grid with yellow pixel labels every 40px is overlaid to help you read coordinates),
your recent actions, and your own running notes. You reply with exactly ONE action.

PRIORITIES, in order, every turn:
1. RESOLVE MODAL DIALOGS FIRST. If any dialog, pop-up, newspaper, advisor message,
   budget window, query box, file dialog or confirmation is open, your action must
   dismiss or answer it (use a named button, or click its Done/OK/Cancel/close box,
   or press Escape/Return). Never try to build while a dialog is open.
2. If you are on the title/main menu, start a new city (button main.start_new_city),
   then in the New City dialog pick new_city.easy and press new_city.done.
3. POWER: a city needs a power plant before anything grows. Early on build one coal
   plant: select_tool power_plant opens the "Select Powerplant" chooser; pick
   button power_plant.coal; THEN click the CENTRE of a large flat, treeless, light-brown
   area (at least 4x4 tiles, away from slopes, cliffs and water) to place it ($4,000).
   VERIFY every placement: funds in the map title bar (e.g. "$20,000") must drop. If
   funds did not change, NOTHING was built - do not write that it was. Try a different,
   flatter spot (or bulldoze trees first) and re-check. The "Power Plant Needed" text in
   the top-left info box means no plant exists yet. Connect it with power_lines to
   every zone.
   Watch for flashing "no power" lightning icons and fix them.
4. ZONING: lay roads (drag with tool road) and place light zones alongside them in a
   healthy mix (roughly 2 residential : 1 commercial : 1 industrial). Avoid dragging
   roads across water (a bridge prompt appears; answer it with bridge.none to cancel).
   Keep industry
   away from homes. Zones must touch a road and be powered. Add water (water_pump +
   pipes) once the city has a few hundred people.
5. BUDGET: never let funds drop below about $1,500. When the budget window opens at
   year end, review it and press budget.done. Do not take loans unless broke.
   Raise/lower speed with speed menu items; use speed.cheetah while waiting for growth
   and speed.pause if something goes wrong.
6. Expand gradually: police, fire stations and schools once population grows.

COORDINATES: Use named toolbar tools, menu items and dialog buttons whenever one
fits - never guess pixels for them. Only map placements (click/drag on the city map)
use raw pixel coordinates; the map view is roughly x 90-550, y 128-382. Zones and
roads are placed by dragging a rectangle/line on the map after selecting the tool.
Tile size at default zoom is about 32x16 pixels (isometric).

Never claim something exists unless you can see it in the CURRENT screenshot; your
notes and past actions may be wrong.

Reply with ONLY a JSON object, no prose, no code fences:
{"observation": "<what you see, 1 sentence>",
 "reasoning": "<why this action, 1 sentence>",
 "action": {"type": "<one of the action types below>", ...},
 "summary": "<updated running notes about the city: funds, population, what is built,
             what to do next; max 60 words>"}

Action types:
 {"type":"select_tool","tool":"<toolbar tool name>"}
 {"type":"menu","item":"<menu item name>"}
 {"type":"button","name":"<dialog button name>"}
 {"type":"click","x":int,"y":int}            (single click on the map / anywhere)
 {"type":"drag","x1":int,"y1":int,"x2":int,"y2":int}  (roads, lines, pipes, zones)
 {"type":"key","key":"<xdotool key name, e.g. Escape, Return>"}
 {"type":"type","text":"<text>"}
 {"type":"wait","seconds":number}             (let the simulation run, 1-20s)
"""


class BrainError(RuntimeError):
    pass


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise BrainError(f"no JSON object in reply: {text[:200]!r}")
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise BrainError(f"invalid JSON: {e}") from e
    if not isinstance(obj, dict):
        raise BrainError("reply is not a JSON object")
    return obj


def parse_decision(text: str) -> dict[str, Any]:
    obj = extract_json(text)
    action = obj.get("action")
    if not isinstance(action, dict):
        raise BrainError("missing 'action' object")
    toolmap.validate_action(action)
    obj.setdefault("summary", "")
    return obj


def _user_text(history: list[dict[str, Any]], summary: str) -> str:
    recent = "\n".join(f"- step {h['step']}: {json.dumps(h['action'])} -> {h['result']}" for h in history) or "- (none yet)"
    return (
        f"Your running notes: {summary or '(none yet - this is the first turn)'}\n\n"
        f"Recent actions (oldest first):\n{recent}\n\n"
        f"{toolmap.describe()}\n\nReturn the JSON for your next single action."
    )


@dataclass
class Brain:
    provider: str
    api_key: str
    model: str
    max_tokens: int = 600
    timeout: float = 90.0
    session: requests.Session = field(default_factory=requests.Session)

    def decide(self, img: Image.Image, history: list[dict[str, Any]], summary: str) -> dict[str, Any]:
        b64 = base64.b64encode(to_png(with_grid(img))).decode()
        text = _user_text(history, summary)
        reply = self._call(b64, text)
        try:
            return parse_decision(reply)
        except BrainError as e:
            reply = self._call(b64, text + f"\n\nYour previous reply was rejected: {e}. Reply with valid JSON only.")
            return parse_decision(reply)

    def _call(self, b64png: str, text: str) -> str:
        if self.provider == "anthropic":
            r = self.session.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={
                    "model": self.model,
                    "max_tokens": self.max_tokens,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64png}},
                        {"type": "text", "text": text},
                    ]}],
                },
                timeout=self.timeout,
            )
            r.raise_for_status()
            return "".join(c.get("text", "") for c in r.json()["content"] if c.get("type") == "text")
        r = self.session.post(
            os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64png}"}},
                        {"type": "text", "text": text},
                    ]},
                ],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-5", "openai": "gpt-4o"}


def from_env() -> Brain:
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    if not provider:
        provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai" if os.environ.get("OPENAI_API_KEY") else ""
    if provider not in DEFAULT_MODELS:
        raise BrainError("set ANTHROPIC_API_KEY or OPENAI_API_KEY (and optionally LLM_PROVIDER=anthropic|openai)")
    key = os.environ.get("ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY", "")
    if not key:
        raise BrainError(f"LLM_PROVIDER={provider} but its API key env var is empty")
    return Brain(provider=provider, api_key=key, model=os.environ.get("LLM_MODEL") or DEFAULT_MODELS[provider])
