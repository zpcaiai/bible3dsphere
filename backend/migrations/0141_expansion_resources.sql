-- 0141_expansion_resources.sql — 推荐书目/圣诗的用户收藏（content-theology-expansion 批次）
-- 书目/诗歌目录本身在 expansion_content.py（真理表）；此处只持久化用户收藏。email-keyed；幂等。
CREATE TABLE IF NOT EXISTS resource_bookmarks (
    id         VARCHAR(64) PRIMARY KEY,
    email      VARCHAR(255) NOT NULL,
    slug       VARCHAR(120) NOT NULL,
    kind       VARCHAR(16) NOT NULL DEFAULT 'book',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (email, slug)
);
CREATE INDEX IF NOT EXISTS idx_resource_bookmarks_email ON resource_bookmarks (email, created_at DESC);
