"""Agent loop: screenshot -> brain -> execute -> log -> sleep -> repeat."""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import actions, brain
from .capture import Screen


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


def main() -> int:
    run_dir = Path(os.environ.get("RUN_DIR", "runs")) / datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    step_delay = float(os.environ.get("STEP_DELAY", "1.5"))
    save_every = env_int("SAVE_EVERY", 25)
    max_steps = env_int("MAX_STEPS", 0)
    history_len = env_int("HISTORY", 8)
    save_prefix = os.environ.get("SAVE_NAME", "AGENT")
    game_dir = Path(os.environ.get("GAME_DIR", "/app/games/simcity2000"))

    try:
        policy = brain.from_env()
    except brain.BrainError as e:
        print(f"[agent] {e}; agent disabled (game still running for viewers)", file=sys.stderr)
        return 2
    print(f"[agent] provider={policy.provider} model={policy.model} logging to {run_dir}")

    screen = Screen()
    history: deque[dict[str, Any]] = deque(maxlen=history_len)
    summary = ""
    log = (run_dir / "actions.jsonl").open("a")
    step = 0
    while not max_steps or step < max_steps:
        step += 1
        img = screen.grab()
        shot = run_dir / f"step_{step:05d}.png"
        img.save(shot)
        record: dict[str, Any] = {"step": step, "time": time.time(), "screenshot": shot.name}
        try:
            decision = policy.decide(img, list(history), summary)
            summary = str(decision.get("summary") or summary)
            action = decision["action"]
            result = actions.execute(action)
            record.update(observation=decision.get("observation"), reasoning=decision.get("reasoning"),
                          action=action, result=result, summary=summary)
        except Exception as e:  # keep playing through API hiccups / bad replies
            action, result = {"type": "error"}, f"error: {e}"
            record.update(action=action, result=result, traceback=traceback.format_exc(limit=3))
        history.append({"step": step, "action": action, "result": result})
        log.write(json.dumps(record) + "\n")
        log.flush()
        print(f"[agent] step {step}: {json.dumps(action)} -> {result}", flush=True)

        if save_every and step % save_every == 0:
            try:
                save_name = actions.next_save_name(game_dir, save_prefix)
                actions.save_city(save_name)
                print(f"[agent] saved city as {save_name}.SC2", flush=True)
            except Exception as e:
                print(f"[agent] save failed: {e}", file=sys.stderr)
        time.sleep(step_delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
