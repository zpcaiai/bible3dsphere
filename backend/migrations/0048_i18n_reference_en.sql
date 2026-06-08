-- Migration 0048: 国际化阶段一 —— 参考/种子内容补英文列（_en）
-- 名称类（name/name_zh、title/title_zh、target_nation/target_nation_zh、commander/commander_zh）
-- 已是双语，无需处理；本迁移只补「中文单列」的说明/含义类字段对应的 _en。
-- 全部 IF NOT EXISTS，幂等；回填由 scripts/i18n_backfill.py 一次性机翻完成。

-- 圣经地图集（0039）
ALTER TABLE bible_territories ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE bible_events     ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE bible_events     ADD COLUMN IF NOT EXISTS spiritual_meaning_en text;
ALTER TABLE bible_prophecies ADD COLUMN IF NOT EXISTS description_en text;
ALTER TABLE bible_prophecies ADD COLUMN IF NOT EXISTS fulfillment_description_en text;
ALTER TABLE bible_campaigns  ADD COLUMN IF NOT EXISTS description_en text;

-- 慕道班课程（0023，全中文单列）
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS title_en       text DEFAULT '';
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS teacher_en     text DEFAULT '';
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS scripture_en   text DEFAULT '';
ALTER TABLE seekers_class_courses ADD COLUMN IF NOT EXISTS description_en text DEFAULT '';

-- 圣经地理事件（0011，title/summary 为中文单列，地图站点弹窗显示）
ALTER TABLE geo_events ADD COLUMN IF NOT EXISTS title_en   text;
ALTER TABLE geo_events ADD COLUMN IF NOT EXISTS summary_en text;
