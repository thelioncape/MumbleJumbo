FROM alpine:latest

USER root
WORKDIR /app
ADD config.json config.json
ADD cert.pem cert.pem
ADD key.pem key.pem
RUN apk add --no-cache git less openssh && \
    apk add --no-cache g++ gcc musl-dev python3 py3-pip && \
    apk add --no-cache youtube-dl ffmpeg && \
    pip install --no-cache-dir --upgrade pip virtualenv && \
    cd /app && \
    git init && \
    git remote add origin https://github.com/thelioncape/MumbleJumbo.git && \
    git fetch && \
    git checkout -t origin/main && \
    virtualenv /app && \
    /app/bin/pip install --no-cache-dir -r /app/requirements.txt

CMD ["/app/bin/python", "/app/music_bot.py"]