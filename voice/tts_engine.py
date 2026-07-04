"""
voice/tts_engine.py

Text-to-speech using Piper (fully offline, runs on CPU).
Converts VARNI's text replies into spoken audio, played through
your speakers. Kept as its own module so we can swap voices or
even swap the whole TTS engine later without touching the brain
or chat loop.
"""

import os
import re
import subprocess
import tempfile

from scripts.logger import get_logger

logger = get_logger(__name__)
# Matches emoji and other pictographic symbols across the common
# Unicode ranges, so we can strip them before sending text to Piper
# (which tries to pronounce every character, including emoji).
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002700-\U000027BF"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001FA70-\U0001FAFF"  # extended symbols
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(text: str) -> str:
    """Removes emoji/pictographic characters from text before TTS,
    since Piper otherwise tries to pronounce them literally."""
    return EMOJI_PATTERN.sub("", text).strip()

class TTSEngine:
    """
    Wraps Piper TTS for converting text to spoken audio.

    Usage:
        tts = TTSEngine()
        tts.speak("Hello, I'm VARNI!")
    """

    def __init__(self, model_name: str = "en_US-amy-medium"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(project_root, "voice", "models", f"{model_name}.onnx")
        self.config_path = f"{self.model_path}.json"

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Voice model not found at {self.model_path}. "
                "Did you download it in Step 9?"
            )

        logger.info("TTSEngine initialized with model: %s", model_name)
    def synthesize_to_bytes(self, text: str) -> bytes:
        """
        Converts text to speech and returns the raw WAV audio bytes,
        without playing it locally. Used by the web API so the
        browser can play the audio itself.
        """
        if not text or not text.strip():
            raise ValueError("Cannot synthesize empty text")

        text = strip_emojis(text)
        if not text:
            raise ValueError("Text was empty after removing emojis")


        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name

        try:
            piper_process = subprocess.run(
                [
                    "python3", "-m", "piper",
                    "--model", self.model_path,
                    "--output_file", wav_path,
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if piper_process.returncode != 0:
                error_msg = piper_process.stderr.decode("utf-8", errors="ignore")
                logger.warning("Piper TTS failed: %s", error_msg)
                raise RuntimeError(f"Piper TTS failed: {error_msg}")

            with open(wav_path, "rb") as f:
                audio_bytes = f.read()

            logger.info("Synthesized %d characters to %d bytes of audio", len(text), len(audio_bytes))
            return audio_bytes

        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
    def speak(self, text: str, enabled: bool = True):
        """
        Converts text to speech and plays it immediately.

        Args:
            text: what to say.
            enabled: if False, skips speaking entirely (useful for a
                     mute toggle without changing calling code).
        """
        if not enabled:
            return

        if not text or not text.strip():
            logger.warning("Empty text passed to speak(); skipping.")
            return

        # Piper can choke on very long text in one go; keep it
        # reasonable for now. We'll add chunking later if needed.
        text = strip_emojis(text)
        if not text:
            logger.warning("Text was empty after removing emojis; skipping.")
            return
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name

        try:
            logger.debug("Generating speech for %d characters", len(text))

            piper_process = subprocess.run(
                [
                    "python3", "-m", "piper",
                    "--model", self.model_path,
                    "--output_file", wav_path,
                ],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )

            if piper_process.returncode != 0:
                logger.warning(
                    "Piper TTS failed: %s",
                    piper_process.stderr.decode("utf-8", errors="ignore"),
                )
                return

            subprocess.run(
                ["play", "-q", wav_path],
                check=True,
                timeout=30,
                capture_output=True,
            )
            logger.info("Spoke %d characters aloud", len(text))

        except subprocess.TimeoutExpired:
            logger.warning("TTS or playback timed out")
        except subprocess.CalledProcessError as e:
            logger.warning("Audio playback failed: %s", e)
        except FileNotFoundError as e:
            logger.warning("Required tool not found: %s", e)
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)
