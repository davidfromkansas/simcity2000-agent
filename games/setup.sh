#!/usr/bin/env bash
# Fetch SimCity 2000 (DOS) from archive.org at runtime. Nothing is committed to git.
# Idempotent: skips the download if SC2000.EXE is already present in $GAME_DIR.
set -euo pipefail

GAME_DIR="${GAME_DIR:-/games/sc2000}"
GAME_ZIP_URL="${GAME_ZIP_URL:-https://archive.org/download/SimCity-2/simcity2000.zip}"
GAME_ZIP_SHA256="${GAME_ZIP_SHA256:-ba64e0314abd21f58249373fbb812bd25074e5efe9d6a039eb0014fdd7468043}"

mkdir -p "$GAME_DIR"
if [[ -f "$GAME_DIR/SC2000.EXE" ]]; then
  echo "[setup] game already present in $GAME_DIR"
  exit 0
fi

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "[setup] downloading $GAME_ZIP_URL"
curl -fL --retry 5 --retry-delay 3 -o "$tmp/sc2000.zip" "$GAME_ZIP_URL"

if [[ -n "$GAME_ZIP_SHA256" ]]; then
  echo "$GAME_ZIP_SHA256  $tmp/sc2000.zip" | sha256sum -c -
fi

unzip -q -o "$tmp/sc2000.zip" -d "$GAME_DIR"
# Some mirrors nest the files one directory deep; flatten so SC2000.EXE sits at C:\.
if [[ ! -f "$GAME_DIR/SC2000.EXE" ]]; then
  inner="$(dirname "$(find "$GAME_DIR" -iname SC2000.EXE | head -1)")"
  [[ -n "$inner" && "$inner" != "." ]] && cp -a "$inner"/. "$GAME_DIR"/
fi
test -f "$GAME_DIR/SC2000.EXE" || { echo "[setup] SC2000.EXE not found after unzip" >&2; exit 1; }
echo "[setup] installed SimCity 2000 into $GAME_DIR"
