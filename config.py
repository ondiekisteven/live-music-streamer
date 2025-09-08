import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional

class Config:
    """Configuration class for Music Streamer application"""
    # =============================================================================
    # AUTHENTICATION
    # =============================================================================
    
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "xu0UqJbMmv5ljRSBLTcnMkdXrx9YfF6SUZyUiKiH")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # =============================================================================
    # DIRECTORY CONFIGURATION
    # =============================================================================
    
    # Base directory (where the application runs)
    BASE_DIR = Path(__file__).parent.absolute()
    
    CURRENT_SONG_FILE = os.path.join(BASE_DIR, "conf/now.txt")
    NEXT_SONG_FILE = os.path.join(BASE_DIR,"conf/next.txt")
    
    # Music directory - where audio files are stored
    MUSIC_DIR = os.getenv('MUSIC_DIR', str(BASE_DIR / 'music'))
    
    # Background image path
    BACKGROUND_IMAGE = os.getenv('BACKGROUND_IMAGE', str(BASE_DIR / 'background.png'))
    
    # Database file path
    DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'data/music_stream.db'))
    
    # Logs directory
    LOGS_DIR = os.getenv('LOGS_DIR', str(BASE_DIR / 'logs'))
    
    # =============================================================================
    # STREAMING CONFIGURATION
    # =============================================================================
    
    # YouTube Live RTMP URL
    YOUTUBE_URL = os.getenv('YOUTUBE_URL', '')
    
    # Video configuration
    VIDEO_WIDTH = int(os.getenv('VIDEO_WIDTH', '1280'))
    VIDEO_HEIGHT = int(os.getenv('VIDEO_HEIGHT', '720'))
    VIDEO_PRESET = os.getenv('VIDEO_PRESET', 'veryfast')
    VIDEO_TUNE = os.getenv('VIDEO_TUNE', 'stillimage')
    
    # Audio configuration
    AUDIO_SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', '44100'))
    AUDIO_CHANNELS = int(os.getenv('AUDIO_CHANNELS', '2'))
    AUDIO_BITRATE = os.getenv('AUDIO_BITRATE', '128k')
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 's16le')
    
    # Supported audio file extensions
    SUPPORTED_EXTENSIONS = tuple(os.getenv('SUPPORTED_EXTENSIONS', '.mp3,.wav,.flac,.aac,.mpeg').split(','))
    
    # =============================================================================
    # FFMPEG CONFIGURATION
    # =============================================================================
    
    # FFmpeg command paths
    FFMPEG_PATH = os.getenv('FFMPEG_PATH', 'ffmpeg')
    
    # FFmpeg log level
    FFMPEG_LOG_LEVEL = os.getenv('FFMPEG_LOG_LEVEL', 'quiet')
    
    # Audio chunk size for streaming
    AUDIO_CHUNK_SIZE = int(os.getenv('AUDIO_CHUNK_SIZE', '4096'))
    
    # =============================================================================
    # APPLICATION CONFIGURATION
    # =============================================================================
    
    # Playlist refresh interval when no songs available (seconds)
    PLAYLIST_REFRESH_INTERVAL = int(os.getenv('PLAYLIST_REFRESH_INTERVAL', '5'))
    
    # Enable/disable file watching
    ENABLE_FILE_WATCHING = os.getenv('ENABLE_FILE_WATCHING', 'true').lower() == 'true'
    
    # Enable/disable database cleanup on startup
    ENABLE_DB_CLEANUP = os.getenv('ENABLE_DB_CLEANUP', 'true').lower() == 'true'
    
    # =============================================================================
    # LOGGING CONFIGURATION
    # =============================================================================
    
    # Log level
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Log format
    LOG_FORMAT = os.getenv('LOG_FORMAT', 
        '%(asctime)s\t%(levelname)s\t[%(name)s:%(lineno)s]\t%(message)s')
    
    # Log file name
    LOG_FILENAME = os.getenv('LOG_FILENAME', 'music_streamer.log')
    
    # Maximum log file size (bytes)
    LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
    
    # Number of backup log files
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
    
    # Enable console logging
    LOG_TO_CONSOLE = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    
    # Enable file logging
    LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    
    # =============================================================================
    # DATABASE CONFIGURATION
    # =============================================================================
    
    # Database connection timeout (seconds)
    DB_TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))
    
    # Enable database statistics logging
    ENABLE_DB_STATS = os.getenv('ENABLE_DB_STATS', 'true').lower() == 'true'
    
    # =============================================================================
    # VALIDATION AND INITIALIZATION
    # =============================================================================
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration settings"""
        errors = []
        
        # Check required directories
        if not os.path.exists(cls.MUSIC_DIR):
            errors.append(f"Music directory does not exist: {cls.MUSIC_DIR}")
        
        if not os.path.exists(cls.BACKGROUND_IMAGE):
            errors.append(f"Background image does not exist: {cls.BACKGROUND_IMAGE}")
        
        # Check YouTube URL
        if not cls.YOUTUBE_URL:
            errors.append("YouTube URL is required")
        elif not cls.YOUTUBE_URL.startswith('rtmp://'):
            errors.append("YouTube URL must be a valid RTMP URL")
        
        # Check log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"Invalid log level: {cls.LOG_LEVEL}. Must be one of {valid_log_levels}")
        
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
        
        return True
    
    @classmethod
    def setup_logging(cls) -> logging.Logger:
        """Setup logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        
        # Create logger
        logger = logging.getLogger('music_streamer')
        logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT)
        
        # Console handler
        if cls.LOG_TO_CONSOLE:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # File handler
        if cls.LOG_TO_FILE:
            log_file_path = os.path.join(cls.LOGS_DIR, cls.LOG_FILENAME)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_path,
                maxBytes=cls.LOG_MAX_SIZE,
                backupCount=cls.LOG_BACKUP_COUNT
            )
            file_handler.setLevel(getattr(logging, cls.LOG_LEVEL))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    @classmethod
    def get_ffmpeg_stream_cmd(cls) -> list:
        return [
            cls.FFMPEG_PATH,
            "-re", "-f", cls.AUDIO_FORMAT, "-ar", str(cls.AUDIO_SAMPLE_RATE),
            "-ac", str(cls.AUDIO_CHANNELS), "-i", "pipe:0",
            "-loop", "1", "-i", cls.BACKGROUND_IMAGE,
            "-c:v", "libx264", "-preset", cls.VIDEO_PRESET, "-tune", cls.VIDEO_TUNE,
            "-c:a", "aac", "-b:a", cls.AUDIO_BITRATE,
            "-shortest",
            "-vf", (
                f"scale={cls.VIDEO_WIDTH}:{cls.VIDEO_HEIGHT},format=yuv420p,"
                # Bottom-left: current song
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"textfile={cls.CURRENT_SONG_FILE}:reload=1:"
                "x=if(gt(tw\\,w*0.45-20)\\,10-mod(t*30\\,tw-(w*0.45-40))\\,10):"
                "y=h-th-20:fontsize=28:fontcolor=white:borderw=2,"
                # Bottom-right: next song
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
                f"textfile={cls.NEXT_SONG_FILE}:reload=1:"
                "x=if(gt(tw\\,w*0.45-20)\\,w*0.55+mod(t*30\\,tw-(w*0.45-40))\\,w-tw-10):"
                "y=h-th-20:fontsize=24:fontcolor=yellow:borderw=2"
            ),
            "-f", "flv",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "8",
            "-reconnect_on_network_error", "1",
            cls.YOUTUBE_URL

        ]

    
    @classmethod
    def get_ffmpeg_decode_cmd(cls, input_file: str) -> list:
        """Get FFmpeg decode command for a file"""
        return [
            cls.FFMPEG_PATH, "-i", input_file,
            "-f", cls.AUDIO_FORMAT, "-ar", str(cls.AUDIO_SAMPLE_RATE), 
            "-ac", str(cls.AUDIO_CHANNELS), "pipe:1",
            "-loglevel", cls.FFMPEG_LOG_LEVEL
        ]
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=== Music Streamer Configuration ===")
        print(f"Music Directory: {cls.MUSIC_DIR}")
        print(f"Background Image: {cls.BACKGROUND_IMAGE}")
        print(f"Database Path: {cls.DATABASE_PATH}")
        print(f"Logs Directory: {cls.LOGS_DIR}")
        print(f"YouTube URL: {cls.YOUTUBE_URL[:20]}..." if cls.YOUTUBE_URL else "Not set")
        print(f"Video Resolution: {cls.VIDEO_WIDTH}x{cls.VIDEO_HEIGHT}")
        print(f"Audio Sample Rate: {cls.AUDIO_SAMPLE_RATE}Hz")
        print(f"Supported Extensions: {cls.SUPPORTED_EXTENSIONS}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"File Watching: {'Enabled' if cls.ENABLE_FILE_WATCHING else 'Disabled'}")
        print("=" * 40)
