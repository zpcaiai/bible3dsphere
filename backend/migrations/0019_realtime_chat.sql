-- Migration 0019: 圣徒相通 — 好友关系 + 1对1聊天 + 通话房间
-- Realtime feature: friendships, 1:1 chat (QQ-style), small-group voice call rooms.
-- 幂等：所有对象使用 IF NOT EXISTS。用户以 email 标识（沿用 users.email）。

-- ---------------------------------------------------------------------------
-- 1. 好友关系表 (无向：以 user_low/user_high 规范化排序，保证唯一)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS friendships (
    id          SERIAL PRIMARY KEY,
    requester   VARCHAR(255) NOT NULL,          -- 发起方 email
    addressee   VARCHAR(255) NOT NULL,          -- 接收方 email
    user_low    VARCHAR(255) NOT NULL,          -- LEAST(requester, addressee) — 规范化去重
    user_high   VARCHAR(255) NOT NULL,          -- GREATEST(requester, addressee)
    status      VARCHAR(20)  NOT NULL DEFAULT 'pending',  -- pending | accepted | blocked
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_low, user_high)
);
CREATE INDEX IF NOT EXISTS idx_friendships_requester ON friendships(requester);
CREATE INDEX IF NOT EXISTS idx_friendships_addressee ON friendships(addressee);
CREATE INDEX IF NOT EXISTS idx_friendships_status   ON friendships(status);

-- ---------------------------------------------------------------------------
-- 2. 1对1聊天消息表 (离线可达 + 历史记录)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id          BIGSERIAL PRIMARY KEY,
    sender      VARCHAR(255) NOT NULL,          -- 发送方 email
    recipient   VARCHAR(255) NOT NULL,          -- 接收方 email
    body        TEXT NOT NULL,
    kind        VARCHAR(20) NOT NULL DEFAULT 'text',  -- text | image | system
    client_id   VARCHAR(64),                    -- 客户端去重/回执用 (可空)
    delivered   BOOLEAN NOT NULL DEFAULT FALSE, -- 是否已实时投递
    read_at     TIMESTAMP,                      -- 已读时间 (NULL=未读)
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 取某对会话的历史（双向）；按时间排序
CREATE INDEX IF NOT EXISTS idx_chat_pair ON chat_messages(sender, recipient, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_recipient_unread ON chat_messages(recipient, read_at) WHERE read_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at DESC);

