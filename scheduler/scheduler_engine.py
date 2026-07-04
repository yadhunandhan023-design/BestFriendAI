"""
scheduler/scheduler_engine.py

Background scheduler that checks for due reminders and fires
notifications. Runs continuously — designed to be started once
and left running (we'll turn this into a proper background
service in a later step).
"""

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from memory.memory_manager import MemoryManager
from scheduler.notifier import send_notification
from scripts.logger import get_logger

logger = get_logger(__name__)


class ReminderScheduler:
    """
    Polls the reminders table every minute and fires notifications
    for anything due. Handles rescheduling recurring reminders
    automatically.

    Usage:
        scheduler = ReminderScheduler()
        scheduler.start()
        # ... keep the program alive ...
        scheduler.stop()
    """

    def __init__(self, memory: MemoryManager = None):
        self.memory = memory or MemoryManager()
        self.scheduler = BackgroundScheduler()
        logger.info("ReminderScheduler initialized")

    def _check_due_reminders(self):
        """Runs every minute: finds reminders whose time has passed
        and haven't fired yet, sends notifications, and reschedules
        recurring ones."""
        now = datetime.now()
        reminders = self.memory.get_active_reminders()

        for reminder in reminders:
            remind_at = datetime.fromisoformat(reminder["remind_at"])

            if remind_at <= now:
                logger.info("Reminder due: '%s'", reminder["title"])
                send_notification(reminder["title"], reminder["message"])

                recurrence = reminder["recurrence"]
                if recurrence == "daily":
                    next_time = (remind_at + timedelta(days=1)).isoformat()
                    self.memory.mark_reminder_fired(reminder["id"], next_remind_at=next_time)
                elif recurrence == "weekly":
                    next_time = (remind_at + timedelta(weeks=1)).isoformat()
                    self.memory.mark_reminder_fired(reminder["id"], next_remind_at=next_time)
                else:  # 'once'
                    self.memory.mark_reminder_fired(reminder["id"])

    def start(self):
        """Starts the background polling loop (checks every 60 seconds)."""
        self.scheduler.add_job(
            self._check_due_reminders,
            "interval",
            seconds=60,
            id="reminder_check",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("ReminderScheduler started — checking every 60 seconds")

    def stop(self):
        """Stops the background scheduler cleanly."""
        self.scheduler.shutdown(wait=False)
        logger.info("ReminderScheduler stopped")
