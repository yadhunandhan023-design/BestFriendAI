"""
tools/control_intent_parser.py

Uses the LLM to detect when the user wants to open an app or search
files, separate from normal conversation and separate from reminder
intent. Mirrors the design of reminders/intent_parser.py.
"""

import json
import re

from scripts.logger import get_logger

logger = get_logger(__name__)

CONTROL_PARSE_PROMPT = """You are a strict JSON extraction tool. Analyze the user's message and determine if they are asking to open an application, search for files, or play something on YouTube.

Respond with ONLY one of these JSON shapes, nothing else:

If opening an app (and NOT asking to play media): {{"action": "open_app", "app_name": "the app name"}}
If searching files: {{"action": "search_files", "query": "search term"}}
If playing a video/song/music on YouTube: {{"action": "play_youtube", "query": "what to search for"}}
If neither: {{"action": "none"}}

IMPORTANT: if the message mentions playing a song, video, or music (even alongside opening a browser), classify it as "play_youtube", NOT "open_app" — opening the browser is handled automatically as part of playing the video.

Examples:
"open chrome" -> {{"action": "open_app", "app_name": "chrome"}}
"find my resume file" -> {{"action": "search_files", "query": "resume"}}
"play believer by imagine dragons" -> {{"action": "play_youtube", "query": "believer imagine dragons"}}
"open firefox and play a song on youtube" -> {{"action": "play_youtube", "query": "popular song"}}
"open youtube and play despacito" -> {{"action": "play_youtube", "query": "despacito"}}
"how are you" -> {{"action": "none"}}
"remind me to drink water" -> {{"action": "none"}}

Respond with ONLY the JSON object, no explanation, no markdown formatting.

User message: "{message}"
"""


class ControlIntentParser:
    """
    Uses the Brain's LLM connection to detect app-open and
    file-search intents from natural language.
    """

    def __init__(self, brain):
        self.brain = brain

    def parse_control_intent(self, message: str) -> dict:
        prompt = CONTROL_PARSE_PROMPT.format(message=message)

        try:
            raw_reply = self.brain.think(prompt, history=[], known_facts={})
        except Exception as e:
            logger.warning("Control intent parsing LLM call failed: %s", e)
            return {"action": "none"}

        json_str = self._extract_json(raw_reply)
        if not json_str:
            return {"action": "none"}

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            return {"action": "none"}

        if not isinstance(data, dict) or "action" not in data:
            return {"action": "none"}

        logger.info("Parsed control intent: %s", data)
        return data

    def _extract_json(self, text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else None
