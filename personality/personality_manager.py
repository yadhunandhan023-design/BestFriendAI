"""
personality/personality_manager.py

Loads the AI's identity, traits, tone, and behavior rules from
personality.yaml and turns them into a system prompt for the LLM.
This keeps "who the AI is" fully separate from "how it talks to
the model" (brain/ollama_client.py) — so tuning personality never
requires touching core logic.
"""

import os
import yaml

from scripts.logger import get_logger

logger = get_logger(__name__)


class PersonalityError(Exception):
    """Raised when personality.yaml is missing or malformed."""
    pass


class PersonalityManager:
    """
    Loads and exposes the AI's personality definition.

    Usage:
        personality = PersonalityManager()
        prompt_piece = personality.build_prompt_section()
        name = personality.name
    """

    def __init__(self, personality_path: str = None):
        if personality_path is None:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            personality_path = os.path.join(project_root, "personality", "personality.yaml")

        self.personality_path = personality_path
        self._data = self._load()

        identity = self._data.get("identity", {})
        self.name = identity.get("name", "Assistant")
        self.role = identity.get("role", "AI assistant")

        logger.info("Personality loaded: name=%s role=%s", self.name, self.role)

    def _load(self) -> dict:
        if not os.path.exists(self.personality_path):
            logger.error("personality.yaml not found at %s", self.personality_path)
            raise PersonalityError(f"personality.yaml not found at {self.personality_path}")

        try:
            with open(self.personality_path, "r") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise PersonalityError(f"personality.yaml has invalid YAML syntax: {e}")

        if not data:
            raise PersonalityError("personality.yaml is empty.")

        return data

    def build_prompt_section(self) -> str:
        """
        Converts the personality definition into a block of text
        suitable for injecting into the LLM's system prompt.
        """
        identity = self._data.get("identity", {})
        traits = self._data.get("traits", [])
        tone = self._data.get("tone", {})
        rules = self._data.get("behavior_rules", [])

        name = identity.get("name", "Assistant")
        role = identity.get("role", "AI assistant")

        lines = [
            f"Your name is {name}. You are the user's {role}.",
        ]

        if traits:
            lines.append(f"Your personality traits: {', '.join(traits)}.")

        if tone:
            style = tone.get("style", "")
            humor = tone.get("humor", "")
            tone_desc = []
            if style:
                tone_desc.append(f"speak in a {style} way")
            if humor:
                tone_desc.append(f"humor should be {humor}")
            if tone_desc:
                lines.append("Tone: " + "; ".join(tone_desc) + ".")

        if rules:
            lines.append("Rules you always follow:")
            for rule in rules:
                lines.append(f"- {rule}")

        return "\n".join(lines)

    def reload(self):
        """Re-reads personality.yaml from disk without restarting the app.
        Useful if you edit personality.yaml while the AI is running."""
        self._data = self._load()
        identity = self._data.get("identity", {})
        self.name = identity.get("name", "Assistant")
        self.role = identity.get("role", "AI assistant")
        logger.info("Personality reloaded: name=%s role=%s", self.name, self.role)

