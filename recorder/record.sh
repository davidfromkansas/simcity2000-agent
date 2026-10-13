#!/usr/bin/env bash
# Recorder sidecar.
#   RECORDER_MODE=x11grab (default): ffmpeg grabs the whole X display -> segmented MP4.
#   RECORDER_MODE=dosbox: transcode DOSBox-X native captures (game started with
#                         DOSBOX_CAPTURE=1) from runs/<id>/dosbox-capture/*.avi to MP4.
#   RECORDER_MODE=both:   do both.
set -uo pipefail

RUNS_DIR="${RUNS_DIR:-/runs}"
export DISPLAY="${DISPLAY:-game:99}"
MODE="${RECORDER_MODE:-x11grab}"
FPS="${RECORD_FPS:-10}"
SEGMENT_SECONDS="${SEGMENT_SECONDS:-300}"
CRF="${RECORD_CRF:-23}"

echo "[recorder] waiting for run id and display $DISPLAY"
until [[ -s "$RUNS_DIR/CURRENT_RUN" ]] && xdpyinfo >/dev/null 2>&1; do sleep 1; done
RUN_ID="${RUN_ID:-$(cat "$RUNS_DIR/CURRENT_RUN")}"
VIDEO_DIR="$RUNS_DIR/$RUN_ID/video"
mkdir -p "$VIDEO_DIR/native"
echo "[recorder] run $RUN_ID mode=$MODE segments=${SEGMENT_SECONDS}s -> $VIDEO_DIR"

x11grab_loop() {
  while true; do
    # Fragmented MP4 so the segment being written is already playable in a browser.
    ffmpeg -nostdin -loglevel warning \
      -f x11grab -draw_mouse 1 -framerate "$FPS" -video_size 640x480 -i "$DISPLAY" \
      -c:v libx264 -preset veryfast -tune animation -crf "$CRF" -pix_fmt yuv420p \
      -g "$((FPS * 2))" \
      -f segment -segment_time "$SEGMENT_SECONDS" -segment_format mp4 \
      -segment_format_options movflags=+frag_keyframe+empty_moov+default_base_moof \
      -reset_timestamps 1 -strftime 1 \
      "$VIDEO_DIR/session_%Y%m%d-%H%M%S.mp4"
    echo "[recorder] ffmpeg exited ($?); restarting in 2s"
    sleep 2
  done
}

dosbox_loop() {
  local cap="$RUNS_DIR/$RUN_ID/dosbox-capture"
  while true; do
    for avi in "$cap"/*.avi; do
      [[ -e "$avi" ]] || continue
      local out="$VIDEO_DIR/native/$(basename "${avi%.avi}").mp4"
      [[ -e "$out" ]] && continue
      # Only transcode files DOSBox-X has finished writing (unchanged for 10s).
      if [[ $(( $(date +%s) - $(stat -c %Y "$avi") )) -lt 10 ]]; then continue; fi
      echo "[recorder] transcoding $avi"
      ffmpeg -nostdin -loglevel warning -i "$avi" -c:v libx264 -preset veryfast -crf 18 \
        -pix_fmt yuv420p -c:a aac "$out.tmp.mp4" && mv "$out.tmp.mp4" "$out"
    done
    sleep 15
  done
}

case "$MODE" in
  x11grab) x11grab_loop ;;
  dosbox)  dosbox_loop ;;
  both)    dosbox_loop & x11grab_loop ;;
  *) echo "unknown RECORDER_MODE=$MODE" >&2; exit 2 ;;
esac
