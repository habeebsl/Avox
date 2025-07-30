FROM python:3.13

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update -q && \
    apt-get install -y -qq --no-install-recommends \
        xvfb \
        libxcomposite1 \
        libxdamage1 \
        libatk1.0-0 \
        libasound2 \
        libasound2-dev \
        libdbus-1-3 \
        libnspr4 \
        libgbm1 \
        libatk-bridge2.0-0 \
        libcups2 \
        libxkbcommon0 \
        libatspi2.0-0 \
        libnss3 \
        ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip3 install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps chromium

COPY . .

ENV DISPLAY=:99

CMD Xvfb :99 -screen 0 1280x720x24 -ac & \
    sleep 2 && \
    uvicorn main:app --host 0.0.0.0 --port $PORT