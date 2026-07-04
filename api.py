"""
api.py

Simple personal web API for VARNI — just for you, no accounts,
no login. Serves the web chat page and connects it to your
existing single-user Brain, MemoryManager, and PersonalityManager.

Run with: uvicorn api:app --host 127.0.0.1 --port 8000
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from brain.ollama_client import Brain, BrainError
from memory.memory_manager import MemoryManager
from personality.personality_manager import PersonalityManager, PersonalityError
from reminders.intent_parser import IntentParser
from voice.tts_engine import TTSEngine
from scripts.logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="VARNI")

personality = PersonalityManager()
brain = Brain(personality=personality)
memory = MemoryManager()
intent_parser = IntentParser(brain)
tts = TTSEngine()

class ChatRequest(BaseModel):
    message: str


@app.get("/")
def serve_ui():
    return FileResponse(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "web", "index.html")
    )


@app.post("/chat")
def chat(req: ChatRequest):
    if not req.message or not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    known_facts = memory.get_all_facts()

    intent = intent_parser.parse_reminder_intent(req.message)
    if intent and intent.get("is_reminder"):
        reminder_id = memory.add_reminder(
            title=intent["title"],
            message=intent["message"],
            remind_at=intent["remind_at"],
            recurrence=intent["recurrence"],
        )
        reply_text = (
            f"Got it! I'll remind you about \"{intent['title']}\" "
            f"at {intent['remind_at']} ({intent['recurrence']})."
        )
        memory.add_message("user", req.message)
        memory.add_message("assistant", reply_text)
        return {"reply": reply_text, "is_reminder": True, "reminder_id": reminder_id}

    memory.add_message("user", req.message)
    history = memory.get_recent_messages(limit=20)[:-1]

    try:
        reply = brain.think(req.message, history=history, known_facts=known_facts)
    except BrainError as e:
        raise HTTPException(status_code=503, detail=str(e))

    memory.add_message("assistant", reply)
    return {"reply": reply, "is_reminder": False}


@app.get("/history")
def get_history(limit: int = 50):
    return memory.get_recent_messages(limit=limit)

@app.post("/speak")
def speak(req: ChatRequest):
    """Generates spoken audio for the given text and returns it as
    a WAV file the browser can play directly."""
    text = req.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")

    try:
        audio_bytes = tts.synthesize_to_bytes(text)
        return Response(content=audio_bytes, media_type="audio/wav")
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/health")
def health():
    return {"status": "ok", "personality": personality.name}
