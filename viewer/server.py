"""Tiny stdlib web server: viewer page + JSON index of runs + static files from runs/."""
from __future__ import annotations

import argparse
import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    runs: Path = Path("/runs")

    def log_message(self, fmt, *args):  # quieter logs
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._file(HERE / "index.html", "text/html")
        if url.path == "/api/runs":
            return self._json(self._list_runs())
        if url.path == "/api/steps":
            q = parse_qs(url.query)
            return self._json(self._steps(q.get("run", [""])[0],
                                          int(q.get("offset", ["0"])[0]),
                                          int(q.get("limit", ["200"])[0])))
        if url.path.startswith("/runs/"):
            rel = url.path[len("/runs/"):]
            target = (self.runs / rel).resolve()
            if self.runs.resolve() not in target.parents or not target.is_file():
                return self.send_error(404)
            return self._file(target)
        return self.send_error(404)

    def _file(self, path: Path, ctype: str | None = None):
        ctype = ctype or self.guess_type(str(path))
        size = path.stat().st_size
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else max(0, size - int(b))
            end = int(b) if a and b else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(1 << 16, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _list_runs(self):
        current = (self.runs / "CURRENT_RUN").read_text().strip() if (self.runs / "CURRENT_RUN").exists() else ""
        out = []
        for d in sorted((p for p in self.runs.iterdir() if p.is_dir()), reverse=True):
            steps = d / "steps.jsonl"
            videos = sorted(str(p.relative_to(self.runs)) for p in (d / "video").rglob("*.mp4")) if (d / "video").exists() else []
            saves = sorted(str(p.relative_to(self.runs)) for p in (d / "saves").glob("*")) if (d / "saves").exists() else []
            n = sum(1 for _ in steps.open()) if steps.exists() else 0
            out.append({"id": d.name, "current": d.name == current, "steps": n,
                        "videos": videos, "saves": saves})
        return {"current": current, "runs": out}

    def _steps(self, run: str, offset: int, limit: int):
        path = (self.runs / run / "steps.jsonl").resolve()
        if self.runs.resolve() not in path.parents or not path.exists():
            return {"steps": [], "total": 0}
        lines = path.read_text().splitlines()
        total = len(lines)
        sel = lines[::-1][offset:offset + limit]  # newest first
        return {"total": total, "steps": [json.loads(l) for l in sel if l.strip()]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("VIEWER_PORT", "8080")))
    ap.add_argument("--runs", default=os.environ.get("RUNS_DIR", "/runs"))
    args = ap.parse_args()
    Handler.runs = Path(args.runs)
    srv = ThreadingHTTPServer(("0.0.0.0", args.port), partial(Handler))
    print(f"viewer on :{args.port} serving {args.runs}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
