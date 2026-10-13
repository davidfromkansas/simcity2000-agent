import json
from types import SimpleNamespace

import pytest
from PIL import Image

from agent import actions, brain, capture, toolmap


class FakeInput(SimpleNamespace):
    def __init__(self):
        super().__init__(calls=[])

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a: self.calls.append((name, *a))


def test_all_coordinates_on_screen():
    w, h = toolmap.SCREEN
    pts = list(toolmap.TOOLBAR.values()) + list(toolmap.BUTTONS.values())
    pts += [p for _, p in toolmap.MENU_ITEMS.values()]
    pts += [toolmap.subtool_point(n)[1] for n in toolmap.SUBTOOLS]
    for x, y in pts:
        assert 0 <= x < w and 0 <= y < h


def test_subtools_reference_real_buttons():
    for parent, _ in toolmap.SUBTOOLS.values():
        assert parent in toolmap.TOOLBAR
    assert set(toolmap.DIRECT_TOOLS) <= set(toolmap.TOOLBAR)
    assert toolmap.subtool_point("power_plant") == ((23, 81), (48, 105))


@pytest.mark.parametrize("action", [
    {"type": "select_tool", "tool": "road"},
    {"type": "menu", "item": "speed.cheetah"},
    {"type": "button", "name": "budget.done"},
    {"type": "click", "x": 300, "y": 200},
    {"type": "drag", "x1": 100, "y1": 200, "x2": 300, "y2": 200},
    {"type": "key", "key": "Escape"},
    {"type": "type", "text": "hi"},
    {"type": "wait", "seconds": 0},
])
def test_valid_actions_execute(action):
    inp = FakeInput()
    assert actions.execute(action, inp)
    if action["type"] != "wait":
        assert inp.calls


@pytest.mark.parametrize("action", [
    {"type": "fly"},
    {"type": "select_tool", "tool": "laser"},
    {"type": "click", "x": 700, "y": 10},
    {"type": "drag", "x1": 1, "y1": 2},
    {"type": "button", "name": "nope"},
])
def test_invalid_actions_rejected(action):
    with pytest.raises(toolmap.InvalidAction):
        toolmap.validate_action(action)


def test_select_subtool_uses_hold_and_pick():
    inp = FakeInput()
    actions.execute({"type": "select_tool", "tool": "light_residential"}, inp)
    assert inp.calls == [("hold_and_pick", 23, 130, 48, 138)]


def test_parse_decision_handles_fences():
    reply = "```json\n" + json.dumps({"observation": "o", "action": {"type": "key", "key": "Escape"}}) + "\n```"
    d = brain.parse_decision(reply)
    assert d["action"]["key"] == "Escape" and d["summary"] == ""


def test_parse_decision_rejects_garbage():
    with pytest.raises(brain.BrainError):
        brain.parse_decision("I think I will build a road")
    with pytest.raises(toolmap.InvalidAction):
        brain.parse_decision('{"action": {"type": "select_tool", "tool": "nuke"}}')


def test_brain_retries_once_on_bad_reply(monkeypatch):
    replies = iter(["not json", '{"action": {"type": "wait", "seconds": 1}, "summary": "s"}'])
    b = brain.Brain(provider="anthropic", api_key="k", model="m")
    monkeypatch.setattr(b, "_call", lambda *a: next(replies))
    d = b.decide(Image.new("RGB", (640, 480)), [], "")
    assert d["action"]["type"] == "wait" and d["summary"] == "s"


def test_from_env_picks_provider(monkeypatch):
    for k in ("LLM_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(brain.BrainError):
        brain.from_env()
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert brain.from_env().provider == "openai"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "y")
    assert brain.from_env().provider == "anthropic"


def test_grid_overlay_keeps_size():
    img = Image.new("RGB", (640, 480))
    assert capture.with_grid(img).size == (640, 480)
    assert capture.to_png(img)[:4] == b"\x89PNG"


def test_save_city_sequence():
    inp = FakeInput()
    actions.save_city("AGENT", inp)
    names = [c[0] for c in inp.calls]
    assert names[:2] == ["key", "key"] and "hold_and_pick" in names and ("type", "AGENT") in inp.calls
    assert ("click", *toolmap.BUTTONS["save.save"]) in inp.calls


def test_next_save_name(tmp_path):
    assert actions.next_save_name(tmp_path) == "AGENT001"
    (tmp_path / "AGENT001.SC2").write_bytes(b"")
    (tmp_path / "agent002.sc2").write_bytes(b"")
    assert actions.next_save_name(tmp_path, "agent") == "AGENT003"
