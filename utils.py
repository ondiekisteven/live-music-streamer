import logging
from urllib.parse import parse_qs, urlparse
import requests
import yt_dlp
from config import Config

Config.configure_logger()
logger = logging.getLogger(__name__)

def send_ntfy_notification(
    message: str,
    topic: str=Config.NTFY_TOPIC,
    title: str = Config.NTFY_TITLE,
    priority: str = Config.NTFY_PRIORITY,
    tags: list[str] = None,
    application_id: int = 1
) -> None:

    if tags is None: 
        tags = []
    if not topic.startswith('http'):
        logger.error("Error: The topic must be a valid URL starting with 'http' or 'https'.")
        return

    headers = {}
    tags.append(f"app_{application_id}")
    if title:
        headers['Title'] = f"{title} [{application_id}]"
    if priority:
        headers['Priority'] = priority
    if tags:
        headers['Tags'] = ",".join(tags)

    try:
        response = requests.post(topic, data=message, headers=headers)
        response.raise_for_status() 
        logger.info("Notification sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification: {e}")



def extract_playlist_id(url: str):
    """Extract playlist ID from a YouTube URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    playlist_id = query.get("list", [None])[0]
    return playlist_id

def get_playlist_videos(playlist_url):
    """Fetch playlist metadata using yt-dlp."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
        if "entries" in info:
            return [
                {
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "artist": entry.get("channel"),
                    "thumbnail": entry.get("thumbnails")[0]['url'] if len(entry.get("thumbnails")) > 0 else "",
                    "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
                }
                for entry in info["entries"] if entry
            ]
        else:
            return [
                {
                    "id": info.get("id"),
                    "title": info.get("title"),
                    "artist": info.get("channel"),
                    "url": info.get("webpage_url"),
                    "thumbnail": info.get("thumbnails")[0]['url'] if len(info.get("thumbnails")) > 0 else "",
                }
            ]
