# games/

Game binaries are never committed here.

- `fetch.sh` – downloads SimCity 2000 (DOS) from
  <https://archive.org/details/SimCity-2> (`simcity2000.zip`) into
  `games/simcity2000/`. The container runs it automatically on start if
  `SC2000.EXE` is missing. Run it by hand with `./games/fetch.sh`.
  Override the source with `SC2K_ARCHIVE_URL=<zip url>`.
- `dosbox-x.conf` – mounts `games/simcity2000` as `C:` and runs
  `SC2000.EXE NOSOUND` in a fixed 640x480 window.

See the top-level README for the licensing caveat.
