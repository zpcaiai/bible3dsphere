-- 0092_worldview_belief_enrichment.sql
-- Worldview Formation OS — 持久化结构化 AI 富信息（truth_mapper / DiagnosisAgentOutput）
-- 幂等：ADD COLUMN IF NOT EXISTS。
-- 注：worldview_beliefs.biblical_evaluation / related_scripture_refs 已在 0070 存在
--     （承载 diagnoser 的 biblicalCounterTruth / scriptureAnchors），无需在此新增。
--     distorted_beliefs.severity 已在 0071 存在；此处仅补充 truth-map 的其余 AI 字段。

ALTER TABLE distorted_beliefs ADD COLUMN IF NOT EXISTS gospel_reframe           TEXT;
ALTER TABLE distorted_beliefs ADD COLUMN IF NOT EXISTS scripture_refs           JSONB   DEFAULT '[]';
ALTER TABLE distorted_beliefs ADD COLUMN IF NOT EXISTS requires_pastor_attention BOOLEAN DEFAULT FALSE;
ALTER TABLE distorted_beliefs ADD COLUMN IF NOT EXISTS possible_root            TEXT;

CREATE INDEX IF NOT EXISTS idx_distorted_beliefs_pastor
    ON distorted_beliefs(requires_pastor_attention) WHERE requires_pastor_attention = TRUE;
