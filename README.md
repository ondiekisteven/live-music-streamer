# Music Streamer

A Python-based music streaming application that broadcasts audio to YouTube Live with SQLite database tracking and automatic playlist management.

## Features

- 🎵 **Automatic Music Streaming**: Streams music files to YouTube Live 24/7
- 📊 **Database Tracking**: SQLite database tracks all songs, play counts, and playback history
- 🔄 **Dynamic Playlist Management**: Automatically detects new/removed music files
- 🎨 **Background Video**: Uses a static background image for the video stream
- 📈 **Statistics**: Track most played songs, total plays, and current playback state
- 🐳 **Docker Support**: Containerized deployment with Docker
- 🔒 **Thread-Safe**: Multi-threaded architecture with proper locking

## Supported Audio Formats

- MP3
- WAV
- FLAC
- AAC
- MPEG (can be added by modifying the code)

## Requirements

- Python 3.11+
- FFmpeg
- YouTube Live Stream Key
- Background image (PNG/JPG)

## Installation

### Local Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd music-streamer
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

### Docker Installation

1. **Build the image**:
   ```bash
   docker build -t music-streamer .
   ```

2. **Run the container**:
   ```bash
   docker run -d --name music-stream \
     -v /path/to/your/music:/app/music \
     -e YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/your-stream-key" \
     music-streamer
   ```

## Configuration

### Environment Variables

- `MUSIC_DIR`: Path to music directory (default: `/home/steven/Music/streams/ffmpeg/music`)
- `BACKGROUND`: Path to background image (default: `/home/steven/Music/streams/ffmpeg/background.png`)
- `YOUTUBE_URL`: YouTube Live RTMP URL (required)

### YouTube Live Setup

1. Go to [YouTube Studio](https://studio.youtube.com/)
2. Create a new live stream
3. Copy the RTMP URL (format: `rtmp://a.rtmp.youtube.com/live2/your-stream-key`)
4. Set this as your `YOUTUBE_URL` environment variable

## Usage

### Local Usage

1. **Prepare your music**:
   - Place audio files in the `music/` directory
   - Supported formats: MP3, WAV, FLAC, AAC

2. **Set up background image**:
   - Place your background image as `background.png` in the project root
   - Recommended size: 1280x720 pixels

3. **Configure YouTube URL**:
   ```bash
   export YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/your-stream-key"
   ```

4. **Run the application**:
   ```bash
   python main.py
   ```

### Docker Usage

```bash
# Basic run
docker run -d --name music-stream \
  -v /path/to/your/music:/app/music \
  -e YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/your-stream-key" \
  music-streamer

# With custom background
docker run -d --name music-stream \
  -v /path/to/your/music:/app/music \
  -v /path/to/background.png:/app/background.png \
  -e YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/your-stream-key" \
  music-streamer

# View logs
docker logs -f music-stream
```

## Database Features

The application uses SQLite to track:

- **Song Information**: File paths, titles, duration, creation date
- **Playback History**: Last played time, play count
- **Current State**: Currently playing song, next song, playlist position
- **Statistics**: Most played songs, total play count

### Database Schema

```sql
-- Songs table
CREATE TABLE songs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    title TEXT,
    duration_seconds INTEGER,
    last_played TIMESTAMP,
    play_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playback state table
CREATE TABLE playback_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_song_id INTEGER,
    next_song_id INTEGER,
    playlist_position INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## File Structure

```
music-streamer/
├── main.py              # Main streaming application
├── music_db.py          # SQLite database helper
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── .dockerignore       # Docker ignore file
├── background.png      # Background image for stream
├── music/              # Music files directory
│   ├── song1.mp3
│   ├── song2.wav
│   └── ...
└── music_stream.db     # SQLite database (created automatically)
```

## Monitoring

The application provides detailed logging:

```
=== Music Streamer with Database Tracking ===
[Database cleanup] Removed 0 songs with missing files
[Database sync] Added 2 new songs
[Playlist updated] 2 tracks loaded

=== Music Database Statistics ===
Total songs: 2
Total plays: 0
Currently playing: None
Next up: None
===================================

[Now playing] Song Title
[Database] Song ID: 1, Position: 1/2
[Database] Marked 'Song Title' as played
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**:
   - Ensure FFmpeg is installed and in PATH
   - For Docker: FFmpeg is included in the image

2. **YouTube stream fails**:
   - Verify your RTMP URL is correct
   - Check if your YouTube Live stream is active
   - Ensure your stream key is valid

3. **No music files detected**:
   - Check file permissions
   - Verify files are in supported formats
   - Ensure music directory is mounted correctly (Docker)

4. **Database errors**:
   - Check file permissions for database creation
   - Ensure no other process is using the database

### Logs

- **Local**: Check console output
- **Docker**: `docker logs music-stream`

## Development

### Adding New Audio Formats

To support additional audio formats, modify the `load_playlist()` function in `main.py`:

```python
if f.lower().endswith((".mp3", ".wav", ".flac", ".aac", ".mpeg")):
```

### Database Queries

You can interact with the database directly:

```python
from music_db import MusicDatabase

db = MusicDatabase()
stats = db.get_stats()
print(f"Total songs: {stats['total_songs']}")
```

## License

This project is open source. Please check the license file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue on GitHub

---

**Note**: This application is designed for personal use. Ensure you have the rights to stream the music content and comply with YouTube's terms of service.
