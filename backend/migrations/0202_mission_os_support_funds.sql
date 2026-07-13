-- Skill 62/63/64: support campaigns/pledges, fund governance and anti-fraud.
CREATE TABLE IF NOT EXISTS mission_support_campaigns (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,financial_plan_id TEXT,campaign_type TEXT NOT NULL,
 campaign_version INTEGER NOT NULL DEFAULT 1,title TEXT NOT NULL,public_summary TEXT,target_amount NUMERIC(14,2),target_monthly_amount NUMERIC(14,2),currency TEXT NOT NULL DEFAULT 'USD',
 starts_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,campaign_status TEXT NOT NULL DEFAULT 'draft',content_reviewed BOOLEAN NOT NULL DEFAULT FALSE,approved_by TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_support_pledges (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,campaign_id UUID NOT NULL REFERENCES mission_support_campaigns(id),
 supporter_reference TEXT NOT NULL,supporter_type TEXT,pledge_type TEXT,amount NUMERIC(14,2) NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',recurrence_rule TEXT,
 starts_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,pledge_status TEXT NOT NULL DEFAULT 'pledged' CHECK(pledge_status IN('invited','pledged','active','paused','cancelled','expired','completed','uncollectible')),
 privacy_preference TEXT NOT NULL DEFAULT 'private',governance_rights_none BOOLEAN NOT NULL DEFAULT TRUE,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CHECK(governance_rights_none));
CREATE TABLE IF NOT EXISTS mission_support_receipts (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,pledge_id UUID REFERENCES mission_support_pledges(id),receiving_fund_id TEXT NOT NULL,
 amount NUMERIC(14,2) NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',received_at TIMESTAMPTZ NOT NULL DEFAULT now(),payment_reference TEXT,restricted_purpose TEXT,reconciliation_status TEXT NOT NULL DEFAULT 'unreconciled',created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_funds (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,owning_organization_id TEXT NOT NULL,fund_type TEXT NOT NULL,fund_name TEXT NOT NULL,base_currency TEXT NOT NULL DEFAULT 'USD',
 restriction_type TEXT NOT NULL DEFAULT 'general' CHECK(restriction_type IN('general','restricted')),restriction_summary TEXT,accounting_adapter_reference TEXT,fund_status TEXT NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_expense_requests (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,fund_id UUID NOT NULL REFERENCES mission_funds(id),requester_id TEXT NOT NULL,budget_item_id TEXT,
 expense_type TEXT,amount NUMERIC(14,2) NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',purpose TEXT,request_status TEXT NOT NULL DEFAULT 'submitted',
 approvals_count INTEGER NOT NULL DEFAULT 0,submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_expense_approvals (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,expense_request_id UUID NOT NULL REFERENCES mission_expense_requests(id),approver_id TEXT NOT NULL,
 approval_stage TEXT,decision TEXT NOT NULL CHECK(decision IN('approve','reject')),approved_amount NUMERIC(14,2),rationale TEXT,decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 UNIQUE(tenant_id,expense_request_id,approver_id));
CREATE TABLE IF NOT EXISTS mission_financial_findings (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,subject_type TEXT NOT NULL,subject_id TEXT NOT NULL,rule_key TEXT NOT NULL,
 finding_type TEXT NOT NULL,severity TEXT NOT NULL DEFAULT 'medium',summary TEXT,status TEXT NOT NULL DEFAULT 'open',assigned_to TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),resolved_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS mission_financial_disclosures (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,user_id TEXT NOT NULL,disclosure_type TEXT NOT NULL,related_party_reference TEXT,relationship_summary TEXT,
 disclosure_status TEXT NOT NULL DEFAULT 'submitted',reviewed_by TEXT,starts_at TIMESTAMPTZ,ends_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
ALTER TABLE mission_support_campaigns ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_support_pledges ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_support_receipts ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_funds ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_expense_requests ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_expense_approvals ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_financial_findings ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_financial_disclosures ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_support_campaigns','mission_support_pledges','mission_support_receipts','mission_funds','mission_expense_requests','mission_expense_approvals','mission_financial_findings','mission_financial_disclosures'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_pledge_campaign ON mission_support_pledges(tenant_id,campaign_id,pledge_status);
CREATE INDEX IF NOT EXISTS idx_mission_expense_fund ON mission_expense_requests(tenant_id,fund_id,request_status);
CREATE INDEX IF NOT EXISTS idx_mission_fin_finding ON mission_financial_findings(tenant_id,status,severity);
-- Rollback: drop disclosures, findings, expense_approvals, expense_requests, funds, receipts, pledges, then campaigns.
