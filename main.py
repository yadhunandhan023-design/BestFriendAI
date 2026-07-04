"""
main.py

BestFriendAI unified entry point.

Runs the chat loop and the background reminder scheduler together,
in a single process. Voice output is on-demand only — VARNI stays
silent by default and speaks only when you prefix your message with
"speak:".
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.ollama_client import Brain, BrainError
from memory.memory_manager import MemoryManager
from personality.personality_manager import PersonalityManager, PersonalityError
from reminders.intent_parser import IntentParser
from scheduler.scheduler_engine import ReminderScheduler
from voice.tts_engine import TTSEngine
from voice.stt_engine import STTEngine
from tools.control_intent_parser import ControlIntentParser
from tools.system_control import describe_open_app, describe_search_files, execute_action
from tools.browser_control import describe_play_youtube, execute_browser_action, close_browser
from scripts.logger import get_logger

logger = get_logger(__name__)


def run_chat_loop(brain, memory, personality, intent_parser,control_parser, tts,stt):
    """Main conversational loop. Runs on the main thread and blocks
    on input(), while the scheduler (on its own thread) keeps
    checking for due reminders independently in the background."""

    known_facts = memory.get_all_facts()
    print(f"{personality.name} is ready and running (reminders active in the background).")
    if known_facts:
        print(f"Loaded {len(known_facts)} known fact(s) about you: {known_facts}")

    print("Type a message and press Enter.")
    print("Try: 'remind me to drink water every day at 9am'")
    print("Prefix a message with 'speak:' to hear VARNI say it out loud.")
    print("Special commands: 'quit' or 'exit' to close, 'remember <key>=<value>' to save a fact.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{personality.name}: Talk soon!")
            break

        if not user_input:
            continue
        if user_input.lower() == "listen":
            user_input = stt.listen_and_transcribe(duration_seconds=5)
            if not user_input:
                continue
            print(f"You (spoken): {user_input}")
        if user_input.lower() in ("quit", "exit"):
            print(f"{personality.name}: Talk soon! Everything you said has been saved.")
            break

        if user_input.lower().startswith("speak:"):
            message_to_speak = user_input[6:].strip()
            if not message_to_speak:
                print("[ERROR] Use format: speak: <your message>\n")
                continue

            memory.add_message("user", message_to_speak)
            history = memory.get_recent_messages(limit=20)[:-1]

            try:
                reply = brain.think(message_to_speak, history=history, known_facts=known_facts)
                memory.add_message("assistant", reply)
                print(f"{personality.name}: {reply}\n")
                tts.speak(reply)
            except BrainError as e:
                print(f"[ERROR] {e}\n")
            continue

        if user_input.lower().startswith("remember "):
            try:
                fact = user_input[9:]
                key, value = fact.split("=", 1)
                key = key.strip().lower()
                value = value.strip()
                memory.set_fact(key, value)
                known_facts[key] = value
                print(f"[Saved] {key} = {value}\n")
            except ValueError:
                print("[ERROR] Use format: remember key=value\n")
            continue
        control_intent = control_parser.parse_control_intent(user_input)

        if control_intent.get("action") == "open_app":
            result = describe_open_app(control_intent["app_name"])
            if not result["allowed"]:
                print(f"{personality.name}: I can't open that — {result['reason']}")
                print(f"I can open: {', '.join(result['available_apps'])}\n")
            else:
                confirm = input(f"{personality.name}: {result['description']} — confirm? (yes/no): ").strip().lower()
                if confirm in ("yes", "y"):
                    outcome = execute_action(result)
                    print(f"{personality.name}: {outcome}\n")
                else:
                    print(f"{personality.name}: Okay, not doing that.\n")
            continue

        if control_intent.get("action") == "search_files":
            result = describe_search_files(control_intent["query"])
            print(f"{personality.name}: {result['description']}")
            for match in result.get("matches", []):
                print(f"  - {match}")
            print()
            continue
        if control_intent.get("action") == "play_youtube":
            result = describe_play_youtube(control_intent["query"])
            if not result["allowed"]:
                print(f"{personality.name}: {result['reason']}\n")
            else:
                confirm = input(f"{personality.name}: {result['description']} — confirm? (yes/no): ").strip().lower()
                if confirm in ("yes", "y"):
                    print(f"{personality.name}: Opening browser, this may take a few seconds...")
                    outcome = execute_browser_action(result)
                    print(f"{personality.name}: {outcome}\n")
                else:
                    print(f"{personality.name}: Okay, not doing that.\n")
            continue
        intent = intent_parser.parse_reminder_intent(user_input)

        if intent and intent.get("is_reminder"):
            reminder_id = memory.add_reminder(
                title=intent["title"],
                message=intent["message"],
                remind_at=intent["remind_at"],
                recurrence=intent["recurrence"],
            )
            print(
                f"{personality.name}: Got it! I'll remind you about "
                f"\"{intent['title']}\" at {intent['remind_at']} "
                f"({intent['recurrence']}). [Reminder #{reminder_id}]\n"
            )
            memory.add_message("user", user_input)
            memory.add_message(
                "assistant",
                f"Got it! I'll remind you about \"{intent['title']}\" at {intent['remind_at']}.",
            )
            continue

        memory.add_message("user", user_input)
        history = memory.get_recent_messages(limit=20)[:-1]

        try:
            reply = brain.think(user_input, history=history, known_facts=known_facts)
            memory.add_message("assistant", reply)
            print(f"{personality.name}: {reply}\n")
        except BrainError as e:
            print(f"[ERROR] {e}\n")


def main():
    print("=" * 50)
    print("  BestFriendAI — Starting Up")
    print("=" * 50)

    try:
        personality = PersonalityManager()
        brain = Brain(personality=personality)
        memory = MemoryManager()
        intent_parser = IntentParser(brain)
       	control_parser = ControlIntentParser(brain)
        tts = TTSEngine()
        stt = STTEngine(model_size="base")
    except (BrainError, PersonalityError, FileNotFoundError) as e:
        print(f"\n[FATAL ERROR] Could not start: {e}\n")
        logger.error("Startup failed: %s", e)
        sys.exit(1)

    scheduler = ReminderScheduler(memory=MemoryManager())
    scheduler.start()
    logger.info("Main process started: chat loop + background scheduler")

    try:
        run_chat_loop(brain, memory, personality, intent_parser,control_parser, tts,stt)
    finally:
        scheduler.stop()
        close_browser()
        print("\nScheduler stopped. Goodbye!")


if __name__ == "__main__":
    main()
