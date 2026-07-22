-- ============================================================================
-- SFDS Core Schema (Part 1/3) - Tables & Indexes
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Users table
CREATE TABLE IF NOT EXISTS sfds_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    nickname VARCHAR(100),
    avatar_url TEXT,
    spiritual_maturity_score INTEGER CHECK (spiritual_maturity_score BETWEEN 0 AND 10) DEFAULT 5,
    discernment_history_count INTEGER DEFAULT 0,
    personality_type VARCHAR(20),
    decision_style VARCHAR(20),
    email_notifications BOOLEAN DEFAULT true,
    weekly_digest BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- Decision Events
CREATE TABLE IF NOT EXISTS sfds_decision_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) NOT NULL CHECK (category IN ('career', 'relationship', 'temptation', 'calling', 'financial', 'health', 'ministry', 'other')),
    urgency_level INTEGER CHECK (urgency_level BETWEEN 1 AND 5) DEFAULT 3,
    importance_level INTEGER CHECK (importance_level BETWEEN 1 AND 5) DEFAULT 3,
    reversibility BOOLEAN DEFAULT false,
    deadline_date DATE,
    final_decision TEXT,
    outcome_status VARCHAR(20) DEFAULT 'pending' CHECK (outcome_status IN ('pending', 'implemented', 'reversed', 'abandoned', 'ongoing')),
    processing_status VARCHAR(20) DEFAULT 'analyzing' CHECK (processing_status IN ('analyzing', 'guided', 'decided', 'reviewed', 'archived')),
    motive_analysis JSONB,
    discernment_result JSONB,
    guidance_output JSONB,
    context_factors JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed_at TIMESTAMP WITH TIME ZONE,
    decided_at TIMESTAMP WITH TIME ZONE,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE
);

-- State Snapshots
CREATE TABLE IF NOT EXISTS sfds_state_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    stress_level INTEGER CHECK (stress_level BETWEEN 0 AND 10) DEFAULT 5,
    anxiety_level INTEGER CHECK (anxiety_level BETWEEN 0 AND 10) DEFAULT 5,
    fatigue_level INTEGER CHECK (fatigue_level BETWEEN 0 AND 10) DEFAULT 5,
    spiritual_dryness_level INTEGER CHECK (spiritual_dryness_level BETWEEN 0 AND 10) DEFAULT 5,
    emotional_stability_level INTEGER CHECK (emotional_stability_level BETWEEN 0 AND 10) DEFAULT 5,
    overall_wellbeing_score INTEGER CHECK (overall_wellbeing_score BETWEEN 0 AND 10),
    decision_readiness_score INTEGER CHECK (decision_readiness_score BETWEEN 0 AND 10),
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 0 AND 10),
    physical_health INTEGER CHECK (physical_health BETWEEN 0 AND 10),
    relational_harmony INTEGER CHECK (relational_harmony BETWEEN 0 AND 10),
    financial_pressure INTEGER CHECK (financial_pressure BETWEEN 0 AND 10),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_notes TEXT
);

-- Emotion Logs
CREATE TABLE IF NOT EXISTS sfds_emotion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    emotion_type VARCHAR(50) NOT NULL,
    intensity INTEGER CHECK (intensity BETWEEN 0 AND 10) NOT NULL,
    trigger_description TEXT,
    trigger_category VARCHAR(50),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_minutes INTEGER,
    metric_snapshot_id UUID
);

-- Motive Analyses
CREATE TABLE IF NOT EXISTS sfds_motive_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    fear_driven_score DECIMAL(3,2) CHECK (fear_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    pride_driven_score DECIMAL(3,2) CHECK (pride_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    love_driven_score DECIMAL(3,2) CHECK (love_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    desire_driven_score DECIMAL(3,2) CHECK (desire_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    duty_driven_score DECIMAL(3,2) CHECK (duty_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    ambition_driven_score DECIMAL(3,2) CHECK (ambition_driven_score BETWEEN 0.0 AND 1.0) DEFAULT 0.0,
    primary_motive VARCHAR(20) NOT NULL,
    secondary_motive VARCHAR(20),
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0) DEFAULT 0.5,
    analysis_algorithm VARCHAR(50) DEFAULT 'v1.0-rule-based',
    extracted_keywords TEXT[],
    sentiment_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Discernment Results
CREATE TABLE IF NOT EXISTS sfds_discernment_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    primary_source VARCHAR(30) NOT NULL,
    secondary_source VARCHAR(30),
    source_confidence DECIMAL(3,2) CHECK (source_confidence BETWEEN 0.0 AND 1.0) DEFAULT 0.5,
    biblical_alignment_score DECIMAL(3,2) CHECK (biblical_alignment_score BETWEEN 0.0 AND 1.0),
    long_term_fruit_prediction DECIMAL(3,2) CHECK (long_term_fruit_prediction BETWEEN -1.0 AND 1.0),
    explanation_text TEXT,
    alternative_explanations TEXT[],
    has_spiritual_warning BOOLEAN DEFAULT false,
    has_psychological_warning BOOLEAN DEFAULT false,
    has_practical_warning BOOLEAN DEFAULT false,
    warning_details JSONB,
    supporting_principle_ids UUID[],
    conflicting_principle_ids UUID[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Guidance Outputs
CREATE TABLE IF NOT EXISTS sfds_guidance_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    structured_advice TEXT NOT NULL,
    summary_advice VARCHAR(500),
    primary_risks TEXT[],
    risk_severity VARCHAR(10) CHECK (risk_severity IN ('low', 'medium', 'high', 'critical')),
    alternative_interpretations TEXT[],
    blind_spots TEXT[],
    recommended_actions TEXT[],
    immediate_actions TEXT[],
    long_term_actions TEXT[],
    priority_level VARCHAR(10) CHECK (priority_level IN ('low', 'medium', 'high', 'urgent')) DEFAULT 'medium',
    suggested_timeline VARCHAR(100),
    recommended_scriptures TEXT[],
    recommended_practices TEXT[],
    recommended_readings TEXT[],
    follow_up_questions TEXT[],
    guidance_version VARCHAR(20) DEFAULT 'v1.0',
    generation_algorithm VARCHAR(50),
    used_llm BOOLEAN DEFAULT false,
    llm_model VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Spiritual Principles (with pgvector)
CREATE TABLE IF NOT EXISTS sfds_spiritual_principles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    principle_text TEXT NOT NULL,
    principle_summary VARCHAR(200),
    scripture_reference VARCHAR(100),
    scripture_text TEXT,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(50),
    applicable_contexts TEXT[],
    applicable_emotions TEXT[],
    teaching_notes TEXT,
    historical_examples TEXT[],
    counter_principles UUID[],
    embedding VECTOR(1536),
    search_keywords TEXT[],
    search_vectors TSVECTOR,
    reference_count INTEGER DEFAULT 0,
    last_referenced_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES sfds_users(id)
);

-- Decision-Principles Junction
CREATE TABLE IF NOT EXISTS sfds_decision_principles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    principle_id UUID NOT NULL REFERENCES sfds_spiritual_principles(id) ON DELETE CASCADE,
    relationship_type VARCHAR(20) CHECK (relationship_type IN ('supporting', 'conflicting', 'neutral', 'primary', 'secondary')) DEFAULT 'supporting',
    relevance_score DECIMAL(3,2) CHECK (relevance_score BETWEEN 0.0 AND 1.0),
    application_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(decision_id, principle_id)
);

-- Decision Reviews
CREATE TABLE IF NOT EXISTS sfds_decision_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    decision_id UUID NOT NULL REFERENCES sfds_decision_events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    outcome_description TEXT NOT NULL,
    outcome_category VARCHAR(20) CHECK (outcome_category IN ('positive', 'negative', 'mixed', 'neutral', 'ongoing', 'unclear')),
    peace_level INTEGER CHECK (peace_level BETWEEN -5 AND 5),
    regret_level INTEGER CHECK (regret_level BETWEEN 0 AND 10),
    satisfaction_level INTEGER CHECK (satisfaction_level BETWEEN 0 AND 10),
    followed_guidance BOOLEAN,
    guidance_accuracy INTEGER CHECK (guidance_accuracy BETWEEN 0 AND 10),
    character_growth TEXT,
    spiritual_lessons TEXT,
    relational_impact TEXT,
    what_went_well TEXT[],
    what_could_improve TEXT[],
    what_i_learned TEXT,
    review_date DATE NOT NULL,
    days_since_decision INTEGER,
    would_decide_differently BOOLEAN,
    what_would_change TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Spiritual Metrics (Time-series)
CREATE TABLE IF NOT EXISTS sfds_spiritual_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    metric_period VARCHAR(10) DEFAULT 'daily' CHECK (metric_period IN ('daily', 'weekly', 'monthly')),
    prayer_consistency INTEGER CHECK (prayer_consistency BETWEEN 0 AND 10),
    scripture_engagement INTEGER CHECK (scripture_engagement BETWEEN 0 AND 10),
    meditation_practice INTEGER CHECK (meditation_practice BETWEEN 0 AND 10),
    fasting_frequency INTEGER CHECK (fasting_frequency BETWEEN 0 AND 10),
    community_connection INTEGER CHECK (community_connection BETWEEN 0 AND 10),
    service_activity INTEGER CHECK (service_activity BETWEEN 0 AND 10),
    giving_generosity INTEGER CHECK (giving_generosity BETWEEN 0 AND 10),
    humility_score INTEGER CHECK (humility_score BETWEEN 0 AND 10),
    patience_score INTEGER CHECK (patience_score BETWEEN 0 AND 10),
    self_control_score INTEGER CHECK (self_control_score BETWEEN 0 AND 10),
    love_score INTEGER CHECK (love_score BETWEEN 0 AND 10),
    joy_score INTEGER CHECK (joy_score BETWEEN 0 AND 10),
    peace_score INTEGER CHECK (peace_score BETWEEN 0 AND 10),
    emotional_regulation INTEGER CHECK (emotional_regulation BETWEEN 0 AND 10),
    stress_resilience INTEGER CHECK (stress_resilience BETWEEN 0 AND 10),
    spiritual_vitality INTEGER CHECK (spiritual_vitality BETWEEN 0 AND 10),
    overall_spiritual_health INTEGER CHECK (overall_spiritual_health BETWEEN 0 AND 10),
    character_growth_trajectory VARCHAR(10) CHECK (character_growth_trajectory IN ('declining', 'stable', 'growing', 'accelerating')),
    daily_reflection TEXT,
    gratitude_items TEXT[],
    struggle_items TEXT[],
    recorded_via VARCHAR(20) DEFAULT 'manual' CHECK (recorded_via IN ('manual', 'checkin', 'journal', 'decision_review')),
    source_decision_id UUID REFERENCES sfds_decision_events(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, metric_date, metric_period)
);

-- User Patterns
CREATE TABLE IF NOT EXISTS sfds_user_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES sfds_users(id) ON DELETE CASCADE,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    pattern_description TEXT,
    first_observed_at TIMESTAMP WITH TIME ZONE,
    last_observed_at TIMESTAMP WITH TIME ZONE,
    occurrence_count INTEGER DEFAULT 1,
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0.0 AND 1.0),
    related_decision_ids UUID[],
    pattern_data JSONB,
    is_active BOOLEAN DEFAULT true,
    is_addressed BOOLEAN DEFAULT false,
    addressed_how TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit Log
CREATE TABLE IF NOT EXISTS sfds_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by UUID REFERENCES sfds_users(id),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);
