import logging
import signal
import subprocess
import time
from config import Config
from main import signal_handler
from music_db import MusicDatabaseMysql as MusicDatabase
from utils import send_ntfy_notification

db = MusicDatabase(Config.DATABASE_PATH)
Config.configure_logger()
logger = logging.getLogger(__name__)

def get_ffmpeg_stream_cmd(pulse_name) -> list:
    base = [
        Config.FFMPEG_PATH,
        "-re", "-thread_queue_size", "1024",
        "-f", "pulse", "-i", f"{pulse_name}.monitor",
        "-c:v", "libx264", "-preset", Config.VIDEO_PRESET,
        "-g", "60", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", Config.AUDIO_BITRATE,
        "-b:v", Config.VIDEO_BITRATE,
        "-f", "flv", "-loglevel", "verbose",
        "-rtmp_live", "live",
        "-timeout", "5000000",
        "-rtmp_buffer", "1000",
        Config.RTMP_URL,
    ]

    if Config.VIDEO_SOURCE == 'image':
        return [
            Config.FFMPEG_PATH,
            "-hide_banner",
            
            # Input settings
            "-re", 
            "-thread_queue_size", "1024",
            "-loop", "1", 
            "-i", Config.BACKGROUND_IMAGE,
            "-f", "pulse", 
            "-thread_queue_size", "1024",  # Also for audio input
            "-i", f"{pulse_name}.monitor",
            
            # Mapping
            "-map", "0:v", 
            "-map", "1:a",
            
            # Video encoding
            "-c:v", "libx264", 
            "-preset", Config.VIDEO_PRESET,
            "-tune", Config.VIDEO_TUNE,
            "-g", "60", 
            "-pix_fmt", "yuv420p",
            "-b:v", Config.VIDEO_BITRATE,
            
            # Audio encoding
            "-c:a", "aac", 
            "-b:a", Config.AUDIO_BITRATE,
            "-ar", "44100",
            "-ac", "2",
            
            # Output format
            "-f", "flv", 
            "-loglevel", "warning",  # Changed from verbose to reduce noise
            "-stats",  # Still show progress stats
            
            # Critical reconnection settings (NEW)
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "2",
            "-reconnect_at_eof", "1",
            
            # TCP and RTMP settings
            "-timeout", "3000000",
            "-rtmp_buffer", "1000",
            "-rtmp_live", "live",
            
            "-err_detect", "ignore_err",
            "-max_muxing_queue_size", "1024",
            
            Config.RTMP_URL,
        ]
    # for video source
    return [
        Config.FFMPEG_PATH,
        "-re", "-thread_queue_size", "1024",
        "-stream_loop", "-1", "-i", Config.BACKGROUND_VIDEO,
        "-f", "pulse", "-i", f"{pulse_name}.monitor",
        "-filter_complex", "[0:a][1:a]amix=inputs=2:dropout_transition=2[outa]",
        "-map", "0:v", "-map", "[outa]",
        "-c:v", "libx264", "-preset", Config.VIDEO_PRESET,
        "-g", "60", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", Config.AUDIO_BITRATE,
        "-b:v", Config.VIDEO_BITRATE,
        "-f", "flv", "-loglevel", "verbose",
        "-rtmp_live", "live",
        "-timeout", "5000000",
        "-rtmp_buffer", "1000",
        Config.RTMP_URL,
    ]


def run_ffmpeg(ffmpeg_cmd, application_id):
    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    stream_started = False
    send_ntfy_notification("🎬 Stream process launched...", priority='max', application_id=application_id)

    for line in ffmpeg_process.stdout:
        logger.warning(line.strip())

        # Detect start of streaming
        if not stream_started and ("frame=" in line or "Connection to" in line):
            send_ntfy_notification("✅ Stream started successfully!", priority='max', application_id=application_id)
            stream_started = True

    ffmpeg_process.wait()
    return ffmpeg_process.returncode


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    pulse_name = Config.PULSE_NAME
    application_id = Config.APPLICATION_ID
    db.start_streaming(application_id=application_id)
    
    retry_delay = 0.1
    max_consecutive_failures = 30
    consecutive_failures = 0
    
    while True:
        ffmpeg_cmd = get_ffmpeg_stream_cmd(pulse_name)
        
        try:
            logger.info("🚀 Starting FFmpeg stream...")
            exit_code = run_ffmpeg(ffmpeg_cmd, application_id)
            
            if exit_code == 0:
                logger.info("FFmpeg exited normally.")
                consecutive_failures = 0  # Reset on success
                break
            else:
                consecutive_failures += 1
                logger.error(f"FFmpeg exited with code {exit_code} (failure {consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    send_ntfy_notification(
                        f"🚨 Stream failed {max_consecutive_failures} times. Stopping.",
                        priority='max',
                        application_id=application_id
                    )
                    break
                
        except Exception as e:
            consecutive_failures += 1
            logger.exception(e)
            send_ntfy_notification(
                f"🚨 Stream crashed: {str(e)} (failure {consecutive_failures}/{max_consecutive_failures})",
                priority='max',
                application_id=application_id
            )
            
        finally:
            logger.info(f"Restarting stream in {retry_delay}s...")
            time.sleep(retry_delay)

if __name__ == '__main__':
    main()
