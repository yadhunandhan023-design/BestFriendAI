"""
memory/memory_manager.py

Handles all persistent memory for BestFriendAI:
- conversation history (short-term: recent turns; long-term: full history)
- user profile facts (name, preferences, important dates, etc.)

Everything is stored in a local SQLite database file so it survives
restarts, reboots, and doesn't depend on any external service.
"""

import os
import sqlite3
from datetime import datetime

from scripts.logger import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """
    Manages BestFriendAI's persistent memory using SQLite.

    Usage:
        memory = MemoryManager()
        memory.add_message("user", "Hi, I'm Alex")
        memory.add_message("assistant", "Nice to meet you, Alex!")
        recent = memory.get_recent_messages(limit=10)
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(project_root, "database", "bestfriendai.db")

        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._init_db()
        logger.info("MemoryManager initialized with database at %s", self.db_path)

    def _get_connection(self):
        """Creates a new connection with row access by column name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates tables from schema.sql if they don't already exist.
        Safe to run every time the app starts — CREATE TABLE IF NOT EXISTS
        means existing data is never touched or lost."""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(project_root, "database", "schema.sql")

        if not os.path.exists(schema_path):
            logger.error("schema.sql not found at %s", schema_path)
            raise FileNotFoundError(f"schema.sql not found at {schema_path}")

        with open(schema_path, "r") as f:
            schema = f.read()

        conn = self._get_connection()
        try:
            conn.executescript(schema)
            conn.commit()
            logger.debug("Database schema verified/created.")
        finally:
            conn.close()

    # -------------------- Conversation history --------------------

    def add_message(self, role: str, content: str):
        """Saves one message (from 'user' or 'assistant') to permanent history."""
        if role not in ("user", "assistant"):
            raise ValueError(f"role must be 'user' or 'assistant', got '{role}'")
        if not content or not content.strip():
            logger.warning("Ignoring empty message (role=%s)", role)
            return

        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, datetime.now().isoformat()),
            )
            conn.commit()
            logger.debug("Saved message: role=%s length=%d", role, len(content))
        finally:
            conn.close()

    def get_recent_messages(self, limit: int = 10) -> list:
        """
        Returns the last `limit` messages, oldest first, ready to feed
        straight into the LLM as conversation context.

        Returns a list of dicts like: [{"role": "user", "content": "..."}, ...]
        """
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT role, content FROM conversations "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()

        # rows come back newest-first; reverse so the LLM sees them
        # in correct chronological order.
        messages = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        logger.debug("Retrieved %d recent messages", len(messages))
        return messages

    def clear_conversations(self):
        """Wipes conversation history. Does NOT touch user_profile facts.
        Useful for starting a fresh chat without losing who-you-are info."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM conversations")
            conn.commit()
            logger.info("Conversation history cleared.")
        finally:
            conn.close()
# -------------------- Reminders --------------------

    def add_reminder(self, title: str, message: str, remind_at: str, recurrence: str = "once") -> int:
        """
        Creates a new reminder.

        Args:
            title: short label, e.g. "Drink water"
            message: what VARNI will say/notify, e.g. "Time to drink some water!"
            remind_at: ISO datetime string, e.g. "2026-07-04 09:00:00"
            recurrence: 'once', 'daily', or 'weekly'

        Returns:
            The new reminder's id.
        """
        if recurrence not in ("once", "daily", "weekly"):
            raise ValueError(f"recurrence must be once/daily/weekly, got '{recurrence}'")

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO reminders (title, message, remind_at, recurrence) VALUES (?, ?, ?, ?)",
                (title, message, remind_at, recurrence),
            )
            conn.commit()
            reminder_id = cursor.lastrowid
            logger.info("Added reminder id=%d title='%s' at=%s recurrence=%s",
                        reminder_id, title, remind_at, recurrence)
            return reminder_id
        finally:
            conn.close()

    def get_active_reminders(self) -> list:
        """Returns all active reminders as a list of dicts."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE is_active = 1 ORDER BY remind_at ASC"
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def mark_reminder_fired(self, reminder_id: int, next_remind_at: str = None):
        """
        Records that a reminder just fired. If next_remind_at is given
        (for recurring reminders), updates remind_at to the next occurrence.
        If not given, deactivates the reminder (one-time reminders end here).
        """
        conn = self._get_connection()
        try:
            if next_remind_at:
                conn.execute(
                    "UPDATE reminders SET last_fired_at = ?, remind_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), next_remind_at, reminder_id),
                )
            else:
                conn.execute(
                    "UPDATE reminders SET last_fired_at = ?, is_active = 0 WHERE id = ?",
                    (datetime.now().isoformat(), reminder_id),
                )
            conn.commit()
            logger.debug("Reminder id=%d marked as fired", reminder_id)
        finally:
            conn.close()

    def delete_reminder(self, reminder_id: int):
        """Permanently deletes a reminder."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            logger.info("Deleted reminder id=%d", reminder_id)
        finally:
            conn.close()


    # -------------------- User profile facts --------------------

    def set_fact(self, key: str, value: str):
        """
        Stores or updates a permanent fact about the user.
        e.g. memory.set_fact("name", "Alex")
             memory.set_fact("birthday", "1998-05-14")
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO user_profile (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, value, datetime.now().isoformat()),
            )
            conn.commit()
            logger.info("Saved fact: %s = %s", key, value)
        finally:
            conn.close()

    def get_fact(self, key: str) -> str:
        """Retrieves a single fact by key. Returns None if not set."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT value FROM user_profile WHERE key = ?", (key,)
            ).fetchone()
        finally:
            conn.close()
        return row["value"] if row else None

    def get_all_facts(self) -> dict:
        """Returns all stored facts as a dict, e.g. {'name': 'Alex', 'birthday': '1998-05-14'}."""
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT key, value FROM user_profile").fetchall()
        finally:
            conn.close()
        return {row["key"]: row["value"] for row in rows}
