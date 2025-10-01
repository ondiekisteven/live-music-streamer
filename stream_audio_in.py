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
from utils import send_ntfy_notification

if not Config.validate():
    exit(1)

Config.configure_logger()
logger = logging.getLogger(__name__)

playlist = []
playlist_lock = threading.Lock()
db = MusicDatabase(Config.DATABASE_PATH)

restarting = False

def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    db.stop_streaming()
    logger.info("Streaming stopped (signal handler)")
    sys.exit(0)


def load_playlist():
    files = [os.path.join(Config.MUSIC_DIR, f) for f in os.listdir(Config.MUSIC_DIR)
             if f.lower().endswith(Config.SUPPORTED_EXTENSIONS)]
    
    if Config.ENABLE_DB_CLEANUP:
        removed_count = db.cleanup_missing_files()
        if removed_count > 0:
            logger.info(f"Database cleanup: Removed {removed_count} songs with missing files")
    
    added_count = 0
    for file_path in files:
        existing_song = db.get_song_by_path(file_path)
        if not existing_song:
            song_id = db.add_song(file_path)
            added_count += 1
    
    if added_count > 0:
        logger.info(f"Database sync: Added {added_count} new songs")

    logger.info(f"Playlist updated: {len(files)} tracks loaded")


def get_audio_stream_cmd(file_path, pulse_name):
    return [
        Config.FFMPEG_PATH, 
        "-re", "-i", file_path, 
        "-device", pulse_name
        "-f", "pulse", "-ar", "44100", 
        "-ac", str(Config.AUDIO_CHANNELS), 
        "-loglevel", "verbose", 
        "dummy"
    ]

def stream_loop(application_id, pulse_name):
    processes = []
    try:
        while True:
            current_song, next_song = db.advance_playback(application_id=application_id)

            if not current_song:
                m = "No song available to play. Retrying..."
                logger.warning(m)
                send_ntfy_notification(m, application_id=application_id)
                time.sleep(Config.PLAYLIST_REFRESH_INTERVAL)
                continue

            song_id = current_song["id"]
            file_path = current_song["file_path"] 
            song_title = current_song["title"]
            source_type = current_song["source_type"]
            next_song_title = next_song["title"] if next_song else "Unknown"
            
            send_ntfy_notification(f"▶️ Now : {song_title}\n🕑 Next : {next_song_title}", priority='low', application_id=application_id)

            if song_id:
                logger.debug(f"Database: Song ID: {song_id}")

            if source_type == "file":
                try:
                    file_stream_cmd = get_audio_stream_cmd(file_path, pulse_name=pulse_name)
                    file_process = None
                    file_process = subprocess.Popen(file_stream_cmd, stdout=subprocess.PIPE)
                    processes.append(file_process)
                    
                    file_process.wait()
                except Exception as x: 
                    logger.exception(x)
                    send_ntfy_notification(f"⚠️ {str(x)}", priority='max', application_id=application_id)

            elif source_type == "youtube":
                try:
                    yt_proc = subprocess.Popen(
                        ["yt-dlp", "-f", "bestaudio", "--no-part", "--no-playlist", "-o", "-", file_path],
                        stdout=subprocess.PIPE
                    )

                    ffmpeg_cmd = get_audio_stream_cmd("pipe:0", pulse_name=pulse_name)

                    ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=yt_proc.stdout)
                    processes.append(ffmpeg_proc)

                    yt_proc.stdout.close()

                    ffmpeg_proc.wait()
                    yt_proc.wait()
                except Exception as x: 
                    logger.exception(x)
                    send_ntfy_notification(f"⚠️ {str(x)}", priority='max', application_id=application_id)

            if song_id:
                db.update_song_played(song_id)
                logger.info(f"Database: Marked '{song_title}' as played")

    except KeyboardInterrupt as x:
        logger.info("Stopping stream...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()

        logger.info("Streaming stopped")


def show_stats(application_id):
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
    current_song = db.get_current_song(application_id=application_id)
    next_song = db.get_next_song(application_id=application_id)
    
    if current_song:
        logger.info(f"Currently playing: {current_song[2]}")
    if next_song:
        logger.info(f"Next up: {next_song[2]}")
    logger.info("=" * 35)


def main():
    application_id = Config.APPLICATION_ID
    pulse_name = Config.PULSE_NAME

    logger.info("=== Music Streamer with Database Tracking ===")
    send_ntfy_notification("✅ Stream Input Started", priority='max', application_id=application_id)
    Config.print_config()

    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    load_playlist()

    try:
        stream_loop(application_id=application_id, pulse_name=pulse_name)
    finally:
        # Ensure streaming is stopped on any shutdown
        db.stop_streaming(application_id=application_id)
        logger.info("Streaming stopped (shutdown)")

        logger.info("=== Final Statistics ===")
        show_stats(application_id=application_id)
        logger.info("Application shutdown complete")
    send_ntfy_notification("⚠️ Stream input process stopped!!", priority='max', application_id=application_id)
    
if __name__ == "__main__":
    main()