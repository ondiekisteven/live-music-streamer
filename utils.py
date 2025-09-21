import logging
import requests
from config import Config

Config.configure_logger()
logger = logging.getLogger(__name__)

def send_ntfy_notification(
    message: str,
    topic: str=Config.NTFY_TOPIC,
    title: str = Config.NTFY_TITLE,
    priority: str = Config.NTFY_PRIORITY,
    tags: list[str] = None
) -> None:

    if not topic.startswith('http'):
        logger.error("Error: The topic must be a valid URL starting with 'http' or 'https'.")
        return

    headers = {}
    if title:
        headers['Title'] = title
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
