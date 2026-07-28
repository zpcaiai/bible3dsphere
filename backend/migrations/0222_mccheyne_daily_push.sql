-- Migration 0222: 麦琴每日 08:00 推送偏好与幂等发送日期
-- Web Push 与 FCM 都按设备记录，失败可在下一轮 cron 重试。

ALTER TABLE push_subscriptions
    ADD COLUMN IF NOT EXISTS mccheyne_on BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_mccheyne_sent DATE;

ALTER TABLE fcm_device_tokens
    ADD COLUMN IF NOT EXISTS mccheyne_on BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS last_mccheyne_sent DATE;

CREATE INDEX IF NOT EXISTS idx_push_mccheyne_due
    ON push_subscriptions (last_mccheyne_sent)
    WHERE enabled = TRUE AND mccheyne_on = TRUE;

CREATE INDEX IF NOT EXISTS idx_fcm_mccheyne_due
    ON fcm_device_tokens (last_mccheyne_sent)
    WHERE revoked_at IS NULL AND mccheyne_on = TRUE;
