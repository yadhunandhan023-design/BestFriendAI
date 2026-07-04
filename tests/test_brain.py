"""
tests/test_brain.py

Full VARNI test loop: Brain + Memory + Personality + natural
language reminder detection. Just talk normally — if you ask to
be reminded about something, it's automatically parsed and scheduled.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.ollama_client import Brain, BrainError
from memory.memory_manager import MemoryManager
from personality.personality_manager import PersonalityManager, PersonalityError
from reminders.intent_parser import IntentParser


def main():
    print("Starting VARNI (Brain + Memory + Personality + Reminders) test...")
    print("-" * 50)

    try:
        personality = PersonalityManager()
        brain = Brain(personality=personality)
        memory = MemoryManager()
        intent_parser = IntentParser(brain)
    except (BrainError, PersonalityError) as e:
        print(f"\n[ERROR] Could not start: {e}\n")
        return

    known_facts = memory.get_all_facts()
    print(f"{personality.name} is ready.")
    if known_facts:
        print(f"Loaded {len(known_facts)} known fact(s) about you: {known_facts}")

    print("Type a message and press Enter.")
    print("Try: 'remind me to drink water every day at 9am'")
    print("Special commands: 'quit' or 'exit' to close, 'remember <key>=<value>' to save a fact.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit"):
            print(f"{personality.name}: Talk soon! Everything you said has been saved.")
            break

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

        # Check if this message is a reminder request BEFORE treating
        # it as normal conversation.
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

        # Not a reminder — normal conversation flow.
        memory.add_message("user", user_input)
        history = memory.get_recent_messages(limit=20)[:-1]

        try:
            reply = brain.think(user_input, history=history, known_facts=known_facts)
            memory.add_message("assistant", reply)
            print(f"{personality.name}: {reply}\n")
        except BrainError as e:
            print(f"[ERROR] {e}\n")


if __name__ == "__main__":
    main()
