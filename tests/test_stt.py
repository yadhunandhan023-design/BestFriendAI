"""
tests/test_stt.py

Quick standalone test for the speech-to-text engine.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.stt_engine import STTEngine


def main():
    print("Loading Whisper model (this may take a moment the first time)...")
    stt = STTEngine(model_size="base")

    print("\nReady! You'll have 5 seconds to speak once recording starts.")
    input("Press Enter when you're ready to start recording...")

    text = stt.listen_and_transcribe(duration_seconds=5)

    print(f"\nYou said: \"{text}\"")


if __name__ == "__main__":
    main()
