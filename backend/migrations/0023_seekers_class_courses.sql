-- Migration 0023: 宣教tab — 慕道班课程 (seekers class / catechism courses)
-- 仿主日学视频：列表主要走 R2 动态枚举，本表供后台手动登记课程元数据（可选）。
-- 一条记录 = 一节课，可含文字/PPT/视频任一或多种资源 URL。
-- 幂等：所有对象使用 IF NOT EXISTS。

CREATE TABLE IF NOT EXISTS seekers_class_courses (
    id             SERIAL PRIMARY KEY,
    title          VARCHAR(255) NOT NULL DEFAULT '',   -- 课程标题
    teacher        VARCHAR(100) DEFAULT '',            -- 讲员
    scripture      TEXT DEFAULT '',                    -- 相关经文
    description    TEXT DEFAULT '',                    -- 课程简介
    text_url       TEXT DEFAULT '',                    -- 文字讲义 (txt/md/doc/pdf)
    ppt_url        TEXT DEFAULT '',                    -- 幻灯片 (ppt/pptx/pdf)
    video_url      TEXT DEFAULT '',                    -- 视频 (mp4/mov/webm/m4v)
    duration_sec   INTEGER DEFAULT 0,
    sort_order     INTEGER DEFAULT 0,
    is_visible     BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_scc_sort
    ON seekers_class_courses(sort_order, created_at)
    WHERE is_visible = TRUE;
