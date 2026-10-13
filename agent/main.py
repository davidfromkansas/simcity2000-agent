"""Agent loop: screenshot -> brain -> execute -> log -> repeat (+ periodic saves).

Every decision writes runs/<run_id>/steps/<step>.png (the frame the decision was made
on) and appends one JSON line to runs/<run_id>/steps.jsonl.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from . import capture, executor, toolmap
from . import input as inp
from .brain import LLMBrain
from .scripted import ScriptedPolicy

RUNS = Path(os.environ.get("RUNS_DIR", "/runs"))
GAME_DIR = Path(os.environ.get("GAME_DIR", "/games/sc2000"))
_stop = False


def _on_signal(*_):
    global _stop
    _stop = True


def wait_for_game(timeout: float = 300) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if subprocess.run(["xdpyinfo"], capture_output=True).returncode == 0 and inp.window_id():
            return
        time.sleep(2)
    raise SystemExit("DOSBox-X window never appeared on " + os.environ.get("DISPLAY", "?"))


def resolve_run_id(cli: str | None) -> str:
    if cli or os.environ.get("RUN_ID"):
        return cli or os.environ["RUN_ID"]
    marker = RUNS / "CURRENT_RUN"
    for _ in range(60):
        if marker.exists() and marker.read_text().strip():
            return marker.read_text().strip()
        time.sleep(1)
    return "run-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


class SaveManager:
    """Triggers File > Save City (Alt+S) and copies the .SC2 into runs/<id>/saves/."""

    def __init__(self, run_dir: Path):
        self.dir = run_dir / "saves"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.last = time.time()

    def _newest_since(self, t: float):
        files = [p for p in GAME_DIR.glob("*.[Ss][Cc]2") if p.stat().st_mtime >= t - 1]
        return max(files, key=lambda p: p.stat().st_mtime) if files else None

    def save(self) -> str | None:
        before = time.time()
        inp.key(toolmap.HOTKEYS["save_city"])
        time.sleep(3)
        inp.key("Return")  # dismiss a "Save City As" / confirmation box if one is up
        newest = self._newest_since(before)
        if newest is None:  # hotkey can be swallowed mid-drag/popup; fall back to the menu
            menu, item = toolmap.MENU_ITEMS["file.save_city"]
            inp.press_and_pick(*toolmap.MENUS[menu], *item)
            time.sleep(3)
            inp.key("Return")
            newest = self._newest_since(before)
        self.last = time.time()
        if newest is None:
            return None
        dst = self.dir / f"{dt.datetime.now(dt.timezone.utc):%Y%m%d-%H%M%S}_{newest.name}"
        shutil.copy2(newest, dst)
        return str(dst.relative_to(RUNS))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id")
    ap.add_argument("--policy", default=os.environ.get("AGENT_POLICY", "auto"),
                    choices=["auto", "llm", "scripted"])
    ap.add_argument("--max-steps", type=int, default=int(os.environ.get("MAX_STEPS", "0")))
    ap.add_argument("--step-delay", type=float, default=float(os.environ.get("STEP_DELAY_SECONDS", "2")))
    ap.add_argument("--save-every", type=float, default=float(os.environ.get("SAVE_EVERY_SECONDS", "300")))
    args = ap.parse_args()

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    run_id = resolve_run_id(args.run_id)
    run_dir = RUNS / run_id
    (run_dir / "steps").mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "steps.jsonl"
    print(f"[agent] run {run_id} -> {run_dir}", flush=True)

    wait_for_game()
    use_llm = args.policy == "llm" or (args.policy == "auto" and LLMBrain.available())
    policy = LLMBrain() if use_llm else ScriptedPolicy()
    policy_name = f"llm:{policy.provider}:{policy.model}" if use_llm else "scripted"
    print(f"[agent] policy: {policy_name}", flush=True)
    saver = SaveManager(run_dir)

    history: list[dict] = []
    step = sum(1 for _ in log_path.open()) if log_path.exists() else 0
    while not _stop and (args.max_steps <= 0 or step < args.max_steps):
        ts = dt.datetime.now(dt.timezone.utc)
        img = capture.screenshot()
        shot_rel = f"steps/{step:06d}.png"
        capture.save_png(img, str(run_dir / shot_rel))
        png = capture.to_png_bytes(img)

        if use_llm:
            decision = policy.decide(png, history)
        else:
            decision = policy.decide(png, history, img=img)

        results = [executor.run(a, save_fn=saver.save) for a in decision.actions]
        record = {
            "step": step,
            "timestamp": ts.isoformat(timespec="milliseconds"),
            "unix": round(ts.timestamp(), 3),
            "screenshot": shot_rel,
            "policy": policy_name,
            "observation": decision.observation,
            "reasoning": decision.reasoning,
            "actions": decision.actions,
            "results": results,
            "latency_s": decision.latency_s,
            "usage": decision.usage,
        }
        if args.save_every > 0 and time.time() - saver.last > args.save_every:
            record["periodic_save"] = saver.save()
        with log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"[agent] #{step} {decision.reasoning[:100]} -> {[a['type'] for a in decision.actions]}", flush=True)
        history.append(record)
        history = history[-20:]
        step += 1
        time.sleep(args.step_delay)

    print("[agent] stopping; final save", flush=True)
    try:
        saver.save()
    except Exception as exc:  # noqa: BLE001
        print(f"[agent] final save failed: {exc}", flush=True)


if __name__ == "__main__":
    main()
