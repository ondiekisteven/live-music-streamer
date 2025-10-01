# Use Python 3.11 slim image as base
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ffmpeg pulseaudio \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p music logs conf


ENV MUSIC_DIR=/app/music
ENV BACKGROUND_IMAGE=/app/background.png
ENV DATABASE_PATH=/app/music_stream.db
ENV LOGS_DIR=/app/logs
ENV YOUTUBE_URL=""
ENV RTMP_URL=""
ENV VIDEO_WIDTH=1280
ENV VIDEO_HEIGHT=720
ENV AUDIO_SAMPLE_RATE=44100
ENV AUDIO_CHANNELS=2
ENV AUDIO_BITRATE=128k
ENV LOG_LEVEL=INFO
ENV LOG_TO_CONSOLE=true
ENV LOG_TO_FILE=true
ENV ENABLE_FILE_WATCHING=true
ENV ENABLE_DB_CLEANUP=true
ENV ENABLE_DB_STATS=true

EXPOSE 8080

ARG UID=1000
RUN useradd -m -u ${UID} streamer && \
    chown -R streamer:streamer /app
USER streamer
