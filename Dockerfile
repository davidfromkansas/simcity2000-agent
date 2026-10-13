FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    SDL_AUDIODRIVER=dummy

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      dosbox-x xvfb x11vnc novnc websockify xdotool x11-utils \
      ffmpeg python3 python3-venv curl unzip ca-certificates tini procps \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && pip install --no-cache-dir -r /tmp/requirements.txt

WORKDIR /app
COPY . /app
RUN chmod +x /app/games/*.sh /app/recorder/*.sh 2>/dev/null || true

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/app/games/start-game.sh"]
