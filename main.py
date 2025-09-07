import os
import random
import subprocess
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from music_db import MusicDatabase
from config import Config

# Initialize configuration and logging
if not Config.validate():
    exit(1)

logger = Config.setup_logging()
playlist = []
playlist_lock = threading.Lock()
db = MusicDatabase(Config.DATABASE_PATH)


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
    random.shuffle(files)
    with playlist_lock:
        playlist.clear()
        playlist.extend(files)
    
    logger.info(f"Playlist updated: {len(files)} tracks loaded")

def update_text_files(now_song, next_song):
    with open("conf/now.txt", "w") as f:
        f.write(f"Now Playing: {now_song}")
    with open("conf/next.txt", "w") as f:
        f.write(f"Next: {next_song}")

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


def stream_loop():
    process = ffmpeg_streamer()
    try:
        while True:
            with playlist_lock:
                if not playlist:
                    time.sleep(Config.PLAYLIST_REFRESH_INTERVAL)
                    continue
                songs = playlist.copy()

            for i, song in enumerate(songs):
                # Get song info from database
                song_info = db.get_song_by_path(song)
                song_id = song_info[0] if song_info else None
                song_title = song_info[2] if song_info else os.path.basename(song)
                
                # Set current and next song in database
                next_song = songs[i + 1] if i + 1 < len(songs) else songs[0]  # Loop back to start
                next_song_info = db.get_song_by_path(next_song)
                next_song_id = next_song_info[0] if next_song_info else None
                
                db.set_current_song(song_id, next_song_id, i)
                update_text_files(song_title, next_song_info[2] if next_song_info else "Unknown")
                
                logger.info(f"Now playing: {song_title}")
                if song_id:
                    logger.debug(f"Database: Song ID: {song_id}, Position: {i+1}/{len(songs)}")
                
                decode_cmd = Config.get_ffmpeg_decode_cmd(song)
                decoder = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE)

                while True:
                    chunk = decoder.stdout.read(Config.AUDIO_CHUNK_SIZE)
                    if not chunk:
                        break
                    try:
                        process.stdin.write(chunk)
                    except BrokenPipeError:
                        logger.error("FFmpeg crashed: Restarting...")
                        process.terminate()
                        process = ffmpeg_streamer()
                        break

                decoder.wait()
                
                # Mark song as played in database
                if song_id:
                    db.update_song_played(song_id)
                    logger.info(f"Database: Marked '{song_title}' as played")
    except KeyboardInterrupt:
        logger.info("Stopping stream...")
    finally:
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
    
    # Initial playlist load
    load_playlist()
    
    # Show initial stats
    show_stats()

    # Start watchdog observer
    if Config.ENABLE_FILE_WATCHING:
        event_handler = MusicWatcher()
        observer = Observer()
        observer.schedule(event_handler, Config.MUSIC_DIR, recursive=False)
        observer.start()
        logger.info(f"File watching enabled for: {Config.MUSIC_DIR}")

    # Start streaming loop
    try:
        stream_loop()
    finally:
        if Config.ENABLE_FILE_WATCHING:
            observer.stop()
            observer.join()
        logger.info("=== Final Statistics ===")
        show_stats()
        logger.info("Application shutdown complete")
