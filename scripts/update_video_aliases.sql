-- 更新主日学视频别名
-- 执行: psql $DATABASE_URL -f scripts/update_video_aliases.sql

-- 05414bd1 final → 保罗的故事
UPDATE sunday_school_videos 
SET alias = '保罗的故事'
WHERE title ILIKE '%05414bd1%final%'
   OR video_url ILIKE '%05414bd1%'
   OR video_url ILIKE '%baoluo%'
   OR video_url ILIKE '%paul%';

-- bec5d9d2 final → 耶稣复活
UPDATE sunday_school_videos 
SET alias = '耶稣复活'
WHERE title ILIKE '%bec5d9d2%final%'
   OR video_url ILIKE '%bec5d9d2%'
   OR video_url ILIKE '%fuhuo%'
   OR video_url ILIKE '%resurrection%';

-- 1848f3a3 final → 大卫与歌利亚的故事
UPDATE sunday_school_videos 
SET alias = '大卫与歌利亚的故事'
WHERE title ILIKE '%1848f3a3%final%'
   OR video_url ILIKE '%1848f3a3%'
   OR video_url ILIKE '%dawei%'
   OR video_url ILIKE '%goliath%'
   OR video_url ILIKE '%geliya%';

-- d7d28c3a final → 创世六日
UPDATE sunday_school_videos 
SET alias = '创世六日'
WHERE title ILIKE '%d7d28c3a%final%'
   OR video_url ILIKE '%d7d28c3a%'
   OR video_url ILIKE '%chuangshi%'
   OR video_url ILIKE '%creation%';

-- a749f3a9 final → 创世六日
UPDATE sunday_school_videos 
SET alias = '创世六日'
WHERE title ILIKE '%a749f3a9%final%'
   OR video_url ILIKE '%a749f3a9%';

-- 验证更新结果
SELECT id, title, alias, video_url 
FROM sunday_school_videos 
WHERE alias IN ('保罗的故事', '耶稣复活', '大卫与歌利亚的故事', '创世六日')
ORDER BY alias, id;
