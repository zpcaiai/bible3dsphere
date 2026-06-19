-- 自高之事 RAG 知识库 / Stronghold knowledge corpus for retrieval.
-- 嵌入以 JSONB float[] 存储（便于在 Python 中做 cosine，避免对 pgvector 扩展的硬依赖；
-- 语料很小，纯 Python 余弦足够）。未配置嵌入时 embedding 为 NULL，走关键词检索。

CREATE TABLE IF NOT EXISTS stronghold_rag_documents (
  id TEXT PRIMARY KEY,
  doc_type TEXT NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  lang TEXT DEFAULT 'zh',
  tags TEXT[] DEFAULT '{}',
  stronghold_codes TEXT[] DEFAULT '{}',
  doctrine_codes TEXT[] DEFAULT '{}',
  embedding JSONB,
  embed_model TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stronghold_rag_type ON stronghold_rag_documents (doc_type);
CREATE INDEX IF NOT EXISTS idx_stronghold_rag_sh ON stronghold_rag_documents USING GIN (stronghold_codes);
CREATE INDEX IF NOT EXISTS idx_stronghold_rag_doc ON stronghold_rag_documents USING GIN (doctrine_codes);
