#!/usr/bin/env bash
# Game service: Xvfb (640x480) + DOSBox-X running SimCity 2000 + x11vnc + noVNC + viewer.
set -euo pipefail

export DISPLAY_NUM="${DISPLAY_NUM:-99}"
export DISPLAY=":${DISPLAY_NUM}"
RUNS_DIR="${RUNS_DIR:-/runs}"
GAME_DIR="${GAME_DIR:-/games/sc2000}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
VIEWER_PORT="${VIEWER_PORT:-8080}"
DOSBOX_CAPTURE="${DOSBOX_CAPTURE:-0}"   # 1 = also record native DOSBox-X AVI via DX-CAPTURE

RUN_ID="${RUN_ID:-run-$(date -u +%Y%m%d-%H%M%S)}"
RUN_DIR="$RUNS_DIR/$RUN_ID"
mkdir -p "$RUN_DIR"/{steps,video,dosbox-capture,saves,logs}
echo "$RUN_ID" > "$RUNS_DIR/CURRENT_RUN"
echo "[game] run id: $RUN_ID"

/app/games/setup.sh

rm -f "/tmp/.X${DISPLAY_NUM}-lock" "/tmp/.X11-unix/X${DISPLAY_NUM}"
# TCP listener so the agent/recorder containers can reach the display as game:99.
# Port 6000+N is never published outside the compose network.
Xvfb "$DISPLAY" -screen 0 640x480x24 -listen tcp -ac -nocursor >"$RUN_DIR/logs/xvfb.log" 2>&1 &
for _ in $(seq 1 50); do xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break; sleep 0.2; done

vnc_auth=(-nopw)
if [[ -n "${VNC_PASSWORD:-}" ]]; then
  x11vnc -storepasswd "$VNC_PASSWORD" /tmp/vncpass >/dev/null
  vnc_auth=(-rfbauth /tmp/vncpass)
fi
view_only=()
[[ "${VNC_VIEW_ONLY:-1}" == "1" ]] && view_only=(-viewonly)
x11vnc -display "$DISPLAY" -forever -shared -rfbport 5900 -noxdamage -quiet \
  "${vnc_auth[@]}" "${view_only[@]}" >"$RUN_DIR/logs/x11vnc.log" 2>&1 &

websockify --web /usr/share/novnc "$NOVNC_PORT" localhost:5900 >"$RUN_DIR/logs/novnc.log" 2>&1 &
python3 /app/viewer/server.py --port "$VIEWER_PORT" --runs "$RUNS_DIR" >"$RUN_DIR/logs/viewer.log" 2>&1 &

conf=/app/games/dosbox-x.conf
if [[ "$DOSBOX_CAPTURE" == "1" ]]; then
  # Native-resolution fallback recording: wrap the game in DX-CAPTURE (AVI/ZMBV).
  sed 's/^SC2000\.EXE$/DX-CAPTURE \/V SC2000.EXE/' "$conf" > /tmp/dosbox-x.capture.conf
  conf=/tmp/dosbox-x.capture.conf
fi

echo "[game] noVNC:  http://localhost:${NOVNC_PORT}/vnc.html?autoconnect=1&resize=scale"
echo "[game] viewer: http://localhost:${VIEWER_PORT}/"
while true; do
  dosbox-x -conf "$conf" -fastlaunch -nomenu \
    -set "dosbox captures=$RUN_DIR/dosbox-capture" \
    >>"$RUN_DIR/logs/dosbox.log" 2>&1 || true
  echo "[game] dosbox-x exited; restarting in 3s" | tee -a "$RUN_DIR/logs/dosbox.log"
  sleep 3
done
