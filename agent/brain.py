"""Vision-LLM policy: screenshot in, strict JSON actions out.

Providers (picked by env):
  LLM_PROVIDER=anthropic  ANTHROPIC_API_KEY  LLM_MODEL (default claude-sonnet-4-5)
  LLM_PROVIDER=openai     OPENAI_API_KEY     LLM_MODEL (default gpt-4o)
If no key is set, main.py falls back to agent.scripted.ScriptedPolicy.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass, field

import requests

from . import toolmap

SYSTEM_PROMPT = f"""You are an autonomous agent playing SimCity 2000 (DOS, 1993) through a 640x480 screen.
Each turn you receive the current screenshot and a short history of your recent actions.
Reply with ONE JSON object and nothing else.

PRIORITIES (always in this order):
1. RESOLVE MODALS FIRST. If any dialog, newspaper, budget window, query box, advisor popup or
   "Game Saved" box is visible, dismiss/answer it before anything else (Done/OK/close box/Escape).
   Budget window: accept defaults with its Done button unless funds are negative (then raise taxes to 9%).
2. If on the title/main menu: start a new city (Easy, 1900) — prefer "edit_new_map" flow
   only if terrain is too hilly; otherwise "menu.start_new_city".
3. POWER: build one coal plant on flat land, connect it with power lines to every zone.
4. ROADS: lay a straight road spine near the plant; zones must touch a road.
5. ZONING: residential near roads, industrial near the plant/away from homes, commercial between.
   Keep an R:C:I ratio of roughly 2:1:1 and watch the RCI demand meter on the toolbar.
6. WATER: once population grows, add a water pump + pipes (water tool).
7. BUDGET: never go below ~$1,000. If money is low, just let time pass (action "wait").
8. Expand gradually: police, fire, schools, parks as the city grows.

COORDINATES: screen pixels, origin top-left, x 0..639, y 0..479. The city view is the
large isometric window. Zones/roads are placed by "drag" inside it.

NAMED TARGETS you may click by name instead of x/y (prefer these for UI):
{toolmap.describe()}

TOOLS: to pick a tool use {{"type":"tool","name":"<tool name>"}} where tool name is one of:
{", ".join(sorted(toolmap.TOOLS))}
Some tools open a dialog after selection (e.g. power_plant -> choose "dialog.power_plant.coal").

ACTION TYPES:
  {{"type":"click","target":"<named target>"}}            click a named UI element
  {{"type":"click","x":X,"y":Y}}                          click pixels
  {{"type":"drag","from":[X1,Y1],"to":[X2,Y2]}}           press-drag-release (roads, zones, lines)
  {{"type":"tool","name":"<tool>"}}                       select a toolbar tool (handles popups)
  {{"type":"menu","name":"<menu item>"}}                  pick a menu-bar item, one of: {", ".join(toolmap.MENU_ITEMS)}
  {{"type":"key","keys":"Return"}}                         xdotool key names, e.g. Escape, alt+s
  {{"type":"type","text":"Agentville"}}                   type text into a focused text field
  {{"type":"wait","seconds":5}}                           let the simulation run (max 30)
  {{"type":"save"}}                                       save the city (File > Save City)

RESPONSE SCHEMA (strict JSON, no markdown):
{{"observation":"<what is on screen, esp. any modal>",
  "reasoning":"<one or two sentences>",
  "actions":[ <1-5 actions, executed in order> ]}}
"""


@dataclass
class Decision:
    observation: str
    reasoning: str
    actions: list[dict]
    raw: str = ""
    model: str = ""
    latency_s: float = 0.0
    usage: dict = field(default_factory=dict)


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def validate(obj: dict) -> list[dict]:
    actions = obj.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("'actions' must be a non-empty list")
    allowed = {"click", "drag", "tool", "menu", "key", "type", "wait", "save"}
    clean = []
    for a in actions[:5]:
        if not isinstance(a, dict) or a.get("type") not in allowed:
            raise ValueError(f"invalid action: {a!r}")
        if a["type"] == "click" and "target" not in a and not {"x", "y"} <= a.keys():
            raise ValueError(f"click needs target or x/y: {a!r}")
        if a["type"] == "click" and "target" in a and a["target"] not in toolmap.TARGETS:
            raise ValueError(f"unknown target {a['target']!r}")
        if a["type"] == "tool" and a.get("name") not in toolmap.TOOLS:
            raise ValueError(f"unknown tool {a.get('name')!r}")
        if a["type"] == "menu" and a.get("name") not in toolmap.MENU_ITEMS:
            raise ValueError(f"unknown menu item {a.get('name')!r}")
        if a["type"] == "drag" and not (len(a.get("from", [])) == 2 and len(a.get("to", [])) == 2):
            raise ValueError(f"drag needs from/to: {a!r}")
        clean.append(a)
    return clean


class LLMBrain:
    def __init__(self) -> None:
        self.provider = os.environ.get("LLM_PROVIDER") or (
            "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "openai"
        )
        default_model = "claude-sonnet-4-5" if self.provider == "anthropic" else "gpt-4o"
        self.model = os.environ.get("LLM_MODEL", default_model)
        self.max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "800"))
        self.session = requests.Session()

    @staticmethod
    def available() -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))

    def _user_text(self, history: list[dict]) -> str:
        recent = [
            {"step": h["step"], "reasoning": h.get("reasoning", ""), "actions": h.get("actions", [])}
            for h in history[-6:]
        ]
        return (
            "Recent history (oldest first):\n"
            + json.dumps(recent, separators=(",", ":"))
            + "\n\nHere is the current screen. Respond with the JSON object only."
        )

    def _call_anthropic(self, png: bytes, text: str) -> tuple[str, dict]:
        r = self.session.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "system": SYSTEM_PROMPT,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                      "data": base64.b64encode(png).decode()}},
                        {"type": "text", "text": text},
                    ],
                }],
            },
            timeout=120,
        )
        r.raise_for_status()
        body = r.json()
        return "".join(c.get("text", "") for c in body["content"]), body.get("usage", {})

    def _call_openai(self, png: bytes, text: str) -> tuple[str, dict]:
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        r = self.session.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={
                "model": self.model,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "image_url", "image_url": {
                            "url": "data:image/png;base64," + base64.b64encode(png).decode()}},
                        {"type": "text", "text": text},
                    ]},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        body = r.json()
        return body["choices"][0]["message"]["content"], body.get("usage", {})

    def decide(self, png: bytes, history: list[dict]) -> Decision:
        call = self._call_anthropic if self.provider == "anthropic" else self._call_openai
        text = self._user_text(history)
        last_err = None
        for attempt in range(3):
            t0 = time.time()
            try:
                raw, usage = call(png, text if attempt == 0 else
                                  text + f"\n\nYour previous reply was invalid ({last_err}). JSON only.")
                obj = _extract_json(raw)
                return Decision(
                    observation=str(obj.get("observation", "")),
                    reasoning=str(obj.get("reasoning", "")),
                    actions=validate(obj),
                    raw=raw, model=f"{self.provider}:{self.model}",
                    latency_s=round(time.time() - t0, 2), usage=usage,
                )
            except (ValueError, json.JSONDecodeError, KeyError) as exc:
                last_err = str(exc)
            except requests.RequestException as exc:
                last_err = f"http: {exc}"
                time.sleep(5 * (attempt + 1))
        return Decision("", f"LLM failed: {last_err}", [{"type": "wait", "seconds": 5}],
                        model=f"{self.provider}:{self.model}")
