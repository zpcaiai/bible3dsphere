-- Skill 61: full-lifecycle budget, scenarios, reserves and cash flow.
CREATE TABLE IF NOT EXISTS mission_financial_plans (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,sending_journey_id TEXT,worker_profile_id TEXT NOT NULL,team_id TEXT,
 plan_version INTEGER NOT NULL DEFAULT 1,base_currency TEXT NOT NULL DEFAULT 'USD',target_field_id TEXT,term_start_date DATE,term_end_date DATE,
 household_size INTEGER NOT NULL DEFAULT 1,plan_status TEXT NOT NULL DEFAULT 'draft' CHECK(plan_status IN('draft','data_collection','scenario_review','worker_review','agency_review','financial_review','approved','active','review_required','underfunded','paused','superseded','closed')),
 inflation_assumption NUMERIC(5,4),exchange_rate_assumption NUMERIC(12,6),contingency_rate NUMERIC(5,4),sensitivity_level TEXT NOT NULL DEFAULT 'P3',
 created_by TEXT NOT NULL,approved_by TEXT,approved_at TIMESTAMPTZ,next_review_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_budget_scenarios (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,financial_plan_id UUID NOT NULL REFERENCES mission_financial_plans(id),
 scenario_key TEXT NOT NULL,scenario_name TEXT,scenario_type TEXT NOT NULL CHECK(scenario_type IN('baseline','conservative','high_inflation','currency_depreciation','support_loss','medical_event','family_emergency','education_cost_increase','early_return','evacuation','delayed_start','single_income_loss')),
 total_monthly_need NUMERIC(14,2),total_startup_need NUMERIC(14,2),emergency_reserve_target NUMERIC(14,2),evacuation_reserve_target NUMERIC(14,2),funding_gap NUMERIC(14,2),
 status TEXT NOT NULL DEFAULT 'draft',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,financial_plan_id,scenario_key));
CREATE TABLE IF NOT EXISTS mission_budget_items (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,budget_scenario_id UUID NOT NULL REFERENCES mission_budget_scenarios(id),
 category_key TEXT NOT NULL,item_name TEXT NOT NULL,amount NUMERIC(14,2) NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',
 recurrence_type TEXT NOT NULL CHECK(recurrence_type IN('one_time','weekly','monthly','quarterly','annual','term_based','event_triggered')),
 owner_type TEXT NOT NULL DEFAULT 'worker',owner_id TEXT,verification_status TEXT NOT NULL DEFAULT 'unverified',created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_financial_reserves (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,financial_plan_id UUID NOT NULL REFERENCES mission_financial_plans(id),
 reserve_type TEXT NOT NULL CHECK(reserve_type IN('operating','medical','emergency','evacuation','reentry','home_assignment','tax','education','equipment_replacement')),
 target_amount NUMERIC(14,2),current_amount NUMERIC(14,2) NOT NULL DEFAULT 0,minimum_required_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
 restriction_policy TEXT,custodian_organization_id TEXT,verification_status TEXT NOT NULL DEFAULT 'unverified',reviewed_at TIMESTAMPTZ,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS mission_cash_flow_forecasts (
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),tenant_id TEXT NOT NULL,financial_plan_id UUID NOT NULL REFERENCES mission_financial_plans(id),
 forecast_month DATE NOT NULL,expected_income NUMERIC(14,2),committed_income NUMERIC(14,2),probable_income NUMERIC(14,2),expected_expense NUMERIC(14,2),
 reserve_contribution NUMERIC(14,2),projected_ending_balance NUMERIC(14,2),risk_status TEXT,created_at TIMESTAMPTZ NOT NULL DEFAULT now(),UNIQUE(tenant_id,financial_plan_id,forecast_month));
ALTER TABLE mission_financial_plans ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_budget_scenarios ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_budget_items ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_financial_reserves ENABLE ROW LEVEL SECURITY;ALTER TABLE mission_cash_flow_forecasts ENABLE ROW LEVEL SECURITY;
DO $$DECLARE t TEXT;BEGIN FOREACH t IN ARRAY ARRAY['mission_financial_plans','mission_budget_scenarios','mission_budget_items','mission_financial_reserves','mission_cash_flow_forecasts'] LOOP EXECUTE format('DROP POLICY IF EXISTS mission_tenant_isolation ON %I',t);EXECUTE format('CREATE POLICY mission_tenant_isolation ON %I USING(tenant_id=current_setting(''app.tenant_id'',true)) WITH CHECK(tenant_id=current_setting(''app.tenant_id'',true))',t);END LOOP;END$$;
CREATE INDEX IF NOT EXISTS idx_mission_fin_plan_worker ON mission_financial_plans(tenant_id,worker_profile_id,plan_status);
CREATE INDEX IF NOT EXISTS idx_mission_budget_scenario ON mission_budget_scenarios(tenant_id,financial_plan_id,scenario_type);
CREATE INDEX IF NOT EXISTS idx_mission_reserve_plan ON mission_financial_reserves(tenant_id,financial_plan_id,reserve_type);
-- Rollback: drop cash_flow_forecasts, financial_reserves, budget_items, budget_scenarios, then financial_plans.
