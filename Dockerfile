FROM alpine:latest

USER root
WORKDIR /app
ADD config.json config.json
ADD cert.pem cert.pem
ADD key.pem key.pem
RUN apk add --no-cache git less openssh && \
    apk add --no-cache g++ gcc musl-dev && \
    apk add --no-cache youtube-dl ffmpeg && \
    pip install --no-cache-dir --upgrade pip virtualenv && \
    cd /app && \
    git init && \
    git remote add origin https://github.com/thelioncape/MumbleJumbo.git && \
    git fetch && \
    git checkout -t origin/main && \
    virtualenv /app && \
    /app/bin/pip install --nocache-dir -r /app/requirements.txt && \
    apk --purge del .build-deps && \
    /app/bin/python music_bot.py
