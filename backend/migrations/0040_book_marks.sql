-- 属灵书籍：评分 / 想读 / 已读（微信读书式个人书架标记）
CREATE TABLE IF NOT EXISTS book_marks (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL,
  book_id VARCHAR(64) NOT NULL,
  status VARCHAR(16),                                   -- 'want' | 'read' | NULL
  rating SMALLINT CHECK (rating BETWEEN 1 AND 5),       -- 1-5 星，NULL=未评分
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (email, book_id)
);
CREATE INDEX IF NOT EXISTS idx_book_marks_book ON book_marks(book_id);
