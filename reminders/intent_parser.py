"""
reminders/intent_parser.py

Uses the LLM to detect reminder requests inside normal conversation
and extract structured data (title, datetime, recurrence) from them.
Keeps this logic separate from brain/ollama_client.py so the core
brain stays a generic chat interface, and reminder-specific parsing
lives in its own module.
"""

import json
import re
from datetime import datetime

from scripts.logger import get_logger

logger = get_logger(__name__)


REMINDER_PARSE_PROMPT = """You are a strict JSON extraction tool. Analyze the user's message and determine if they are asking to be reminded about something.

Current date and time: {now}

If the message IS a reminder request, respond with ONLY this JSON (no other text):
{{"is_reminder": true, "title": "short title", "message": "friendly reminder message", "remind_at": "YYYY-MM-DD HH:MM:SS", "recurrence": "once"}}

recurrence must be exactly one of: "once", "daily", "weekly"

If the message is NOT a reminder request, respond with ONLY this JSON:
{{"is_reminder": false}}

CRITICAL TIME CONVERSION RULES:
- remind_at MUST use 24-hour format (00:00 to 23:59), never 12-hour AM/PM format.
- "7:22 PM" or "7:22pm" MUST convert to 19:22:00 - add 12 to the hour when PM and hour is not 12.
- "7:22 AM" or "7:22am" MUST convert to 07:22:00 - keep hour as-is when AM (unless it's 12 AM, which becomes 00).
- "12 PM" / "12pm" / "noon" = 12:00:00
- "12 AM" / "12am" / "midnight" = 00:00:00
- Double check your conversion before responding: PM times (except 12 PM) always have an hour of 13-23.

OTHER RULES:
- Always compute remind_at as an absolute future datetime based on the current date/time given above.
- If no specific time is mentioned for a recurring reminder, default to 09:00:00.
- If the time mentioned has already passed today, schedule it for the next valid occurrence (tomorrow, or next week for weekly).
- Respond with ONLY the JSON object, nothing else. No explanation, no markdown formatting, no code fences.

User message: "{message}"
"""


class IntentParser:
    """
    Uses the Brain's LLM connection to detect and parse reminder
    intents from natural language.

    Usage:
        parser = IntentParser(brain)
        result = parser.parse_reminder_intent("remind me to drink water daily at 9am")
        if result and result["is_reminder"]:
            memory.add_reminder(result["title"], result["message"], result["remind_at"], result["recurrence"])
    """

    def __init__(self, brain):
        self.brain = brain

    def parse_reminder_intent(self, message: str) -> dict:
        """
        Returns a dict like:
            {"is_reminder": True, "title": ..., "message": ..., "remind_at": ..., "recurrence": ...}
        or:
            {"is_reminder": False}
        Returns None if parsing fails entirely (LLM gave unusable output).
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        prompt = REMINDER_PARSE_PROMPT.format(now=now_str, message=message)

        try:
            raw_reply = self.brain.think(prompt, history=[], known_facts={})
        except Exception as e:
            logger.warning("Intent parsing LLM call failed: %s", e)
            return None

        json_str = self._extract_json(raw_reply)
        if not json_str:
            logger.warning("Could not find JSON in LLM reply: %s", raw_reply[:200])
            return None

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from LLM: %s | raw: %s", e, json_str[:200])
            return None

        if not isinstance(data, dict) or "is_reminder" not in data:
            logger.warning("Unexpected JSON shape from LLM: %s", data)
            return None

        if data.get("is_reminder"):
            required = ("title", "message", "remind_at", "recurrence")
            if not all(k in data for k in required):
                logger.warning("Reminder JSON missing required fields: %s", data)
                return None
            if not self._validate_datetime(data["remind_at"]):
                logger.warning("Invalid remind_at format: %s", data["remind_at"])
                return None
            if data["recurrence"] not in ("once", "daily", "weekly"):
                data["recurrence"] = "once"

        logger.info("Parsed intent: %s", data)
        return data

    def _extract_json(self, text: str) -> str:
        """LLMs sometimes wrap JSON in markdown code fences or add
        stray text. This pulls out just the JSON object."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else None

    def _validate_datetime(self, dt_str: str) -> bool:
        try:
            datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            return True
        except (ValueError, TypeError):
            return False
