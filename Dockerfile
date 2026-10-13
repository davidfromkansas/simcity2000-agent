FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    DISPLAY=:1 \
    SCREEN_W=640 \
    SCREEN_H=480 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        dosbox-x \
        xvfb x11vnc novnc websockify \
        xdotool x11-utils \
        ffmpeg \
        python3 python3-pip python3-venv \
        curl unzip ca-certificates fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV PATH=/opt/venv/bin:$PATH

COPY agent/ agent/
COPY games/ games/
COPY docker/ docker/
RUN chmod +x docker/*.sh games/*.sh \
    && cp docker/index.html /usr/share/novnc/index.html

EXPOSE 6080 5900
ENTRYPOINT ["/app/docker/entrypoint.sh"]
