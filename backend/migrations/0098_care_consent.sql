-- 0098: 关怀可见性同意 —— 成员可控制自己的成长风险是否进入牧者关怀汇总。
-- 默认 TRUE（沿用既有行为）；成员可随时关闭，formation_flags 即排除其数据。
CREATE TABLE IF NOT EXISTS care_consent (
  email TEXT PRIMARY KEY,
  share_formation_flags BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
