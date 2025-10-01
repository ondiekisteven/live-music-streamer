import logging
import signal
import subprocess
from config import Config
from main import signal_handler
from music_db import MusicDatabaseMysql as MusicDatabase
from utils import send_ntfy_notification

db = MusicDatabase(Config.DATABASE_PATH)
Config.configure_logger()
logger = logging.getLogger(__name__)

def get_ffmpeg_stream_cmd(pulse_name) -> list:
    if Config.VIDEO_SOURCE == 'image': 
        logger.info(f"SOURCE TYPE: {Config.VIDEO_SOURCE}")
        return [
            Config.FFMPEG_PATH,
            "-re", "-thread_queue_size", "1024",
            "-loop", "1", "-i", Config.BACKGROUND_IMAGE,
            "-f", "pulse", "-i", f"{pulse_name}.monitor",
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-preset", Config.VIDEO_PRESET, "-tune", Config.VIDEO_TUNE,
            "-g", "60", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", Config.AUDIO_BITRATE, "-b:v", Config.VIDEO_BITRATE,
            "-f", "flv", "-loglevel", "verbose",
            "-reconnect", "1",
            "-reconnect_streamed", "1",
            "-reconnect_delay_max", "8",
            "-reconnect_on_network_error", "1",
            Config.RTMP_URL,
        ]
    
    return [
        Config.FFMPEG_PATH,
        "-re", "-thread_queue_size", "1024",
        "-stream_loop", "-1", "-i", Config.BACKGROUND_VIDEO, 
        "-f", "pulse", "-i", f"{pulse_name}.monitor", 
        "-filter_complex", "[0:a][1:a]amix=inputs=2:dropout_transition=2[outa]",
        "-map", "0:V", "-map", "[outa]",
        "-c:v", "libx264", "-preset", Config.VIDEO_PRESET, 
        "-g", "60", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", Config.AUDIO_BITRATE, "-b:v", Config.VIDEO_BITRATE, 
        "-f", "flv", "-loglevel", "verbose",
        "-reconnect", "1",
        "-reconnect_streamed", "1",
        "-reconnect_delay_max", "8",
        "-reconnect_on_network_error", "1",
        Config.RTMP_URL
    ]


def main():
    logger = Config.configure_logger()
    # logger = logging.getLogger(__name__)  

    pulse_name = Config.PULSE_NAME
    application_id = Config.APPLICATION_ID
      
    signal.signal(signal.SIGINT, signal_handler)  
    signal.signal(signal.SIGTERM, signal_handler) 
    ffmpeg_process = None
    ffmpeg_cmd = get_ffmpeg_stream_cmd(pulse_name=pulse_name)
    
    try:
        db.start_streaming(application_id=application_id)
        ffmpeg_process = subprocess.Popen(
            ffmpeg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in ffmpeg_process.stdout:
            logger.warning(line.strip())
        
        ffmpeg_process.wait()
        
        if ffmpeg_process.returncode != 0:
            logger.error(f"FFmpeg exited with code {ffmpeg_process.returncode}")
            raise subprocess.CalledProcessError(ffmpeg_process.returncode, ffmpeg_cmd)
    except Exception as x: 
        logger.exception(x)
        send_ntfy_notification(f"⚠️ {str(x)} ⚠️", priority='max', application_id=application_id)
        
    finally:
       
        send_ntfy_notification(f"⚠️ STREAM OUT STOPPED ⚠️", priority='max', application_id=application_id)
        if ffmpeg_process:
            ffmpeg_process.send_signal(signal.SIGKILL)
        logger.info("Application shutdown complete")


if __name__ == '__main__': 
    main()
