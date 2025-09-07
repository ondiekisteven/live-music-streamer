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
COPY background.png .

# Create music directory
RUN mkdir -p music

# Set environment variables
ENV MUSIC_DIR=/app/music
ENV BACKGROUND=/app/background.png
ENV YOUTUBE_URL=""

# Expose port (if needed for future web interface)
EXPOSE 8080

# Create non-root user for security
RUN useradd -m -u 1000 streamer && \
    chown -R streamer:streamer /app
USER streamer

# Default command
CMD ["python", "main.py"]
