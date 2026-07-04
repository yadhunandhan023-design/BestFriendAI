"""
scheduler/run_background.py

Standalone entry point for running ONLY the reminder scheduler,
with no chat loop and no input() calls — safe to run permanently
as a systemd background service.

This is what actually keeps reminders firing 24/7, independent of
whether you have a chat terminal open or not.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_manager import MemoryManager
from scheduler.scheduler_engine import ReminderScheduler
from scripts.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("Starting BestFriendAI background scheduler service")

    memory = MemoryManager()
    scheduler = ReminderScheduler(memory=memory)
    scheduler.start()

    logger.info("Background scheduler running. This process will run indefinitely.")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()
        logger.info("Background scheduler stopped.")


if __name__ == "__main__":
    main()
