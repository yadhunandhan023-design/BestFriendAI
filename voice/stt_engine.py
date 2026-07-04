"""
voice/stt_engine.py

Speech-to-text using faster-whisper (fully offline, runs on CPU).
Records audio from the microphone and transcribes it to text, so
VARNI can understand spoken input instead of only typed messages.
"""

import os
import tempfile
import time

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav
from scipy.signal import resample
from faster_whisper import WhisperModel

from scripts.logger import get_logger

logger = get_logger(__name__)

WHISPER_SAMPLE_RATE = 16000  # Whisper requires exactly 16kHz
RECORDING_SAMPLE_RATE = 48000  # what your microphone hardware actually supports
MIC_DEVICE_INDEX = 8  # confirmed working mic input (sof-hda-dsp hw:1,6)


class STTEngine:
    """
    Wraps faster-whisper for converting spoken audio into text.

    Usage:
        stt = STTEngine()
        text = stt.listen_and_transcribe(duration_seconds=5)
    """

    def __init__(self, model_size: str = "base"):
        logger.info("Loading Whisper model '%s' (CPU)...", model_size)
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("Whisper model loaded and ready.")

    def record_audio(self, duration_seconds: int = 5) -> str:
        """Records audio from the microphone at its native sample
        rate, resamples it down to 16kHz for Whisper, and saves it
        to a temporary WAV file. Returns the file path."""
        logger.info("Recording for %d seconds...", duration_seconds)
        print("Get ready...")
        time.sleep(1)
        print(f"🎤 Listening for {duration_seconds} seconds... speak now!")

        recording = sd.rec(
            int(duration_seconds * RECORDING_SAMPLE_RATE),
            samplerate=RECORDING_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=MIC_DEVICE_INDEX,
        )
        sd.wait()

        num_samples_target = int(len(recording) * WHISPER_SAMPLE_RATE / RECORDING_SAMPLE_RATE)
        resampled = resample(recording.flatten(), num_samples_target).astype(np.int16)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
            wav_path = tmp_wav.name

        write_wav(wav_path, WHISPER_SAMPLE_RATE, resampled)
        logger.debug("Recorded audio saved to %s", wav_path)
        return wav_path

    def transcribe(self, wav_path: str) -> str:
        """Transcribes a WAV file to text using Whisper."""
        try:
            segments, info = self.model.transcribe(wav_path, beam_size=5,language="en")
            text = " ".join(segment.text.strip() for segment in segments).strip()
            logger.info(
                "Transcribed audio (language=%s, confidence=%.2f): '%s'",
                info.language, info.language_probability, text,
            )
            return text
        finally:
            if os.path.exists(wav_path):
                os.remove(wav_path)

    def listen_and_transcribe(self, duration_seconds: int = 5) -> str:
        """Records from mic then immediately transcribes it.
        Returns the transcribed text (empty string if nothing understandable was captured)."""
        wav_path = self.record_audio(duration_seconds)
        text = self.transcribe(wav_path)

        if not text:
            print("(Didn't catch that — try again)")

        return text
