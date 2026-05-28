-- Migration 0003: add emotion_label and mood index columns to user_checkins
-- These columns allow fast server-side aggregation for the emotion-trajectory API
-- without having to parse the JSONB data blob on every query.

ALTER TABLE user_checkins
    ADD COLUMN IF NOT EXISTS emotion_label VARCHAR(100) DEFAULT '',
    ADD COLUMN IF NOT EXISTS mood          VARCHAR(50)  DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_checkins_email_emotion
    ON user_checkins (email, emotion_label)
    WHERE emotion_label <> '';

CREATE INDEX IF NOT EXISTS idx_checkins_email_mood
    ON user_checkins (email, mood)
    WHERE mood <> '';

-- Back-fill from existing JSONB data where possible
UPDATE user_checkins
SET
    emotion_label = COALESCE(
        NULLIF(emotion_label, ''),
        data->>'emotionLabel',
        data->>'emotion_label',
        ''
    ),
    mood = COALESCE(
        NULLIF(mood, ''),
        data->>'mood',
        ''
    )
WHERE emotion_label = '' OR mood = '';
