-- Migration 0122: 产品化层 Productization（B12 模块）
-- 组织/角色/成员 + 计划/订阅/权益 + 平台管理 的「独立后端模块」。
-- 注意:这是该模块自身的后端,不是把现有 90+ router 全部按 org 隔离的"全量多租户改造"(后者是另一项大工程)。
-- 安全例外:危机/安全流程永不因订阅状态被阻断;entitlement 检查仅信息性,不阻断。email 标识用户。

CREATE TABLE IF NOT EXISTS organizations (
    id            VARCHAR(64)  PRIMARY KEY,
    slug          VARCHAR(80)  UNIQUE,
    name          VARCHAR(200) NOT NULL,
    organization_type VARCHAR(24) DEFAULT 'church',
    owner_email   VARCHAR(255) NOT NULL,
    status        VARCHAR(12)  DEFAULT 'active',
    created_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_memberships (
    id              VARCHAR(64)  PRIMARY KEY,
    organization_id VARCHAR(64)  NOT NULL,
    email           VARCHAR(255) NOT NULL,
    role_key        VARCHAR(20)  DEFAULT 'member',  -- owner/org_admin/pastor/leader/mentor/care_team/member/viewer
    status          VARCHAR(12)  DEFAULT 'active',
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, email)
);
CREATE INDEX IF NOT EXISTS idx_org_members_email ON organization_memberships (email, status);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_memberships (organization_id, status);

CREATE TABLE IF NOT EXISTS product_plans (
    plan_key        VARCHAR(40)  PRIMARY KEY,
    display_name    VARCHAR(80)  NOT NULL,
    plan_type       VARCHAR(16)  DEFAULT 'individual',
    billing_interval VARCHAR(12) DEFAULT 'monthly',
    price_cents     INT          DEFAULT 0,
    entitlements    JSONB        DEFAULT '{}'::jsonb,
    public          BOOLEAN      DEFAULT TRUE,
    sort_order      INT          DEFAULT 0,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id              VARCHAR(64)  PRIMARY KEY,
    email           VARCHAR(255),
    organization_id VARCHAR(64),
    plan_key        VARCHAR(40)  NOT NULL DEFAULT 'free_individual',
    scope           VARCHAR(12)  DEFAULT 'user',
    status          VARCHAR(12)  DEFAULT 'active',
    billing_provider VARCHAR(12) DEFAULT 'none',
    current_period_end TIMESTAMP,
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_subs_email ON subscriptions (email, status);

CREATE TABLE IF NOT EXISTS platform_admins (
    email      VARCHAR(255) PRIMARY KEY,
    role_key   VARCHAR(20)  DEFAULT 'support_admin',
    status     VARCHAR(12)  DEFAULT 'active',
    created_at TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO product_plans (plan_key, display_name, plan_type, billing_interval, price_cents, entitlements, sort_order) VALUES
 ('free_individual','免费个人版','individual','free',0,'{"ai_tutor":true,"analytics":false,"mentor_dashboard":false,"admin_console":false,"max_org_members":1,"max_ai_messages_per_month":50}',1),
 ('personal_plus','个人增强版','individual','monthly',900,'{"ai_tutor":true,"analytics":true,"mentor_dashboard":false,"admin_console":false,"max_org_members":1,"max_ai_messages_per_month":1000}',2),
 ('small_group','小组版','group','monthly',2900,'{"ai_tutor":true,"analytics":true,"mentor_dashboard":true,"admin_console":false,"max_org_members":20}',3),
 ('church_starter','教会入门版','church','monthly',9900,'{"ai_tutor":true,"analytics":true,"mentor_dashboard":true,"pastoral_care":true,"admin_console":true,"max_org_members":150}',4),
 ('church_pro','教会专业版','church','monthly',24900,'{"ai_tutor":true,"analytics":true,"mentor_dashboard":true,"pastoral_care":true,"admin_console":true,"ministry_match":true,"max_org_members":1000}',5),
 ('enterprise','机构版','enterprise','custom',0,'{"ai_tutor":true,"analytics":true,"mentor_dashboard":true,"pastoral_care":true,"admin_console":true,"ministry_match":true,"api_access":true,"max_org_members":100000}',6)
ON CONFLICT (plan_key) DO NOTHING;
