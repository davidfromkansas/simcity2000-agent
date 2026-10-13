# AGENTS.md

Notes for coding agents working on this repo.

## Run / test
* `docker compose up --build`: the full stack. Port 6080 is often taken on dev VMs, so use
  `NOVNC_PORT=16080 VIEWER_PORT=18080 docker compose up`.
* Keyless smoke test: leave the API keys unset (scripted policy) and run with `MAX_STEPS=40`. Then check that
  `runs/<id>/steps.jsonl` lines all point to existing PNGs and that `runs/<id>/video/*.mp4` exists.
* Lint: `python3 -m pyflakes agent viewer`.

## Gotchas (verified by hand)
* The archive.org zip ships `SC2000.EXE`, not `SIMCITY.EXE`.
* `mouse_emulation = never` in `games/dosbox-x.conf` is required. With other modes, xdotool
  coordinates don't map 1:1 to the DOS cursor.
* Xvfb, DOSBox-X and every coordinate in `agent/toolmap.py` assume an unscaled
  640x480 window at (0,0). If you change the scaler/window size, re-measure every coordinate.
* Toolbar popups open on mouse *press* and pick on *release*, so use `input.press_and_pick`
  rather than two clicks. Menu-bar items work the same way.
* Escape does **not** close SimCity's "Select / Raised Wires" popup. Click `dialog.wires.none`.
* The city view at default zoom is `toolmap.CITY_VIEW`. Tiles step (8,4) along i and (-8,4) along j.
* Saving: Alt+S writes `<CITYNAME>.SC2` into the game dir. The agent copies it to `runs/<id>/saves/`.
* Never commit game files (`games/sc2000/`, `*.SC2`, `*.EXE`) or anything under `runs/`.
