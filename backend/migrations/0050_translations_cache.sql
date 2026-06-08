-- Migration 0050: 按需翻译缓存（UGC「翻译」按钮回源结果，避免重复机翻）。
CREATE TABLE IF NOT EXISTS translations_cache (
    hash       TEXT PRIMARY KEY,          -- sha1(source_text + '|' + target_lang)
    target     TEXT NOT NULL,             -- 目标语言 'en' / 'zh'
    translated TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
