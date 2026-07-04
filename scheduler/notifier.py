"""
scheduler/notifier.py

Sends desktop notifications using Linux's notify-send.
Kept separate from the scheduler logic so we can later swap this
for voice output (Step: Voice) without touching scheduling code.
"""

import subprocess

from scripts.logger import get_logger

logger = get_logger(__name__)


def send_notification(title: str, message: str):
    """
    Fires a desktop popup notification.
    Fails silently (logs a warning) if notify-send isn't available,
    so a missing notification tool never crashes the whole app.
    """
    try:
        subprocess.run(
            ["notify-send", title, message],
            check=True,
            timeout=5,
        )
        logger.info("Notification sent: %s - %s", title, message)
    except FileNotFoundError:
        logger.warning("notify-send not found. Install with: sudo apt install libnotify-bin")
    except subprocess.CalledProcessError as e:
        logger.warning("notify-send failed: %s", e)
    except subprocess.TimeoutExpired:
        logger.warning("notify-send timed out")
