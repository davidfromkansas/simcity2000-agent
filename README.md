# simcity2000-agent

An LLM agent that plays **SimCity 2000 (DOS)** in the cloud by looking at the screen and
clicking, the way a person would. The game runs in DOSBox-X on a virtual display. You can
watch it live in a browser, and every session is recorded to MP4 along with a
screenshot of every decision the agent made.

```
┌──────────── game ────────────┐   ┌──── agent ────┐   ┌─── recorder ───┐
│ Xvfb :99 (640x480)           │◄──│ screenshot    │   │ ffmpeg x11grab │
│ DOSBox-X → SC2000.EXE        │   │ → LLM (JSON)  │   │ 5-min MP4s     │
│ x11vnc → noVNC :6080         │   │ → xdotool     │   │ (+ DOSBox-X    │
│ viewer :8080                 │   │ → log + save  │   │  native AVI)   │
└──────────────┬───────────────┘   └───────┬───────┘   └───────┬────────┘
               └──────────── ./runs/<run_id>/ (shared volume) ─┘
```

## Run it

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # or OPENAI_API_KEY=... (optional, see below)
docker compose up --build
```

* **Live view:** <http://localhost:6080/vnc.html?autoconnect=1&resize=scale>
* **Dashboard** (live view + recordings + decision log): <http://localhost:8080>

On first start, the `game` container downloads the game from archive.org into a Docker
volume (`game-data`). Later starts reuse that copy.

Without an API key, the agent falls back to a built-in **scripted policy**. It goes
through the same screenshot → decide → act → log loop and builds a starter town
(new city, coal plant, roads, power lines, R/C/I zones), so you can check the whole
stack without spending anything.

Useful settings (environment variables or `.env`):

| Variable | Default | Meaning |
|---|---|---|
| `AGENT_POLICY` | `auto` | `auto` (LLM if a key is set, otherwise scripted), `llm`, `scripted` |
| `LLM_PROVIDER` / `LLM_MODEL` | auto / provider default | `anthropic` or `openai`, plus the model name |
| `OPENAI_BASE_URL` | OpenAI | any OpenAI-compatible vision endpoint |
| `STEP_DELAY_SECONDS` | `2` | pause between decisions |
| `SAVE_EVERY_SECONDS` | `300` | how often the city is saved |
| `MAX_STEPS` | `0` (forever) | stop after N decisions |
| `SEGMENT_SECONDS` | `300` | length of each MP4 chunk |
| `RECORDER_MODE` | `x11grab` | `x11grab`, `dosbox` (native capture only) or `both` |
| `DOSBOX_CAPTURE` | `0` | `1` = also turn on DOSBox-X's own video capture |
| `NOVNC_PORT` / `VIEWER_PORT` | `6080` / `8080` | host ports |
| `VNC_VIEW_ONLY` | `1` | set to `0` to let viewers use the mouse too |

## Where everything lands

```
runs/
  CURRENT_RUN                 id of the session in progress
  <run_id>/
    steps.jsonl               one JSON line per decision
    steps/000123.png          the exact frame decision #123 was made from
    video/session_*.mp4       ffmpeg x11grab, 5-minute segments
    video/native/*.mp4        DOSBox-X native capture, transcoded (when enabled)
    dosbox-capture/*.avi      raw DOSBox-X capture (when enabled)
    saves/*.SC2               periodic city saves
    logs/                     emulator / vnc logs
```

Each `steps.jsonl` record contains `step`, `timestamp`, `screenshot`, `policy`,
`observation`, `reasoning`, `actions`, `results` and, for the LLM policy, `latency_s` and
token `usage`. Every record points to a PNG saved before its actions ran.

## How the agent decides

1. **Capture**: `agent/capture.py` grabs the fixed 640x480 game frame (mss, then pyautogui, then
   ffmpeg as fallbacks).
2. **Think**: `agent/brain.py` sends the frame, the last few decisions and the named control map
   from `agent/toolmap.py` to a vision LLM. The model must return strict JSON:
   ```json
   {"observation": "...", "reasoning": "...",
    "actions": [{"type": "tool", "name": "road"},
                {"type": "drag", "from": [260, 240], "to": [420, 320]}]}
   ```
   The prompt sets priorities in this order: **close any dialog first**, then start a city,
   then **power, roads, zoning (R/C/I), water, budget**, then services and growth.
   Anything off-schema (an unknown target, bad coordinates, more than 5 actions) is
   rejected, and the model is asked again.
3. **Act**: `agent/executor.py` turns the actions into `xdotool` input (`agent/input.py`). Named
   targets like `dialog.budget.done` or tools like `light_residential` are resolved from
   hardcoded coordinates, so the model doesn't have to guess where the buttons are.
4. **Log & save**: the screenshot, decision, results and timestamp are written to
   `runs/<run_id>/`. Every `SAVE_EVERY_SECONDS` the agent presses Alt+S and copies the
   `.SC2` file into `saves/`.

The scripted fallback (`agent/scripted.py`) uses simple pixel checks to tell which screen
it's on (title, editor, budget, newspaper, popup, city). It looks for an open patch of
dry land in the screenshot and lays a small town out on the tile grid.

## Game files and licensing

**No game files are in this repo.** `games/setup.sh` downloads `simcity2000.zip` from
<https://archive.org/details/SimCity-2> when the container starts and checks its
SHA-256. SimCity 2000 is © 1993 Maxis / Electronic Arts and is still under copyright.
Archive.org hosting it doesn't give you a license. Only use it if you're legally
allowed to (for example, you own a copy), and don't redistribute the files or the
`game-data` volume. You can point `GAME_ZIP_URL` (and `GAME_ZIP_SHA256`) at your own copy.

## Layout

```
Dockerfile            Ubuntu 24.04 + dosbox-x, xvfb, x11vnc, novnc/websockify, xdotool, ffmpeg, python
docker-compose.yml    game / agent / recorder, shared ./runs
games/                setup.sh (download), dosbox-x.conf, start-game.sh
agent/                capture, input, toolmap, brain, scripted, executor, main
recorder/record.sh    segmented MP4 recorder + DOSBox-X capture transcoder
viewer/               dashboard (server.py + index.html)
```
