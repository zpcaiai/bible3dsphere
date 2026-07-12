-- Migration 0209: FCM 设备推送 token（移动端 Android/iOS 服务端推送）
-- 每个设备 token 一条记录；同一 token 被新用户注册时改挂到新用户（ON CONFLICT upsert）。
-- revoked_at 非空表示已失效：用户主动退订，或 FCM 返回 404/UNREGISTERED 时由发送器标记。

CREATE TABLE IF NOT EXISTS fcm_device_tokens (
    id            VARCHAR(64)  PRIMARY KEY,
    user_email    VARCHAR(255) NOT NULL,
    token         TEXT         NOT NULL UNIQUE,
    platform      VARCHAR(16)  NOT NULL DEFAULT 'android' CHECK (platform IN ('android', 'ios')),

    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fcm_tokens_email  ON fcm_device_tokens (user_email);
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_active ON fcm_device_tokens (user_email) WHERE revoked_at IS NULL;
