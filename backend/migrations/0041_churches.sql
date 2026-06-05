-- 0041_churches.sql — 多教会数据隔离：教会实体 + 成员 + 邀请码 + 公开标记
--
-- 设计注记
-- --------
-- chat_messages / friendships / 评论 / 阿们 不加 church_id：
--   好友与聊天跨教会合法（已接受好友关系不因换教会而断裂），
--   评论和阿们随父帖 church_id 隔离，无需单独标注。

CREATE TABLE IF NOT EXISTS churches (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(120) NOT NULL,
    slug         VARCHAR(64),
    owner_email  VARCHAR(255) NOT NULL DEFAULT '',
    join_code    VARCHAR(12)  NOT NULL UNIQUE,
    is_default   BOOLEAN      NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_churches_default ON churches(is_default) WHERE is_default = TRUE;

CREATE TABLE IF NOT EXISTS church_members (
    church_id  INTEGER      NOT NULL REFERENCES churches(id) ON DELETE CASCADE,
    email      VARCHAR(255) NOT NULL UNIQUE,
    role       VARCHAR(20)  NOT NULL DEFAULT 'member',
    joined_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    PRIMARY KEY (church_id, email)
);
CREATE INDEX IF NOT EXISTS idx_church_members_church ON church_members(church_id);

ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS church_id INTEGER;
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_community_posts_church ON community_posts(church_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_community_posts_public ON community_posts(created_at DESC) WHERE is_public = TRUE;

ALTER TABLE prayers ADD COLUMN IF NOT EXISTS church_id INTEGER;
ALTER TABLE prayers ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE;
-- prayers 表有 updated_at 列（main.py 建表 + migration 0003 均已确认）
CREATE INDEX IF NOT EXISTS idx_prayers_church ON prayers(church_id, updated_at DESC);

ALTER TABLE voice_groups ADD COLUMN IF NOT EXISTS church_id INTEGER;

-- 默认教会（平台种子数据）
INSERT INTO churches (name, owner_email, join_code, is_default)
SELECT '情感星球大家庭', 'zpclord@sina.com', 'HOME2026', TRUE
WHERE NOT EXISTS (SELECT 1 FROM churches WHERE is_default = TRUE);

-- 将全部现有用户加入默认教会
INSERT INTO church_members (church_id, email, role)
SELECT (SELECT id FROM churches WHERE is_default = TRUE), u.email,
       CASE WHEN u.email = 'zpclord@sina.com' THEN 'owner' ELSE 'member' END
FROM users u
ON CONFLICT (email) DO NOTHING;

-- 将现有内容归属默认教会
UPDATE community_posts SET church_id = (SELECT id FROM churches WHERE is_default = TRUE) WHERE church_id IS NULL;
UPDATE prayers        SET church_id = (SELECT id FROM churches WHERE is_default = TRUE) WHERE church_id IS NULL;
UPDATE voice_groups   SET church_id = (SELECT id FROM churches WHERE is_default = TRUE) WHERE church_id IS NULL;
