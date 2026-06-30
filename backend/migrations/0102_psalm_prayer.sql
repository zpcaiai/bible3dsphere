-- Migration 0102: 诗篇祷告 Psalm Prayer（哀歌 / 赞美 / 认罪 / 信靠）
-- 用诗篇的结构带领祷告：在神面前诚实表达真实情绪，又被经文重新定位，
-- 但不强求廉价的正能量——允许未解的哀伤（如诗88），把审判交给神（咒诅诗）。
-- email 标识用户；自由文本过 detect_spiritual_crisis，命中记 crisis_flag 但不阻断。

CREATE TABLE IF NOT EXISTS psalm_profiles (
    psalm_number          INT PRIMARY KEY,
    title                 VARCHAR(120) DEFAULT '',
    psalm_type            VARCHAR(24)  DEFAULT 'mixed',  -- lament/praise/thanksgiving/penitential/trust/wisdom/torah/creation/imprecatory/pilgrimage/royal/messianic/mixed
    translation           VARCHAR(20)  DEFAULT 'CUV',
    text                  TEXT         DEFAULT '',
    dominant_emotions     JSONB        DEFAULT '[]'::jsonb,
    formation_themes      JSONB        DEFAULT '[]'::jsonb,
    suggested_use_cases   JSONB        DEFAULT '[]'::jsonb,
    difficulty            VARCHAR(20)  DEFAULT 'normal',
    caution_notes         TEXT         DEFAULT '',
    sort_order            INT          DEFAULT 0,
    created_at            TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS psalm_prayer_sessions (
    id                      VARCHAR(64)  PRIMARY KEY,
    email                   VARCHAR(255) NOT NULL,
    psalm_number            INT          DEFAULT 0,
    session_date            DATE         NOT NULL,
    mode                    VARCHAR(20)  DEFAULT 'guided', -- guided/lament/praise/confession/trust/thanksgiving/free
    current_movement        VARCHAR(24)  DEFAULT '',
    movements               JSONB        DEFAULT '{}'::jsonb,
    emotional_state_before  JSONB        DEFAULT '[]'::jsonb,
    emotional_state_after   JSONB        DEFAULT '[]'::jsonb,
    key_verse               VARCHAR(200) DEFAULT '',
    honest_prayer_text      TEXT         DEFAULT '',
    reoriented_prayer_text  TEXT         DEFAULT '',
    obedience_or_rest_step  TEXT         DEFAULT '',
    completion_score        INT          DEFAULT 0,
    crisis_flag             VARCHAR(40)  DEFAULT '',
    completed_at            TIMESTAMP,
    created_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_psalm_sessions_email_date
    ON psalm_prayer_sessions (email, session_date DESC);

INSERT INTO psalm_profiles (psalm_number, title, psalm_type, text, dominant_emotions, formation_themes, suggested_use_cases, difficulty, caution_notes, sort_order) VALUES
 (1,  '义人与恶人之路', 'wisdom',      '不从恶人的计谋，不站罪人的道路，惟喜爱耶和华的律法，昼夜思想，这人便为有福。他要像一棵树栽在溪水旁，按时候结果子。', '["定志","平安"]', '["律法","蒙福","扎根"]', '["智慧","默想"]', 'beginner', '', 1),
 (8,  '人算什么',       'creation',    '耶和华我们的主啊，你的名在全地何其美！我观看你指头所造的天，并你所陈设的月亮星宿，便说：人算什么，你竟顾念他？', '["敬畏","惊叹"]', '["创造","尊贵"]', '["赞美","敬拜"]', 'beginner', '', 8),
 (13, '要到几时呢',     'lament',      '耶和华啊，你忘记我要到几时呢？要到永远吗？……但我倚靠你的慈爱；我的心因你的救恩快乐。', '["忧伤","孤单","盼望"]', '["哀歌","信靠"]', '["哀伤","等候"]', 'normal', '允许在未解的等候中诚实呼求，不必急于给出答案。', 13),
 (19, '诸天述说荣耀',   'creation',    '诸天述说神的荣耀，穹苍传扬他的手段。耶和华的律法全备，能苏醒人心；耶和华的法度确定，能使愚人有智慧。', '["敬畏","渴慕"]', '["创造","律法"]', '["智慧","默想"]', 'normal', '', 19),
 (23, '耶和华是我的牧者','trust',      '耶和华是我的牧者，我必不至缺乏。他使我躺卧在青草地上，领我在可安歇的水边。我虽然行过死荫的幽谷，也不怕遭害，因为你与我同在。', '["平安","安全感"]', '["牧养","同在"]', '["焦虑","安息"]', 'beginner', '', 23),
 (27, '我还怕谁呢',     'trust',       '耶和华是我的亮光，是我的拯救，我还怕谁呢？耶和华是我性命的保障，我还惧谁呢？', '["惧怕","勇气"]', '["信靠","勇敢"]', '["恐惧","勇气"]', 'normal', '', 27),
 (32, '得赦免是有福的', 'penitential', '得赦免其过、遮盖其罪的，这人是有福的！我向你陈明我的罪，不隐瞒我的恶……你就赦免我的罪恶。', '["愧疚","释放"]', '["认罪","赦免"]', '["认罪"]', 'normal', '', 32),
 (37, '不要心怀不平',   'wisdom',      '不要为作恶的心怀不平，也不要向那行不义的生出嫉妒。当倚靠耶和华而行善……当默然倚靠耶和华，耐性等候他。', '["愤怒","不平"]', '["公义","忍耐"]', '["不公","愤怒"]', 'normal', '把伸冤交给神，不以恶报恶。', 37),
 (42, '如鹿切慕溪水',   'lament',      '神啊，我的心切慕你，如鹿切慕溪水。我的心渴想神，就是永生神……我的心哪，你为何忧闷？应当仰望神。', '["忧伤","渴慕"]', '["哀歌","渴慕神"]', '["属灵低谷","哀伤"]', 'normal', '属灵枯干是真实的；可以一边忧闷一边仰望，无需假装。', 42),
 (46, '患难中的帮助',   'trust',       '神是我们的避难所，是我们的力量，是我们在患难中随时的帮助。你们要休息，要知道我是神！', '["惧怕","安稳"]', '["避难所","平安"]', '["焦虑","危机"]', 'beginner', '', 46),
 (51, '为我造清洁的心', 'penitential', '神啊，求你按你的慈爱怜恤我，按你丰盛的慈悲涂抹我的过犯……神啊，求你为我造清洁的心，使我里面重新有正直的灵。', '["愧疚","悔改"]', '["认罪","更新"]', '["认罪","悔改"]', 'normal', '认罪是为了被释放、被更新，不是为了定罪自己。', 51),
 (73, '我常与你同在',   'wisdom',      '我见恶人和狂傲人享平安，就心怀不平……然而我常与你同在；你搀着我的右手。除你以外，在天上我有谁呢？', '["嫉妒","不平","安稳"]', '["公义","信靠"]', '["不公","嫉妒"]', 'deep', '把眼目从比较转回到与神同在的真实。', 73),
 (88, '深处的黑夜',     'lament',      '耶和华拯救我的神啊，我昼夜在你面前呼吁……你把我的良朋密友隔在远处，使我所认识的人进入黑暗里。', '["绝望","孤单","黑暗"]', '["哀歌","黑夜"]', '["深度哀伤"]', 'deep', '这是圣经中最黑暗的哀歌，几乎没有转折。允许你停在未解的痛里，不强求正能量。若此刻有自伤或不想活的念头，请立刻联系信任的人或危机陪伴。', 88),
 (100,'普天下欢呼',     'thanksgiving','普天下当向耶和华欢呼！你们当乐意事奉耶和华，当来向他歌唱！当称谢进入他的门，当赞美进入他的院。', '["喜乐","感恩"]', '["赞美","感恩"]', '["感恩","敬拜"]', 'beginner', '', 100),
 (103,'我的心称颂耶和华','praise',     '我的心哪，你要称颂耶和华！不可忘记他的一切恩惠！他赦免你的一切罪孽，医治你的一切疾病。父亲怎样怜恤他的儿女，耶和华也怎样怜恤敬畏他的人。', '["喜乐","感恩"]', '["赞美","慈爱"]', '["感恩","赞美"]', 'beginner', '', 103),
 (119,'藏你话在心里',   'torah',       '行为完全、遵行耶和华律法的，这人便为有福！我将你的话藏在心里，免得我得罪你。你的话是我脚前的灯，是我路上的光。', '["定志","渴慕"]', '["律法","圣洁"]', '["智慧","默想"]', 'deep', '', 119),
 (121,'向山举目',       'pilgrimage',  '我要向山举目，我的帮助从何而来？我的帮助从造天地的耶和华而来。保护你的是耶和华……你出你入，耶和华要保护你。', '["惧怕","安稳"]', '["保护","同在"]', '["出行","惧怕"]', 'beginner', '', 121),
 (130,'从深处求告',     'penitential', '耶和华啊，我从深处向你求告！主啊，求你听我的声音……但在你有赦免之恩，要叫人敬畏你。我等候耶和华，我的心等候。', '["愧疚","盼望"]', '["认罪","等候"]', '["认罪","等候"]', 'normal', '', 130),
 (139,'你已经鉴察我',   'trust',       '耶和华啊，你已经鉴察我，认识我……我的肺腑是你所造的；我在母腹中，你已覆庇我。我要称谢你，因我受造奇妙可畏。', '["被知","安全感"]', '["被神认识","尊贵"]', '["身份","安息"]', 'normal', '', 139),
 (145,'我要尊崇你',     'praise',      '我的神我的王啊，我要尊崇你！我要永永远远称颂你的名……耶和华本为善，他的慈悲覆庇他一切所造的。', '["喜乐","敬畏"]', '["赞美","慈爱"]', '["赞美","敬拜"]', 'beginner', '', 145)
ON CONFLICT (psalm_number) DO NOTHING;
