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


def _answer_when_asked(ctl, payload):
    import threading
    import time

    def go():
        while not (ctl / "screen.png").exists():
            time.sleep(0.01)
        (ctl / "action.json").write_text(json.dumps(payload))

    t = threading.Thread(target=go)
    t.start()
    return t


def test_external_brain_single_and_batch(tmp_path):
    ctl = tmp_path / "control"
    b = brain.ExternalBrain(control_dir=ctl, poll=0.01)
    assert "RESOLVE MODAL DIALOGS" in (ctl / "prompt.md").read_text()
    img = Image.new("RGB", (640, 480))
    t = _answer_when_asked(ctl, {"action": {"type": "button", "name": "main.start_new_city"}, "summary": "s"})
    d = b.decide(img, [], "")
    t.join()
    assert d["action"]["name"] == "main.start_new_city" and not (ctl / "action.json").exists()
    assert json.loads((ctl / "state.json").read_text())["turn"] == 1
    (ctl / "screen.png").unlink()
    batch = {"actions": [{"type": "select_tool", "tool": "road"}, {"type": "wait", "seconds": 2}], "summary": "b"}
    t = _answer_when_asked(ctl, batch)
    assert b.decide(img, [], "")["action"]["tool"] == "road"
    t.join()
    assert b.decide(img, [], "")["action"] == {"type": "wait", "seconds": 2}


def test_external_brain_rejects_bad_action_and_times_out(tmp_path):
    ctl = tmp_path / "c"
    b = brain.ExternalBrain(control_dir=ctl, poll=0.01, timeout=0.05)
    assert b.decide(Image.new("RGB", (640, 480)), [], "x")["action"]["type"] == "wait"
    (ctl / "action.json").write_text(json.dumps({"actions": [{"type": "select_tool", "tool": "nope"}]}))
    with pytest.raises(ValueError):
        b.decide(Image.new("RGB", (640, 480)), [], "")


def test_from_env_external(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_PROVIDER", "devin")
    monkeypatch.setenv("CONTROL_DIR", str(tmp_path / "ctl"))
    b = brain.from_env()
    assert isinstance(b, brain.ExternalBrain) and b.provider == "devin"


def test_sc2_read_stats(tmp_path):
    import struct

    from agent import sc2

    vals = [0] * 20
    vals[sc2.MISC_YEAR_FOUNDED], vals[sc2.MISC_DAYS] = 1900, 10607
    vals[sc2.MISC_FUNDS], vals[sc2.MISC_POPULATION] = 13740, 749
    raw = struct.pack(">20i", *vals)
    misc = bytes([len(raw)]) + raw
    body = b"SCDH" + b"MISC" + struct.pack(">I", len(misc)) + misc
    f = tmp_path / "X.SC2"
    f.write_bytes(b"FORM" + struct.pack(">I", len(body)) + body)
    assert sc2.read_stats(f) == {"date": "May 1935", "year": 1935, "funds": 13740, "population": 749}

    vals = [0] * 1200
    vals[sc2.MISC_YEAR_FOUNDED], vals[sc2.MISC_DAYS] = 1900, 10607
    vals[sc2.MISC_EXTRA["demand_r"]], vals[sc2.MISC_EXTRA["demand_c"]] = 2000, -321
    raw = struct.pack(">1200i", *vals)
    misc = b"".join(bytes([len(c)]) + c for c in (raw[i:i + 127] for i in range(0, len(raw), 127)))
    body = b"SCDH" + b"MISC" + struct.pack(">I", len(misc)) + misc
    f.write_bytes(b"FORM" + struct.pack(">I", len(body)) + body)
    stats = sc2.read_stats(f)
    assert stats["demand_r"] == 2000 and stats["demand_c"] == -321 and stats["pollution"] == 0


def test_block_plan_and_execute():
    from types import SimpleNamespace

    from agent import actions, toolmap

    plan = toolmap.block_plan({"type": "block", "x": 200, "y": 260, "zone": "light_residential", "size": 8})
    drags = [a for a in plan if a["type"] == "drag"]
    assert len(drags) == 7
    assert (drags[0]["x1"], drags[0]["y1"], drags[0]["x2"], drags[0]["y2"]) == (200, 260, 264, 228)
    assert (drags[-1]["x1"], drags[-1]["y1"]) == (224, 240)  # power line stub one tile outside the ring
    calls = []
    inp = SimpleNamespace(drag=lambda *a: calls.append(("drag", a)), click=lambda *a: calls.append(("click", a)),
                          hold_and_pick=lambda *a: calls.append(("pick", a)))
    out = actions.execute({"type": "block", "x": 200, "y": 260, "zone": "light_industrial"}, inp)
    assert "light_industrial" in out and sum(c[0] == "drag" for c in calls) == 7


def test_block_rejects_off_map_and_bad_zone():
    import pytest

    from agent import toolmap

    with pytest.raises(toolmap.InvalidAction):
        toolmap.validate_action({"type": "block", "x": 500, "y": 380, "zone": "light_residential"})
    with pytest.raises(toolmap.InvalidAction):
        toolmap.validate_action({"type": "block", "x": 200, "y": 260, "zone": "airport"})
