# simcity2000-agent

A self-contained cloud setup in which a vision LLM plays **SimCity 2000 (DOS, 1993)**.
One container runs DOSBox-X on a headless X display; the agent looks at
screenshots and moves the mouse/keyboard with `xdotool`; you watch live in a
browser through noVNC.

```
 Xvfb :1 (640x480) ── DOSBox-X ── SC2000.EXE
     │      ▲
     │      └── xdotool (agent/input.py)  ◄── agent/actions.py ◄── JSON action
     ├── mss screenshot (agent/capture.py) ──► agent/brain.py (Anthropic / OpenAI vision)
     └── x11vnc ── websockify/noVNC :6080 ──► your browser
```

## Quick start

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # or OPENAI_API_KEY=sk-...
docker compose up --build
```

Open <http://localhost:6080/> and watch. On first start the container
downloads the game from the Internet Archive into `games/simcity2000/`
(cached on the host for later runs), boots DOSBox-X and, after a short delay,
starts the agent loop. The agent picks "Start New City", then builds power,
roads and zones on its own.

Useful settings (env vars or a `.env` file next to `docker-compose.yml`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | – | API key; provider is picked from whichever is set |
| `LLM_PROVIDER` | auto | force `anthropic` or `openai` |
| `LLM_MODEL` | `claude-sonnet-4-5` / `gpt-4o` | any vision-capable model |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | point at any OpenAI-compatible endpoint |
| `NOVNC_PORT` | `6080` | host port for the browser viewer |
| `STEP_DELAY` | `1.5` | seconds to sleep between actions |
| `SAVE_EVERY` | `25` | save the city every N steps (`0` = never) |
| `MAX_STEPS` | `0` | stop after N steps (`0` = forever) |
| `AGENT_ENABLED` | `1` | `0` = only run the game (play it yourself over VNC) |
| `VNC_VIEW_ONLY` | empty | set to `1` so browser viewers can't send input |
| `RECORD` | `0` | `1` = record the screen to `runs/screen-*.mp4` with ffmpeg |

Without an API key the game still runs and is viewable; the agent just logs
that it is disabled.

## How the agent loop works

`python -m agent.main` (started by `docker/entrypoint.sh`):

1. **Capture** – `capture.py` grabs the fixed 640x480 region at (0, 0) of the
   Xvfb display with `mss`. DOSBox-X is configured to render the game 1:1 and
   the entrypoint pins its window to (0, 0), so a screenshot pixel is a game pixel.
2. **Think** – `brain.py` sends the screenshot (with a faint labelled 40 px grid
   overlay to help the model read coordinates), the last few actions and their
   results, the model's own running notes, and the list of named tools/menus/buttons.
   The model must reply with one strict JSON object:
   ```json
   {"observation": "...", "reasoning": "...",
    "action": {"type": "select_tool", "tool": "light_residential"},
    "summary": "running notes carried to the next turn"}
   ```
   Replies are parsed and validated against `toolmap.py`; an invalid reply is
   retried once with the error message, then logged as an error step.
3. **Act** – `actions.py` turns the action into input via `input.py`:
   `select_tool`, `menu`, `button` (all by name), `click`/`drag` (raw map pixels),
   `key`, `type`, `wait`.
4. **Log** – every step writes `runs/<timestamp>/step_NNNNN.png` and a line in
   `runs/<timestamp>/actions.jsonl` (observation, reasoning, action, result, notes).
5. **Save** – every `SAVE_EVERY` steps the loop runs the game's own
   *File → Save City As…* and saves the next free `AGENTnnn.SC2` (prefix via
   `SAVE_NAME`) to the C: drive
   (`games/simcity2000/` on the host). Reload it from the title screen with
   *Load Saved City*.
6. Sleep `STEP_DELAY`, repeat.

## Tuning

### The prompt

`SYSTEM_PROMPT` in `agent/brain.py` holds the strategy. The order of priorities
matters: modal dialogs are always resolved first (newspaper, budget, power-plant
chooser, bridge prompt, file dialogs), then power, zoning and budget. Edit the
strategy text freely; keep the JSON contract and action list in sync with
`toolmap.validate_action`.

### The toolmap

`agent/toolmap.py` contains every coordinate the agent uses, measured from real
screenshots at 640x480:

- `TOOLBAR` – the left palette's parent buttons.
- `SUBTOOLS` – pop-up items as `(parent, index)`; the item sits at
  `parent_y + 8 + 16 * index`. Selecting one presses the parent, slides to the
  item and releases (`input.hold_and_pick`).
- `MENU_TITLES` / `MENU_ITEMS` – the menu bar (same press-slide-release gesture).
- `BUTTONS` – dialog buttons, title screen, New City dialog, save dialog, etc.

To add or fix one: run with `AGENT_ENABLED=0`, open noVNC, hover the element,
and read the coordinates from a screenshot (`docker compose exec sc2k-agent
python3 -c "from agent.capture import Screen; Screen().grab().save('/app/runs/shot.png')"`).
Add the name to the dict and to the prompt if it needs special guidance.
`pytest` checks that every coordinate is on screen and that every sub-tool
points at a real parent button.

### Display/input notes (learned the hard way)

- There is deliberately **no window manager**: with one, DOSBox-X loops forever
  resizing its 720x400 text-mode window at boot. Instead the entrypoint keeps the
  window at (0, 0) and gives it keyboard focus every 2 s.
- `mouse_emulation = never` + fullscreen keeps the DOS mouse 1:1 with X pointer moves.
- Do not set a custom DOSBox-X `mapperfile` with only a few entries – it unbinds
  every other key and keyboard input silently stops working.
- SimCity polls the mouse, so clicks are held ~120 ms (`CLICK_HOLD`).

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest ruff
.venv/bin/ruff check . && .venv/bin/python -m pytest -q
```

## Game files and licensing

SimCity 2000 is © 1993 Maxis / Electronic Arts and is **not** free software.
This repo contains no game files. `games/fetch.sh` downloads the copy hosted at
<https://archive.org/details/SimCity-2> at setup time into the git-ignored
`games/simcity2000/` directory. Whether you may download and run it depends on
your jurisdiction and on owning a licence; it is your responsibility. To use your
own copy instead, put the game files (containing `SC2000.EXE`) in
`games/simcity2000/` before starting, or set `SC2K_ARCHIVE_URL` to another zip.

Note: the game's executable in this release is `SC2000.EXE` (there is no
`SIMCITY.EXE`); `games/dosbox-x.conf` launches `SC2000.EXE NOSOUND`.
