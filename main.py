"""
This is the legacy application. I want to thank it for its service. But very soon I am moving away from it. :(
"""

import os
import logging
import subprocess
import time
import threading
import signal
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from music_db import MusicDatabaseMysql as MusicDatabase
from config import Config

if not Config.validate():
    exit(1)

Config.configure_logger()
logger = logging.getLogger(__name__)
playlist = []
playlist_lock = threading.Lock()
db = MusicDatabase(Config.DATABASE_PATH)

restarting = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    db.stop_streaming()
    logger.info("Streaming stopped (signal handler)")
    sys.exit(0)


def load_playlist():
    """Shuffle and reload music files, sync with database"""
    files = [os.path.join(Config.MUSIC_DIR, f) for f in os.listdir(Config.MUSIC_DIR)
             if f.lower().endswith(Config.SUPPORTED_EXTENSIONS)]
    
    # Clean up database - remove songs for files that no longer exist
    if Config.ENABLE_DB_CLEANUP:
        removed_count = db.cleanup_missing_files()
        if removed_count > 0:
            logger.info(f"Database cleanup: Removed {removed_count} songs with missing files")
    
    # Add new songs to database
    added_count = 0
    for file_path in files:
        existing_song = db.get_song_by_path(file_path)
        if not existing_song:
            song_id = db.add_song(file_path)
            added_count += 1
    
    if added_count > 0:
        logger.info(f"Database sync: Added {added_count} new songs")
    
    # Shuffle files for playlist
    # random.shuffle(files)
    with playlist_lock:
        pass
        # playlist.clear()
        # playlist.extend(files)
    
    logger.info(f"Playlist updated: {len(files)} tracks loaded")

def update_text_files(now_song, next_song):
    with open(Config.CURRENT_SONG_FILE, "w") as f:
        f.write(f"Now Playing: {now_song}")
    with open(Config.NEXT_SONG_FILE, "w") as f:
        f.write(f"Next: {next_song}")

def save_playlist_to_file(playlist):
    with open("conf/playlist.txt", "w") as f:
        for song in playlist:
            f.write(song + "\n")

class MusicWatcher(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(Config.SUPPORTED_EXTENSIONS):
            logger.info(f"File system event: {event.event_type}: {os.path.basename(event.src_path)}")
            
            # Handle file removal
            if event.event_type == 'deleted':
                song_info = db.get_song_by_path(event.src_path)
                if song_info:
                    song_id = song_info[0]
                    song_title = song_info[2]
                    db.remove_song(song_id)
                    logger.info(f"Database: Removed song: {song_title}")
            
            # Reload playlist (this will sync database)
            load_playlist()

#-loop 1 -i background.jpg ... -vf scale=1280:720 
def ffmpeg_streamer():
    """Main FFmpeg streamer process"""
    ffmpeg_cmd = Config.get_ffmpeg_stream_cmd()
    logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
    return subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)


def get_youtube_direct_url(youtube_url: str) -> str:
    result = subprocess.run(
        ["yt-dlp", "-f", "bestaudio", "-g", youtube_url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, check=True
    )
    return result.stdout.strip()


def stream_loop():
    process = ffmpeg_streamer()
    db.start_streaming()
    logger.info("Streaming started")

    try:
        while True:
            # Promote next → current, increment play count, and select a new next
            current_song, next_song = db.advance_playback()  
            # current_song and next_song are (id, file_path, title) tuples

            if not current_song:
                logger.warning("No song available to play. Retrying...")
                time.sleep(Config.PLAYLIST_REFRESH_INTERVAL)
                continue

            song_id = current_song["id"]
            file_path = current_song["file_path"] 
            song_title = current_song["title"]
            source_type = current_song["source_type"]
            next_song_title = next_song["title"] if next_song else "Unknown"

            update_text_files(song_title, next_song_title)
            logger.info(f"Now playing: {song_title}")
            if song_id:
                logger.debug(f"Database: Song ID: {song_id}")

            if source_type == "file":
                # decode local file and pipe into FFmpeg
                decode_cmd = Config.get_ffmpeg_file_decode_cmd(file_path)
                decoder = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE)

                while True:
                    chunk = decoder.stdout.read(Config.AUDIO_CHUNK_SIZE)
                    if not chunk:
                        break
                    try:
                        process.stdin.write(chunk)
                        restarting = False
                    except BrokenPipeError:
                        logger.error("FFmpeg crashed: Restarting...")
                        process.terminate()
                        process = ffmpeg_streamer()
                        restarting = True
                        break
                
                if not restarting: 
                    decoder.wait()

            elif source_type == "youtube":
                try:
                    yt_proc = subprocess.Popen(
                        ["yt-dlp", "-f", "bestaudio", "--no-part", "--no-playlist", "-o", "-", file_path],
                        stdout=subprocess.PIPE
                    )

                    ffmpeg_cmd = Config.get_ffmpeg_youtube_stream_cmd("pipe:0")

                    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=yt_proc.stdout)

                    # Close yt_proc.stdout in parent so yt-dlp gets SIGPIPE if ffmpeg exits
                    yt_proc.stdout.close()

                    # Wait for ffmpeg to finish first
                    ffmpeg_proc.wait()
                    yt_proc.wait()
                except Exception as x: 
                    logger.exception(x)
                    process.terminate

            if song_id:
                db.update_song_played(song_id)
                logger.info(f"Database: Marked '{song_title}' as played")

    except KeyboardInterrupt:
        logger.info("Stopping stream...")
    finally:
        db.stop_streaming()
        logger.info("Streaming stopped")
        process.terminate()


def show_stats():
    """Display database statistics"""
    if not Config.ENABLE_DB_STATS:
        return
        
    stats = db.get_stats()
    logger.info("=== Music Database Statistics ===")
    logger.info(f"Total songs: {stats['total_songs']}")
    logger.info(f"Total plays: {stats['total_plays']}")
    if stats['most_played']:
        logger.info(f"Most played: {stats['most_played']} ({stats['most_played_count']} times)")
    
    # Show current playback state
    current_song = db.get_current_song()
    next_song = db.get_next_song()
    
    if current_song:
        logger.info(f"Currently playing: {current_song[2]}")
    if next_song:
        logger.info(f"Next up: {next_song[2]}")
    logger.info("=" * 35)

if __name__ == "__main__":
    logger.info("=== Music Streamer with Database Tracking ===")
    Config.print_config()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    load_playlist()

    show_stats()

    if Config.ENABLE_FILE_WATCHING:
        event_handler = MusicWatcher()
        observer = Observer()
        observer.schedule(event_handler, Config.MUSIC_DIR, recursive=False)
        observer.start()
        logger.info(f"File watching enabled for: {Config.MUSIC_DIR}")

    try:
        stream_loop()
    finally:
        # Ensure streaming is stopped on any shutdown
        db.stop_streaming()
        logger.info("Streaming stopped (shutdown)")
        
        if Config.ENABLE_FILE_WATCHING:
            observer.stop()
            observer.join()
        logger.info("=== Final Statistics ===")
        show_stats()
        logger.info("Application shutdown complete")
