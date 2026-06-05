-- 0042_admin_console.sql — 管理端：users 管理列 + 审计表 + 帖子置顶

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin  BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_banned BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS banned_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ban_reason TEXT DEFAULT '';

-- 将已知管理员同步到 users.is_admin
UPDATE users SET is_admin = TRUE WHERE email = 'zpclord@sina.com';

-- 确保 user_roles 中有 admin 记录（user_roles 有 updated_at 列）
INSERT INTO user_roles (email, role, updated_at)
VALUES ('zpclord@sina.com', 'admin', now())
ON CONFLICT (email) DO UPDATE SET role = 'admin', updated_at = now();

-- 将 user_roles 中全部 admin 同步到 users.is_admin
UPDATE users SET is_admin = TRUE
WHERE email IN (SELECT email FROM user_roles WHERE role = 'admin');

CREATE INDEX IF NOT EXISTS idx_users_is_admin  ON users(is_admin)  WHERE is_admin  = TRUE;
CREATE INDEX IF NOT EXISTS idx_users_is_banned ON users(is_banned) WHERE is_banned = TRUE;

-- 审计日志表
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id           BIGSERIAL    PRIMARY KEY,
    admin_email  VARCHAR(255) NOT NULL,
    action       VARCHAR(60)  NOT NULL,
    target_type  VARCHAR(40)  NOT NULL DEFAULT '',
    target_id    TEXT         NOT NULL DEFAULT '',
    detail       JSONB        NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_admin_audit_created ON admin_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_target  ON admin_audit_log(target_type, target_id);

-- 帖子置顶
ALTER TABLE community_posts ADD COLUMN IF NOT EXISTS pinned_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_community_posts_pinned
    ON community_posts(pinned_at DESC) WHERE pinned_at IS NOT NULL;
