"""
tests/test_scheduler.py

Manual test for the reminder scheduling system.
Adds a reminder 1 minute in the future, starts the scheduler,
and waits for it to fire so you can see the notification appear.
"""

import sys
import os
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.memory_manager import MemoryManager
from scheduler.scheduler_engine import ReminderScheduler


def main():
    print("Starting reminder scheduler test...")
    print("-" * 50)

    memory = MemoryManager()
    scheduler = ReminderScheduler(memory=memory)

    remind_time = (datetime.now() + timedelta(minutes=1)).isoformat()
    reminder_id = memory.add_reminder(
        title="Drink water",
        message="Time to drink some water! Stay hydrated.",
        remind_at=remind_time,
        recurrence="once",
    )
    print(f"Reminder #{reminder_id} scheduled for {remind_time}")
    print("Starting scheduler — waiting up to 90 seconds for it to fire...")
    print("(Watch for a desktop notification popup)\n")

    scheduler.start()

    try:
        time.sleep(90)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.stop()

    print("\nTest complete. Check logs/bestfriendai.log to confirm it fired.")


if __name__ == "__main__":
    main()
