-- Migration 0126: 计费(Stripe)+ 平台审核 Billing & Platform Moderation（B12-4）
-- Stripe 字段挂到既有 subscriptions;平台安全审核日志独立成表,绝不复制用户危机隐私正文。

ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_customer_id     VARCHAR(80);
ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(80);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub ON subscriptions(stripe_subscription_id);

-- 平台安全团队对危机事件的复核日志(只记复核动作,不复制 triggering_message/evidence 等用户隐私正文)
CREATE TABLE IF NOT EXISTS crisis_moderation_reviews (
    id                VARCHAR(64)  PRIMARY KEY,
    crisis_event_id   TEXT         NOT NULL,
    reviewed_by_email VARCHAR(255) NOT NULL,
    action            VARCHAR(30)  DEFAULT 'reviewed',  -- reviewed/escalated/resource_sent/closed
    note              TEXT         DEFAULT '',           -- 复核动作备注(非用户隐私正文)
    created_at        TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_crisis_reviews_event ON crisis_moderation_reviews(crisis_event_id);

-- 平台审核审计日志(组织停用/恢复、计划变更等平台级动作)
CREATE TABLE IF NOT EXISTS platform_moderation_log (
    id          VARCHAR(64)  PRIMARY KEY,
    admin_email VARCHAR(255) NOT NULL,
    action      VARCHAR(40)  NOT NULL,
    target_type VARCHAR(24)  DEFAULT '',
    target_id   VARCHAR(64)  DEFAULT '',
    note        TEXT         DEFAULT '',
    created_at  TIMESTAMPTZ  DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_platform_modlog_admin ON platform_moderation_log(admin_email, created_at);
