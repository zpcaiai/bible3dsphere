-- 0097: 成长轻推（next_step 驱动的每日午间提醒）—— 开关 + 去重列
-- 让"今日该做 / 逾期纪律"主动触达用户（对外闭环），默认开启。
ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS growth_on BOOLEAN DEFAULT TRUE;
ALTER TABLE push_subscriptions ADD COLUMN IF NOT EXISTS last_growth_sent DATE;
