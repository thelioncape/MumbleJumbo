FROM alpine:latest

USER root
WORKDIR /app
ADD config.json config.json
RUN apk add --no-cache git less openssh && \
    apk add --no-cache .build-deps g++ gcc musl-dev && \
    apk add --no-cache youtube-dl ffmpeg && \
    pip install --no-cache-dir --upgrade pip virtualenv && \
    cd /app && \
    git init && \
    git remote add origin https://github.com/thelioncape/MumbleJumbo.git && \
    git fetch && \
    git checkout -t origin/main && \
    virtualenv /app && \
    bin/pip install --nocache-dir -r /app/requirements.txt && \
    apk --purge del .build-deps && \
    bin/python music_bot.py
