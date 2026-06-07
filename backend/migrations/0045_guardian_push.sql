-- Migration 0045: 守护者云推送（Web Push 关怀消息）
-- guardian_profiles 加推送偏好开关 + 每日去重列。
-- 复用 0025 的 push_subscriptions（VAPID Web Push），不引入 FCM/APNs。

ALTER TABLE guardian_profiles ADD COLUMN IF NOT EXISTS care_push_on   BOOLEAN DEFAULT TRUE;
ALTER TABLE guardian_profiles ADD COLUMN IF NOT EXISTS last_care_push DATE;
