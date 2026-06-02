-- 0034_community_feed.sql — 在线社区：个人状态 + 消息 + 评论 + 阿们
CREATE TABLE IF NOT EXISTS community_posts (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL DEFAULT '',
    nickname      TEXT NOT NULL DEFAULT '弟兄姐妹',
    avatar        TEXT NOT NULL DEFAULT '',
    status_key    TEXT NOT NULL DEFAULT '',
    status_label  TEXT NOT NULL DEFAULT '',
    status_emoji  TEXT NOT NULL DEFAULT '',
    content       TEXT NOT NULL DEFAULT '',
    amen_count    INTEGER NOT NULL DEFAULT 0,
    comment_count INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_community_posts_created ON community_posts (created_at DESC);

CREATE TABLE IF NOT EXISTS community_comments (
    id         BIGSERIAL PRIMARY KEY,
    post_id    BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    email      TEXT NOT NULL DEFAULT '',
    nickname   TEXT NOT NULL DEFAULT '弟兄姐妹',
    avatar     TEXT NOT NULL DEFAULT '',
    content    TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_community_comments_post ON community_comments (post_id, created_at);

CREATE TABLE IF NOT EXISTS community_post_amens (
    post_id    BIGINT NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    email      TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (post_id, email)
);
