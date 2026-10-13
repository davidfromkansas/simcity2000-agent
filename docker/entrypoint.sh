#!/usr/bin/env bash
set -euo pipefail

GAME_DIR=/app/games/simcity2000
RUN_DIR=${RUN_DIR:-/app/runs}
mkdir -p "$RUN_DIR"

/app/games/fetch.sh "$GAME_DIR"

rm -f "/tmp/.X${DISPLAY#:}-lock" "/tmp/.X11-unix/X${DISPLAY#:}"
echo "[entrypoint] starting Xvfb on $DISPLAY (${SCREEN_W}x${SCREEN_H})"
Xvfb "$DISPLAY" -screen 0 "${SCREEN_W}x${SCREEN_H}x24" -nolisten tcp -ac >/tmp/xvfb.log 2>&1 &
for _ in $(seq 50); do xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && break; sleep 0.1; done

x11vnc -display "$DISPLAY" -forever -shared -nopw -quiet -rfbport 5900 ${VNC_VIEW_ONLY:+-viewonly} >/tmp/x11vnc.log 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/tmp/websockify.log 2>&1 &
echo "[entrypoint] noVNC: http://localhost:${NOVNC_HOST_PORT:-6080}/"

# Keep the emulator alive: if the game quits or crashes, relaunch it.
(
  while true; do
    dosbox-x -conf /app/games/dosbox-x.conf >/tmp/dosbox.log 2>&1 || true
    echo "[entrypoint] dosbox-x exited; restarting in 2s"
    sleep 2
  done
) &
DOSBOX_LOOP_PID=$!

# No window manager: keep the DOSBox-X window pinned at (0,0) (it centres its
# 720x400 text-mode window at boot) and give it keyboard focus so xdotool
# keystrokes reach the game.
(
  while true; do
    W=$(xdotool search --name DOSBox 2>/dev/null | head -1 || true)
    if [ -n "$W" ]; then
      xdotool windowmove "$W" 0 0 2>/dev/null || true
      [ "$(xdotool getwindowfocus 2>/dev/null)" = "$W" ] || xdotool windowfocus "$W" 2>/dev/null || true
    fi
    sleep 2
  done
) &

if [ "${RECORD:-0}" = "1" ]; then
  ffmpeg -loglevel error -y -f x11grab -framerate "${RECORD_FPS:-5}" \
    -video_size "${SCREEN_W}x${SCREEN_H}" -i "$DISPLAY" \
    -c:v libx264 -preset veryfast -pix_fmt yuv420p \
    "$RUN_DIR/screen-$(date +%Y%m%d-%H%M%S).mp4" &
fi

if [ "${AGENT_ENABLED:-1}" = "1" ]; then
  sleep "${AGENT_START_DELAY:-8}"
  echo "[entrypoint] starting agent loop"
  python3 -m agent.main &
fi

wait "$DOSBOX_LOOP_PID"
