# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY main.py .
COPY music_db.py .
COPY config.py .
COPY background.png .

# Create necessary directories
RUN mkdir -p music logs conf

# Set environment variables with defaults
ENV MUSIC_DIR=/app/music
ENV BACKGROUND_IMAGE=/app/background.png
ENV DATABASE_PATH=/app/music_stream.db
ENV LOGS_DIR=/app/logs
ENV YOUTUBE_URL=""
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

# Expose port (if needed for future web interface)
EXPOSE 8080

# Create non-root user for security
RUN useradd -m -u 1000 streamer && \
    chown -R streamer:streamer /app
USER streamer

# Default command
CMD ["python", "main.py"]
