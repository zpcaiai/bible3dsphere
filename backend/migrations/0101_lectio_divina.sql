-- Migration 0101: 圣经默想 Lectio Divina（读经 → 默想 → 祷告 → 默观 → 顺服）
-- 古典基督教灵修阅读法。慢读一段经文，留意触动你的字句，在神面前默想，
-- 从经文出发祷告，安静默观，最后选择一个 24 小时内的具体顺服。
-- email 标识用户；危机文本由 detect_spiritual_crisis 检测并记录 crisis_flag，但不阻断保存。

CREATE TABLE IF NOT EXISTS lectio_passages (
    id            VARCHAR(64)  PRIMARY KEY,
    ref           VARCHAR(120) NOT NULL,           -- 经文出处（中文，如「诗篇 23」）
    book          VARCHAR(80)  DEFAULT '',
    translation   VARCHAR(20)  DEFAULT 'CUV',
    passage_text  TEXT         DEFAULT '',
    theme_tags    JSONB        DEFAULT '[]'::jsonb,
    difficulty    VARCHAR(20)  DEFAULT 'normal',   -- beginner / normal / deep
    sort_order    INT          DEFAULT 0,
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lectio_sessions (
    id                   VARCHAR(64)  PRIMARY KEY,
    email                VARCHAR(255) NOT NULL,
    passage_id           VARCHAR(64)  DEFAULT '',
    passage_ref          VARCHAR(120) DEFAULT '',
    session_date         DATE         NOT NULL,
    stage                VARCHAR(20)  DEFAULT 'read',  -- read/meditate/pray/contemplate/obey/completed
    read_notes           TEXT         DEFAULT '',
    key_words            JSONB        DEFAULT '[]'::jsonb,
    meditation_notes     TEXT         DEFAULT '',
    prayer_text          TEXT         DEFAULT '',
    contemplation_notes  TEXT         DEFAULT '',
    obedience_action     TEXT         DEFAULT '',
    grace_received       TEXT         DEFAULT '',
    completion_score     INT          DEFAULT 0,
    crisis_flag          VARCHAR(40)  DEFAULT '',
    created_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_lectio_email_date
    ON lectio_sessions (email, session_date DESC);

-- 种子经文（公有领域和合本 CUV 节选）。id 确定性，便于幂等重跑。
INSERT INTO lectio_passages (id, ref, book, passage_text, theme_tags, difficulty, sort_order) VALUES
 ('lec_ps1',  '诗篇 1:1-3',        '诗篇',   '不从恶人的计谋，不站罪人的道路，不坐亵慢人的座位，惟喜爱耶和华的律法，昼夜思想，这人便为有福。他要像一棵树栽在溪水旁，按时候结果子，叶子也不枯干，凡他所做的尽都顺利。', '["蒙福","律法","扎根"]', 'beginner', 10),
 ('lec_ps23', '诗篇 23:1-4',       '诗篇',   '耶和华是我的牧者，我必不至缺乏。他使我躺卧在青草地上，领我在可安歇的水边。他使我的灵魂苏醒，为自己的名引导我走义路。我虽然行过死荫的幽谷，也不怕遭害，因为你与我同在。', '["牧养","安息","同在","不惧怕"]', 'beginner', 20),
 ('lec_ps51', '诗篇 51:10-12',     '诗篇',   '神啊，求你为我造清洁的心，使我里面重新有正直的灵。不要丢弃我，使我离开你的面；不要从我收回你的圣灵。求你使我仍得救恩之乐，赐我乐意的灵扶持我。', '["认罪","更新","救恩"]', 'normal', 30),
 ('lec_mt6',  '马太福音 6:25-27', '马太福音', '所以我告诉你们，不要为生命忧虑吃什么，喝什么；为身体忧虑穿什么。生命不胜于饮食吗？身体不胜于衣裳吗？你们看那天上的飞鸟，也不种，也不收，你们的天父尚且养活它。', '["忧虑","信靠","天父供应"]', 'normal', 40),
 ('lec_jn15', '约翰福音 15:4-5',  '约翰福音', '你们要常在我里面，我也常在你们里面。枝子若不常在葡萄树上，自己就不能结果子；你们若不常在我里面，也是这样。我是葡萄树，你们是枝子。常在我里面的，我也常在他里面，这人就多结果子；因为离了我，你们就不能做什么。', '["连结","结果子","住在主里"]', 'normal', 50),
 ('lec_ro12', '罗马书 12:1-2',    '罗马书',  '所以弟兄们，我以神的慈悲劝你们，将身体献上，当作活祭，是圣洁的，是神所喜悦的；你们如此事奉乃是理所当然的。不要效法这个世界，只要心意更新而变化，叫你们察验何为神的善良、纯全、可喜悦的旨意。', '["献上","更新","分别为圣"]', 'deep', 60),
 ('lec_ga5',  '加拉太书 5:22-23', '加拉太书', '圣灵所结的果子，就是仁爱、喜乐、和平、忍耐、恩慈、良善、信实、温柔、节制。这样的事没有律法禁止。', '["圣灵果子","品格"]', 'beginner', 70),
 ('lec_php4', '腓立比书 4:6-7',   '腓立比书', '应当一无挂虑，只要凡事借着祷告、祈求和感谢，将你们所要的告诉神。神所赐出人意外的平安，必在基督耶稣里保守你们的心怀意念。', '["不挂虑","祷告","平安"]', 'beginner', 80),
 ('lec_col3', '歌罗西书 3:1-2',   '歌罗西书', '所以你们若真与基督一同复活，就当求在上面的事；那里有基督坐在神的右边。你们要思念上面的事，不要思念地上的事。', '["复活生命","思念上面"]', 'normal', 90),
 ('lec_mt11', '马太福音 11:28-30','马太福音', '凡劳苦担重担的人，可以到我这里来，我就使你们得安息。我心里柔和谦卑，你们当负我的轭，学我的样式，这样，你们心里就必得享安息。因为我的轭是容易的，我的担子是轻省的。', '["安息","担重担","柔和谦卑"]', 'beginner', 100)
ON CONFLICT (id) DO NOTHING;
