-- Migration 0038: formation 身份统一 — sfds_formation_metrics.user_id 数字id → email
-- 背景：formation 历史按数字 users.id 落库，其余子系统皆按 email。门徒塑造整合层
-- 需要统一身份。配合 formation_engine._canon_uid（读写两端把数字id归一化为email），
-- 这条回填把存量历史行也转成 email，使新旧数据连续一致。
-- 安全：只动"纯数字且能在 users 表匹配到非空 email"的行；转换后不再是数字，幂等可重复执行。

UPDATE sfds_formation_metrics m
   SET user_id = u.email
  FROM users u
 WHERE m.user_id ~ '^[0-9]+$'
   AND u.id::text = m.user_id
   AND u.email IS NOT NULL
   AND u.email <> '';
