import os
import random
import subprocess
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from music_db import MusicDatabase

MUSIC_DIR = "music"
BACKGROUND = "background.png"
YOUTUBE_URL = "rtmp://a.rtmp.youtube.com/live2/3ses-sevb-f6w3-73qc-2683"

playlist = []
playlist_lock = threading.Lock()
db = MusicDatabase()


def load_playlist():
    """Shuffle and reload music files, sync with database"""
    files = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR)
             if f.lower().endswith((".mp3", ".wav", ".flac", ".aac"))]
    
    # Clean up database - remove songs for files that no longer exist
    removed_count = db.cleanup_missing_files()
    if removed_count > 0:
        print(f"[Database cleanup] Removed {removed_count} songs with missing files")
    
    # Add new songs to database
    added_count = 0
    for file_path in files:
        existing_song = db.get_song_by_path(file_path)
        if not existing_song:
            song_id = db.add_song(file_path)
            added_count += 1
    
    if added_count > 0:
        print(f"[Database sync] Added {added_count} new songs")
    
    # Shuffle files for playlist
    random.shuffle(files)
    with playlist_lock:
        playlist.clear()
        playlist.extend(files)
    
    print(f"[Playlist updated] {len(files)} tracks loaded")

def update_text_files(now_song, next_song):
    with open("conf/now.txt", "w") as f:
        f.write(f"Now Playing: {now_song}")
    with open("conf/next.txt", "w") as f:
        f.write(f"Next: {next_song}")

class MusicWatcher(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith((".mp3", ".wav", ".flac", ".aac")):
            print(f"[File system event] {event.event_type}: {os.path.basename(event.src_path)}")
            
            # Handle file removal
            if event.event_type == 'deleted':
                song_info = db.get_song_by_path(event.src_path)
                if song_info:
                    song_id = song_info[0]
                    song_title = song_info[2]
                    db.remove_song(song_id)
                    print(f"[Database] Removed song: {song_title}")
            
            # Reload playlist (this will sync database)
            load_playlist()

#-loop 1 -i background.jpg ... -vf scale=1280:720 
def ffmpeg_streamer():
    """Main FFmpeg streamer process with overlays"""
    ffmpeg_cmd = [
        "ffmpeg",
        "-re", "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
        "-loop", "1", "-i", BACKGROUND,
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-vf",
        (
            "scale=1280:720,format=yuv420p,"
            # Bottom-left (current song)
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "textfile=conf/now.txt:x=10:y=h-th-20:fontsize=28:fontcolor=white:borderw=2,"
            # Bottom-right (next song)
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            "textfile=conf/next.txt:x=w-tw-10:y=h-th-20:fontsize=24:fontcolor=yellow:borderw=2"
        ),
        "-f", "flv", YOUTUBE_URL
    ]
    return subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)


def stream_loop():
    process = ffmpeg_streamer()
    try:
        while True:
            with playlist_lock:
                if not playlist:
                    time.sleep(5)
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
                print(f"[Now playing] {song_title}")
                if song_id:
                    print(f"[Database] Song ID: {song_id}, Position: {i+1}/{len(songs)}")
                
                decode_cmd = [
                    "ffmpeg", "-i", song,
                    "-f", "s16le", "-ar", "44100", "-ac", "2", "pipe:1",
                    "-loglevel", "quiet"
                ]
                decoder = subprocess.Popen(decode_cmd, stdout=subprocess.PIPE)

                while True:
                    chunk = decoder.stdout.read(4096)
                    if not chunk:
                        break
                    try:
                        process.stdin.write(chunk)
                    except BrokenPipeError:
                        print("[FFmpeg crashed] Restarting...")
                        process.terminate()
                        process = ffmpeg_streamer()
                        break

                decoder.wait()
                
                # Mark song as played in database
                if song_id:
                    db.update_song_played(song_id)
                    print(f"[Database] Marked '{song_title}' as played")
    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        process.terminate()

def show_stats():
    """Display database statistics"""
    stats = db.get_stats()
    print("\n=== Music Database Statistics ===")
    print(f"Total songs: {stats['total_songs']}")
    print(f"Total plays: {stats['total_plays']}")
    if stats['most_played']:
        print(f"Most played: {stats['most_played']} ({stats['most_played_count']} times)")
    
    # Show current playback state
    current_song = db.get_current_song()
    next_song = db.get_next_song()
    
    if current_song:
        print(f"\nCurrently playing: {current_song[2]}")
    if next_song:
        print(f"Next up: {next_song[2]}")
    print("=" * 35)

if __name__ == "__main__":
    print("=== Music Streamer with Database Tracking ===")
    
    # Initial playlist load
    load_playlist()
    
    # Show initial stats
    show_stats()

    # Start watchdog observer
    event_handler = MusicWatcher()
    observer = Observer()
    observer.schedule(event_handler, MUSIC_DIR, recursive=False)
    observer.start()

    # Start streaming loop
    try:
        stream_loop()
    finally:
        observer.stop()
        observer.join()
        print("\n=== Final Statistics ===")
        show_stats()
