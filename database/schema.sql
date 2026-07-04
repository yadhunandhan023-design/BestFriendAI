-- database/schema.sql
-- Core tables for BestFriendAI's memory system.

-- Every message either the user or the AI has ever sent.
-- This is the raw conversation log — the foundation for
-- both short-term (recent) and long-term (searchable) memory.
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Key facts about the user that should never be forgotten:
-- name, preferences, important dates, relationships, etc.
-- This is separate from raw conversation so the AI can quickly
-- recall "who is this person" without scanning years of chat logs.
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index to make recent-conversation lookups fast even after
-- years of accumulated chat history.
CREATE INDEX IF NOT EXISTS idx_conversations_timestamp
    ON conversations(timestamp);
-- Reminders: one-time or recurring nudges VARNI gives you.
-- recurrence: 'once', 'daily', 'weekly' — controls whether the
-- scheduler reschedules it after it fires.
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    remind_at DATETIME NOT NULL,
    recurrence TEXT NOT NULL DEFAULT 'once' CHECK(recurrence IN ('once', 'daily', 'weekly')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_fired_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_reminders_remind_at
    ON reminders(remind_at);
