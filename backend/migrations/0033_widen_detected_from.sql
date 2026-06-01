-- Migration 0033: 将 attachment_patterns.detected_from 扩到 VARCHAR(64)
-- （0021 最初为 VARCHAR(40)；多信号源逗号拼接最长 48 字符。加宽到 64 与路由层 [:64] 一致。）
-- ALTER TYPE 到更宽的 VARCHAR 是安全且幂等的（重复执行不报错）。
ALTER TABLE attachment_patterns ALTER COLUMN detected_from TYPE VARCHAR(64);
