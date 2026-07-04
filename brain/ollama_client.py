"""
brain/ollama_client.py

Core LLM connector for BestFriendAI. Wraps the Ollama Python
library with logging, error handling, and config-driven settings.
Supports full conversation context (short-term memory), injected
user facts (long-term memory), and a configurable personality.
"""

import time

import ollama

from config.config_loader import load_config, ConfigError
from scripts.logger import get_logger

logger = get_logger(__name__)


class BrainError(Exception):
    """Raised when the LLM fails to respond after all retries."""
    pass


class Brain:
    """
    The 'brain' of BestFriendAI — talks to the local LLM via Ollama.

    Usage:
        brain = Brain(personality=personality_manager)
        reply = brain.think(
            user_message="Hello, how are you?",
            history=[{"role": "user", "content": "..."}, ...],
            known_facts={"name": "Alex"},
        )
    """

    def __init__(self, personality=None):
        try:
            config = load_config()
        except ConfigError as e:
            logger.error("Failed to load config: %s", e)
            raise

        llm_cfg = config.get("llm", {})
        self.model = llm_cfg.get("model", "llama3.1:8b")
        self.host = llm_cfg.get("host", "http://localhost:11434")
        self.temperature = llm_cfg.get("temperature", 0.7)
        self.max_tokens = llm_cfg.get("max_tokens", 512)

        self.personality = personality  # PersonalityManager instance, or None

        self.client = ollama.Client(host=self.host)

        logger.info(
            "Brain initialized with model=%s host=%s temperature=%s",
            self.model, self.host, self.temperature,
        )

        self._verify_connection()

    def _verify_connection(self):
        try:
            available_models = [m["model"] for m in self.client.list().get("models", [])]
        except Exception as e:
            logger.error("Cannot reach Ollama at %s: %s", self.host, e)
            raise BrainError(
                f"Cannot reach Ollama at {self.host}. "
                "Is the Ollama service running? Try: systemctl status ollama"
            )

        if self.model not in available_models:
            logger.warning(
                "Model '%s' not found in Ollama. Available: %s",
                self.model, available_models,
            )
            raise BrainError(
                f"Model '{self.model}' is not pulled yet. "
                f"Run: ollama pull {self.model}"
            )

        logger.info("Ollama connection verified. Model '%s' is ready.", self.model)

    def _build_system_prompt(self, known_facts: dict) -> str:
        """Builds the system prompt from personality.yaml (if provided)
        plus any known facts about the user."""
        if self.personality:
            base = self.personality.build_prompt_section()
        else:
            # Fallback if no personality module was passed in.
            base = (
                "You are a warm, supportive personal AI companion. "
                "You speak naturally and casually, like a close friend."
            )

        if known_facts:
            facts_str = "; ".join(f"{k}: {v}" for k, v in known_facts.items())
            base += f"\n\nThings you know about the user: {facts_str}"

        return base

    def think(
        self,
        user_message: str,
        history: list = None,
        known_facts: dict = None,
        retries: int = 2,
    ) -> str:
        """
        Sends a message to the LLM, including conversation history,
        known user facts, and personality as context.
        """
        if not user_message or not user_message.strip():
            logger.warning("Empty message passed to think(); ignoring.")
            return ""

        history = history or []
        known_facts = known_facts or {}

        messages = [{"role": "system", "content": self._build_system_prompt(known_facts)}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        last_error = None

        for attempt in range(1, retries + 2):
            try:
                logger.debug(
                    "Sending message to LLM (attempt %d, %d context messages)",
                    attempt, len(messages),
                )
                start = time.time()

                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                )

                elapsed = time.time() - start
                reply = response["message"]["content"]

                logger.info("LLM responded in %.2fs (%d chars)", elapsed, len(reply))
                return reply

            except Exception as e:
                last_error = e
                logger.warning("LLM call failed (attempt %d/%d): %s", attempt, retries + 1, e)
                if attempt <= retries:
                    time.sleep(1.5 * attempt)

        logger.error("LLM failed after %d attempts: %s", retries + 1, last_error)
        raise BrainError(f"The AI failed to respond after {retries + 1} attempts: {last_error}")
