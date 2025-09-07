import os
import random
import subprocess
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

MUSIC_DIR = "/home/steven/Music/streams/ffmpeg/music"
BACKGROUND = "/home/steven/Music/streams/ffmpeg/background.png"
YOUTUBE_URL = "rtmp://a.rtmp.youtube.com/live2/3ses-sevb-f6w3-73qc-2683"

playlist = []
playlist_lock = threading.Lock()

def load_playlist():
    """Shuffle and reload music files"""
    files = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR)
             if f.lower().endswith((".mp3", ".wav", ".flac", ".aac"))]
    random.shuffle(files)
    with playlist_lock:
        playlist.clear()
        playlist.extend(files)
    print(f"[Playlist updated] {len(files)} tracks loaded")

class MusicWatcher(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith((".mp3", ".wav", ".flac", ".aac")):
            load_playlist()

#-loop 1 -i background.jpg ... -vf scale=1280:720 
def ffmpeg_streamer():
    """Main FFmpeg streamer process"""
    ffmpeg_cmd = [
        "ffmpeg",
        "-re", "-f", "s16le", "-ar", "44100", "-ac", "2", "-i", "pipe:0",
        "-loop", "1", "-i", BACKGROUND,
        "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        "-vf", "scale=1280:720,format=yuv420p",
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

            for song in songs:
                print(f"[Now playing] {song}")
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
    except KeyboardInterrupt:
        print("Stopping stream...")
    finally:
        process.terminate()

if __name__ == "__main__":
    # Initial playlist load
    load_playlist()

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
