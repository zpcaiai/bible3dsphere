-- Migration 0049: 国际化阶段二 —— 用户生成内容(UGC)加写作语言标记 lang。
-- 单列、不双行、不动外键/计数；默认 'zh'。前端跨语言查看时用「翻译」按钮按需机翻。
-- 用 DO 循环：仅对存在的表加列，幂等安全。

DO $$
DECLARE
  t text;
  tables text[] := ARRAY[
    'chat_messages',
    'guardian_messages', 'guardian_memories', 'guardian_devotion_entries',
    'guardian_prayer_entries', 'guardian_spiritual_checkins',
    'community_posts', 'community_comments',
    'examen_entries', 'gratitude_entries', 'memory_verses',
    'waiting_cases', 'waiting_practices', 'waiting_reflections',
    'attachment_patterns', 'attachment_sessions',
    'accountability_checkins', 'accountability_goals',
    'book_marks', 'habit_daily_notes', 'pilgrim_visits',
    'user_verse_feedback', 'voice_groups', 'churches',
    'daily_dew', 'gospel_diagnoses', 'spiritual_checkups',
    'decision_discernments', 'disciple_assessments'
  ];
BEGIN
  FOREACH t IN ARRAY tables LOOP
    IF to_regclass(t) IS NOT NULL THEN
      EXECUTE format('ALTER TABLE %I ADD COLUMN IF NOT EXISTS lang text DEFAULT ''zh''', t);
    END IF;
  END LOOP;
END $$;
