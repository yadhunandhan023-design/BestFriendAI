# BestFriendAI (Jarvis)

A fully local, privacy-first personal AI companion — built from scratch, running entirely on your own hardware with zero paid APIs.

## Features
- 🧠 Local LLM brain (Ollama + Llama 3.1 8B, GPU-accelerated)
- 💾 Persistent memory (conversations + facts survive restarts)
- 🎭 Configurable personality (name, tone, traits — fully editable via YAML)
- ⏰ Natural language reminders with background scheduling
- 🎤 Voice input (offline speech-to-text via faster-whisper)
- 🔊 Voice output (offline text-to-speech via Piper)
- 🌐 Web chat interface (FastAPI + vanilla JS)
- 🖥️ App control & file search (permission-gated)
- 🌍 Browser automation (YouTube search & playback, permission-gated)
- ⚙️ Runs as a background systemd service

## Stack
- **LLM**: Ollama (Llama 3.1 8B)
- **Memory**: SQLite
- **Voice**: faster-whisper (STT) + Piper (TTS)
- **Backend**: FastAPI
- **Automation**: Selenium

## Requirements
- Linux (developed on Kali)
- NVIDIA GPU (tested on RTX 4050)
- Python 3.11+
- Ollama installed locally

## Setup
See individual module docstrings for details. Core setup:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.1:8b
python main.py
```

## Safety Design
All system/browser actions require explicit user confirmation before executing. App control uses an allowlist, not arbitrary command execution. No internet exposure — designed for local personal use only.

## Status
Actively in development. Built step-by-step as a learning project.
EOF
