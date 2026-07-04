"""
tests/test_tts.py

Quick standalone test for the TTS engine.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.tts_engine import TTSEngine


def main():
    print("Testing TTS engine...")
    tts = TTSEngine()
    print("Speaking now — you should hear audio through your speakers...")
    tts.speak("Hello! I'm VARNI, your personal AI companion. Can you hear me clearly?")
    print("Done. Did you hear it?")


if __name__ == "__main__":
    main()
