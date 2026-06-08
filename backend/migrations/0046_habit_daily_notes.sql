-- Per-habit, per-day note (does NOT count as a habit execution).
CREATE TABLE IF NOT EXISTS habit_daily_notes (
    user_id   TEXT NOT NULL,
    habit_id  TEXT NOT NULL,
    note_date DATE NOT NULL,
    note      TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, habit_id, note_date)
);
