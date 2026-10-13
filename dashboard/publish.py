"""Publish the live city dashboard (stats, screenshots, activity feed) to gh-pages.

Builds ``timeline.json`` plus JPEG screenshots in a gh-pages worktree, commits and
pushes. Run from the repo root, e.g. every 5 minutes:

    .venv/bin/python dashboard/publish.py --pages-dir ../simcity2000-pages --every 300
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent.sc2 import read_stats  # noqa: E402

GAMES = ROOT / "games" / "simcity2000"
RUNS = ROOT / "runs"
CONTROL = RUNS / "control"
CONTAINER = "simcity2000-agent-sc2k-agent-1"
STAT_KEYS = ("date", "year", "funds", "population", "crime", "pollution",
             "work_force_pct", "education_eq", "demand_r", "demand_c", "demand_i")
GRAB = ("import mss,mss.tools;s=mss.mss();"
        "i=s.grab({'left':0,'top':0,'width':640,'height':480});"
        "mss.tools.to_png(i.rgb,i.size,output='/app/runs/control/live.png')")


def latest_run() -> Path:
    return max((p.parent for p in RUNS.glob("*/actions.jsonl")), key=lambda p: p.name)


def load_actions(run: Path) -> list[dict]:
    out = []
    for line in (run / "actions.jsonl").read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_saves(since: float) -> list[dict]:
    saves = []
    for f in GAMES.glob("AGENT*.SC2"):
        mtime = f.stat().st_mtime
        if mtime < since:
            continue
        try:
            stats = read_stats(f)
        except Exception:
            continue
        saves.append({"t": mtime, "file": f.name, **{k: stats.get(k) for k in STAT_KEYS}})
    return sorted(saves, key=lambda s: s["t"])


def feed_items(actions: list[dict]) -> list[dict]:
    """Group consecutive steps that share one decision summary into a feed item."""
    items: list[dict] = []
    for a in actions:
        summary = a.get("summary") or ""
        result = str(a.get("result") or "")
        if not (items and summary and items[-1]["summary"] == summary):
            items.append({"kind": "action", "t": a.get("time"), "step": a.get("step"),
                          "summary": summary, "actions": [], "errors": 0})
        item = items[-1]
        item["t_end"], item["step_end"] = a.get("time"), a.get("step")
        if (a.get("action") or {}).get("type") != "wait":
            item["actions"].append(result[:140])
        if result.startswith("error"):
            item["errors"] += 1
    return items


def journal_entries() -> list[dict]:
    """Journal paragraphs, each timestamped by when its newest line was committed."""
    blame = subprocess.run(["git", "blame", "--line-porcelain", "JOURNAL.md"], cwd=ROOT,
                           capture_output=True, text=True).stdout
    lines: list[tuple[int, str]] = []
    t = int(time.time())
    for row in blame.splitlines():
        if row.startswith("committer-time "):
            t = int(row.split()[1])
        elif row.startswith("\t"):
            lines.append((t, row[1:]))
    entries, buf, newest = [], [], 0
    for t, text in [*lines, (0, "")]:
        if text.strip():
            buf.append(text)
            newest = max(newest, t)
        elif buf:
            entries.append({"kind": "journal", "t": newest, "text": "\n".join(buf)})
            buf, newest = [], 0
    return entries


def save_jpg(src: Path, pages: Path) -> str:
    data = io.BytesIO()
    Image.open(src).convert("RGB").save(data, "JPEG", quality=82)
    name = f"shots/{hashlib.sha1(data.getvalue()).hexdigest()[:12]}.jpg"
    if not (pages / name).exists():
        (pages / "shots").mkdir(parents=True, exist_ok=True)
        (pages / name).write_bytes(data.getvalue())
    return name


def live_frame() -> Path:
    try:
        r = subprocess.run(["docker", "exec", "-e", "DISPLAY=:1", CONTAINER, "python3", "-c", GRAB],
                           capture_output=True, timeout=30)
        if r.returncode == 0 and (CONTROL / "live.png").exists():
            return CONTROL / "live.png"
    except (OSError, subprocess.TimeoutExpired):
        pass
    return CONTROL / "screen.png"


def stats_at(saves: list[dict], t: float) -> dict | None:
    current = None
    for s in saves:
        if s["t"] > t:
            break
        current = s
    return current


def build(pages: Path, history_every: int) -> None:
    run = latest_run()
    actions = load_actions(run)
    saves = load_saves(actions[0]["time"] - 120 if actions else 0)
    tl_path = pages / "timeline.json"
    snaps = json.loads(tl_path.read_text())["snapshots"] if tl_path.exists() else []
    have = {s["step"] for s in snaps if s["kind"] == "history"}
    for a in actions[::history_every]:
        shot = run / str(a.get("screenshot"))
        if a.get("step") not in have and shot.is_file():
            snaps.append({"kind": "history", "t": a["time"], "step": a["step"],
                          "shot": save_jpg(shot, pages)})
    now = time.time()
    snaps.append({"kind": "live", "t": now, "step": actions[-1]["step"] if actions else 0,
                  "shot": save_jpg(live_frame(), pages)})
    snaps.sort(key=lambda s: s["t"])
    for s in snaps:
        s["stats"] = stats_at(saves, s["t"])
    feed = sorted(feed_items(actions) + journal_entries(), key=lambda e: e["t"] or 0)
    maps = [{"t": m.stat().st_mtime, "shot": save_jpg(m, pages)}
            for m in sorted((CONTROL / "maps").glob("*.png"))]
    timeline = {"generated": now, "goal": 10000, "run": run.name, "snapshots": snaps, "maps": maps,
                "saves": saves, "feed": feed[-1500:],
                "last_action": {k: actions[-1].get(k) for k in ("step", "time", "summary")}
                if actions else None}
    tl_path.write_text(json.dumps(timeline, separators=(",", ":")))
    shutil.copy(ROOT / "dashboard" / "index.html", pages / "index.html")
    shutil.copy(ROOT / "JOURNAL.md", pages / "journal.md")
    (pages / ".nojekyll").touch()


def publish(pages: Path, push: bool) -> None:
    subprocess.run(["git", "add", "-A"], cwd=pages, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=pages).returncode == 0:
        return
    stamp = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    subprocess.run(["git", "commit", "-qm", f"Dashboard update {stamp}"], cwd=pages, check=True)
    for _ in range(3) if push else ():
        r = subprocess.run(["git", "push", "-q", "origin", "HEAD:gh-pages"], cwd=pages,
                           capture_output=True, text=True)
        if r.returncode == 0:
            return
        time.sleep(5)
    if push:
        print("push failed:", r.stderr[-300:], file=sys.stderr, flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages-dir", type=Path, default=ROOT.parent / "simcity2000-pages")
    ap.add_argument("--every", type=int, default=300, help="seconds between publishes; 0 = once")
    ap.add_argument("--history-every", type=int, default=15,
                    help="backfill one screenshot every N agent steps")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()
    while True:
        try:
            build(args.pages_dir, args.history_every)
            publish(args.pages_dir, not args.no_push)
            print(time.strftime("%H:%M:%S"), "published", flush=True)
        except Exception as e:  # keep the publisher alive between rounds
            print("publish error:", repr(e), file=sys.stderr, flush=True)
        if args.every <= 0:
            break
        time.sleep(args.every)


if __name__ == "__main__":
    main()
