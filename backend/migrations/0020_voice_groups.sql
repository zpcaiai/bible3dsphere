-- Migration 0020: 语音群组 — 多人实时语音通话 (LiveKit SFU)
-- 在已有「圣徒相通」(migration 0019: friendships / chat_messages / call_rooms) 之上，
-- 新增持久化的「语音群」：两个或以上登录用户可建群、凭邀请码加入、进行 Zoom 级群语音。
--
-- 媒体层用 LiveKit 托管 SFU（真正的 Zoom 级音质：Opus + RED 抗丢包 + Krisp AI 降噪 +
-- 服务端回声消除 + 自带 TURN）。后端只负责「群成员管理」与「签发进房 JWT」，
-- 音频流不经过本服务（零媒体成本，可扩到多人）。
--
-- 幂等：所有对象使用 IF NOT EXISTS。用户以 email 标识（沿用 users.email）。

-- ---------------------------------------------------------------------------
-- 1. 语音群表
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS voice_groups (
    id           VARCHAR(64)  PRIMARY KEY,                  -- uuid
    name         VARCHAR(120) NOT NULL DEFAULT '语音祷告群',
    owner        VARCHAR(255) NOT NULL,                     -- 创建者 email
    join_code    VARCHAR(12)  NOT NULL UNIQUE,              -- 可分享的短邀请码
    max_members  INTEGER      NOT NULL DEFAULT 10,          -- 群上限（SFU 可承载 5-10+）
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    archived_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_voice_groups_owner  ON voice_groups(owner);
CREATE INDEX IF NOT EXISTS idx_voice_groups_active ON voice_groups(is_active) WHERE is_active = TRUE;

-- ---------------------------------------------------------------------------
-- 2. 群成员表 (谁在哪个群里 —— 通话名单)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS voice_group_members (
    group_id   VARCHAR(64)  NOT NULL,
    email      VARCHAR(255) NOT NULL,
    role       VARCHAR(20)  NOT NULL DEFAULT 'member',   -- owner | member
    joined_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (group_id, email)
);
CREATE INDEX IF NOT EXISTS idx_voice_group_members_email ON voice_group_members(email);
CREATE INDEX IF NOT EXISTS idx_voice_group_members_group ON voice_group_members(group_id);
