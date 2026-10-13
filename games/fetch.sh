#!/usr/bin/env bash
# Download SimCity 2000 (DOS) from the Internet Archive into games/simcity2000/.
# Runs automatically on container start when the game dir is empty.
set -euo pipefail

ITEM_URL="${SC2K_ARCHIVE_URL:-https://archive.org/download/SimCity-2/simcity2000.zip}"
DEST="${1:-$(dirname "$0")/simcity2000}"

if [ -f "$DEST/SC2000.EXE" ]; then
  echo "[fetch] SimCity 2000 already present in $DEST"
  exit 0
fi

mkdir -p "$DEST"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
echo "[fetch] downloading $ITEM_URL"
curl -fL --retry 3 -o "$tmp/sc2k.zip" "$ITEM_URL"
unzip -q -o "$tmp/sc2k.zip" -d "$DEST"
test -f "$DEST/SC2000.EXE" || { echo "[fetch] SC2000.EXE not found after unzip" >&2; exit 1; }
echo "[fetch] installed to $DEST"
