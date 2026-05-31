-- Migration 0018: geo_events 增加 image/audio 媒体列，并回填关键事件配图
-- Depends on 0011 (geo_events)。幂等：列 IF NOT EXISTS；UPDATE 可重复。

ALTER TABLE geo_events ADD COLUMN IF NOT EXISTS image TEXT;
ALTER TABLE geo_events ADD COLUMN IF NOT EXISTS audio TEXT;

UPDATE geo_events SET image = 'https://commons.wikimedia.org/wiki/Special:FilePath/The_Crossing_of_The_Red_Sea.jpg?width=640'
WHERE title = '过红海，法老追兵覆没';

UPDATE geo_events SET image = 'https://commons.wikimedia.org/wiki/Special:FilePath/Rembrandt_-_Moses_with_the_Ten_Commandments_-_Google_Art_Project.jpg?width=640'
WHERE title = '颁布十诫与立约';

UPDATE geo_events SET image = 'https://commons.wikimedia.org/wiki/Special:FilePath/V%26A_-_Raphael%2C_St_Paul_Preaching_in_Athens_(1515).jpg?width=640'
WHERE title = '亚略巴古讲"未识之神"';
