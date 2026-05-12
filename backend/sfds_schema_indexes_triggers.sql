-- ============================================================================
-- SFDS Schema (Part 2/3) - Indexes, Triggers, Functions, Views
-- ============================================================================

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Decision events indexes
CREATE INDEX IF NOT EXISTS idx_decisions_user_id ON sfds_decision_events(user_id);
CREATE INDEX IF NOT EXISTS idx_decisions_user_created ON sfds_decision_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_category ON sfds_decision_events(category);
CREATE INDEX IF NOT EXISTS idx_decisions_status ON sfds_decision_events(processing_status);
CREATE INDEX IF NOT EXISTS idx_decisions_outcome ON sfds_decision_events(outcome_status);
CREATE INDEX IF NOT EXISTS idx_decisions_deadline ON sfds_decision_events(deadline_date) WHERE deadline_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_analyzed ON sfds_decision_events(analyzed_at) WHERE analyzed_at IS NOT NULL;

-- State snapshots indexes
CREATE INDEX IF NOT EXISTS idx_snapshots_decision ON sfds_state_snapshots(decision_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_stress ON sfds_state_snapshots(stress_level);
CREATE INDEX IF NOT EXISTS idx_snapshots_anxiety ON sfds_state_snapshots(anxiety_level);
CREATE INDEX IF NOT EXISTS idx_snapshots_dryness ON sfds_state_snapshots(spiritual_dryness_level);
CREATE INDEX IF NOT EXISTS idx_snapshots_readiness ON sfds_state_snapshots(decision_readiness_score);

-- Emotion logs indexes
CREATE INDEX IF NOT EXISTS idx_emotions_decision ON sfds_emotion_logs(decision_id);
CREATE INDEX IF NOT EXISTS idx_emotions_type ON sfds_emotion_logs(emotion_type);
CREATE INDEX IF NOT EXISTS idx_emotions_intensity ON sfds_emotion_logs(intensity);
CREATE INDEX IF NOT EXISTS idx_emotions_recorded ON sfds_emotion_logs(recorded_at);
CREATE INDEX IF NOT EXISTS idx_emotions_decision_type ON sfds_emotion_logs(decision_id, emotion_type);
CREATE INDEX IF NOT EXISTS idx_emotions_high_intensity ON sfds_emotion_logs(intensity) WHERE intensity >= 7;

-- Motive analysis indexes
CREATE INDEX IF NOT EXISTS idx_motives_decision ON sfds_motive_analyses(decision_id);
CREATE INDEX IF NOT EXISTS idx_motives_primary ON sfds_motive_analyses(primary_motive);
CREATE INDEX IF NOT EXISTS idx_motives_fear ON sfds_motive_analyses(fear_driven_score);
CREATE INDEX IF NOT EXISTS idx_motives_love ON sfds_motive_analyses(love_driven_score);
CREATE INDEX IF NOT EXISTS idx_motives_confidence ON sfds_motive_analyses(confidence_score);

-- Discernment results indexes
CREATE INDEX IF NOT EXISTS idx_discernment_decision ON sfds_discernment_results(decision_id);
CREATE INDEX IF NOT EXISTS idx_discernment_source ON sfds_discernment_results(primary_source);
CREATE INDEX IF NOT EXISTS idx_discernment_confidence ON sfds_discernment_results(source_confidence);
CREATE INDEX IF NOT EXISTS idx_discernment_warnings ON sfds_discernment_results(has_spiritual_warning, has_psychological_warning);

-- Guidance outputs indexes
CREATE INDEX IF NOT EXISTS idx_guidance_decision ON sfds_guidance_outputs(decision_id);
CREATE INDEX IF NOT EXISTS idx_guidance_priority ON sfds_guidance_outputs(priority_level);
CREATE INDEX IF NOT EXISTS idx_guidance_urgent ON sfds_guidance_outputs(priority_level) WHERE priority_level = 'urgent';

-- Spiritual principles indexes
CREATE INDEX IF NOT EXISTS idx_principles_category ON sfds_spiritual_principles(category);
CREATE INDEX IF NOT EXISTS idx_principles_subcategory ON sfds_spiritual_principles(subcategory);
CREATE INDEX IF NOT EXISTS idx_principles_active ON sfds_spiritual_principles(is_active);
CREATE INDEX IF NOT EXISTS idx_principles_text_search ON sfds_spiritual_principles USING GIN(search_vectors);
CREATE INDEX IF NOT EXISTS idx_principles_keywords ON sfds_spiritual_principles USING GIN(search_keywords);
CREATE INDEX IF NOT EXISTS idx_principles_embedding ON sfds_spiritual_principles USING IVFFLAT (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_principles_contexts ON sfds_spiritual_principles USING GIN(applicable_contexts);
CREATE INDEX IF NOT EXISTS idx_principles_emotions ON sfds_spiritual_principles USING GIN(applicable_emotions);

-- Decision principles junction indexes
CREATE INDEX IF NOT EXISTS idx_decision_principles_decision ON sfds_decision_principles(decision_id);
CREATE INDEX IF NOT EXISTS idx_decision_principles_principle ON sfds_decision_principles(principle_id);
CREATE INDEX IF NOT EXISTS idx_decision_principles_relevance ON sfds_decision_principles(relevance_score);

-- Reviews indexes
CREATE INDEX IF NOT EXISTS idx_reviews_decision ON sfds_decision_reviews(decision_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON sfds_decision_reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON sfds_decision_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_outcome ON sfds_decision_reviews(outcome_category);
CREATE INDEX IF NOT EXISTS idx_reviews_peace ON sfds_decision_reviews(peace_level);

-- Spiritual metrics indexes
CREATE INDEX IF NOT EXISTS idx_metrics_user ON sfds_spiritual_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON sfds_spiritual_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_metrics_user_date ON sfds_spiritual_metrics(user_id, metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_period ON sfds_spiritual_metrics(user_id, metric_period, metric_date DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_health ON sfds_spiritual_metrics(overall_spiritual_health);

-- User patterns indexes
CREATE INDEX IF NOT EXISTS idx_patterns_user ON sfds_user_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON sfds_user_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_active ON sfds_user_patterns(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON sfds_user_patterns(confidence_score);

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON sfds_users(email);
CREATE INDEX IF NOT EXISTS idx_users_created ON sfds_users(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_users_active ON sfds_users(deleted_at) WHERE deleted_at IS NULL;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Update user decision count
CREATE OR REPLACE FUNCTION update_user_decision_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sfds_users 
    SET discernment_history_count = discernment_history_count + 1,
        updated_at = NOW()
    WHERE id = NEW.user_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Update principle reference count
CREATE OR REPLACE FUNCTION update_principle_reference_count()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE sfds_spiritual_principles 
    SET reference_count = reference_count + 1,
        last_referenced_at = NOW()
    WHERE id = NEW.principle_id;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Update principle search vector
CREATE OR REPLACE FUNCTION update_principle_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vectors := 
        setweight(to_tsvector('simple', COALESCE(NEW.principle_text, '')), 'A') ||
        setweight(to_tsvector('simple', COALESCE(NEW.principle_summary, '')), 'B') ||
        setweight(to_tsvector('simple', COALESCE(NEW.scripture_reference, '')), 'C') ||
        setweight(to_tsvector('simple', COALESCE(array_to_string(NEW.search_keywords, ' '), '')), 'D');
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Calculate decision readiness score
CREATE OR REPLACE FUNCTION calculate_decision_readiness(
    p_stress INTEGER,
    p_anxiety INTEGER,
    p_fatigue INTEGER,
    p_dryness INTEGER,
    p_stability INTEGER
) RETURNS INTEGER AS $$
DECLARE
    v_score INTEGER;
BEGIN
    -- Higher stability = higher readiness
    -- Lower stress, anxiety, fatigue, dryness = higher readiness
    v_score := 10 - (p_stress + p_anxiety + p_fatigue + p_dryness) / 4;
    v_score := (v_score + p_stability) / 2;
    RETURN GREATEST(0, LEAST(10, v_score));
END;
$$ language 'plpgsql';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Apply update triggers
CREATE TRIGGER update_sfds_users_updated_at BEFORE UPDATE ON sfds_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sfds_decision_events_updated_at BEFORE UPDATE ON sfds_decision_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sfds_spiritual_principles_updated_at BEFORE UPDATE ON sfds_spiritual_principles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sfds_decision_reviews_updated_at BEFORE UPDATE ON sfds_decision_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sfds_user_patterns_updated_at BEFORE UPDATE ON sfds_user_patterns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Decision count increment
CREATE TRIGGER increment_user_decision_count 
    AFTER INSERT ON sfds_decision_events
    FOR EACH ROW EXECUTE FUNCTION update_user_decision_count();

-- Principle reference count
CREATE TRIGGER increment_principle_reference_count 
    AFTER INSERT ON sfds_decision_principles
    FOR EACH ROW EXECUTE FUNCTION update_principle_reference_count();

-- Search vector update
CREATE TRIGGER update_principle_search_vector_trigger 
    BEFORE INSERT OR UPDATE ON sfds_spiritual_principles
    FOR EACH ROW EXECUTE FUNCTION update_principle_search_vector();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- User decision summary view
CREATE OR REPLACE VIEW sfds_user_decision_summary AS
SELECT 
    u.id AS user_id,
    u.email,
    u.nickname,
    COUNT(DISTINCT d.id) AS total_decisions,
    COUNT(DISTINCT CASE WHEN d.processing_status = 'guided' THEN d.id END) AS guided_decisions,
    COUNT(DISTINCT CASE WHEN d.processing_status = 'reviewed' THEN d.id END) AS reviewed_decisions,
    COUNT(DISTINCT CASE WHEN d.outcome_status = 'implemented' THEN d.id END) AS implemented_decisions,
    COUNT(DISTINCT CASE WHEN d.category = 'temptation' THEN d.id END) AS temptation_decisions,
    COUNT(DISTINCT CASE WHEN d.category = 'relationship' THEN d.id END) AS relationship_decisions,
    COUNT(DISTINCT CASE WHEN d.category = 'career' THEN d.id END) AS career_decisions,
    AVG(m.fear_driven_score) FILTER (WHERE m.fear_driven_score IS NOT NULL) AS avg_fear_score,
    AVG(m.love_driven_score) FILTER (WHERE m.love_driven_score IS NOT NULL) AS avg_love_score,
    AVG(m.pride_driven_score) FILTER (WHERE m.pride_driven_score IS NOT NULL) AS avg_pride_score,
    MAX(d.created_at) AS last_decision_at,
    MAX(r.review_date) AS last_review_date
FROM sfds_users u
LEFT JOIN sfds_decision_events d ON u.id = d.user_id AND d.deleted_at IS NULL
LEFT JOIN sfds_motive_analyses m ON d.id = m.decision_id
LEFT JOIN sfds_decision_reviews r ON d.id = r.decision_id
WHERE u.deleted_at IS NULL
GROUP BY u.id, u.email, u.nickname;

-- High-risk decisions view
CREATE OR REPLACE VIEW sfds_high_risk_decisions AS
SELECT 
    d.id AS decision_id,
    d.title,
    d.user_id,
    u.email,
    u.nickname,
    s.stress_level,
    s.anxiety_level,
    s.spiritual_dryness_level,
    m.fear_driven_score,
    m.pride_driven_score,
    dr.primary_source,
    dr.has_spiritual_warning,
    dr.has_psychological_warning,
    g.priority_level,
    g.risk_severity,
    d.created_at,
    d.category
FROM sfds_decision_events d
JOIN sfds_users u ON d.user_id = u.id
LEFT JOIN sfds_state_snapshots s ON d.id = s.decision_id
LEFT JOIN sfds_motive_analyses m ON d.id = m.decision_id
LEFT JOIN sfds_discernment_results dr ON d.id = dr.decision_id
LEFT JOIN sfds_guidance_outputs g ON d.id = g.decision_id
WHERE d.processing_status IN ('guided', 'decided')
    AND d.outcome_status = 'pending'
    AND (
        s.stress_level >= 8 
        OR s.anxiety_level >= 8
        OR s.spiritual_dryness_level >= 7
        OR m.fear_driven_score >= 0.7
        OR m.pride_driven_score >= 0.7
        OR dr.has_spiritual_warning = true
        OR dr.has_psychological_warning = true
        OR g.priority_level = 'urgent'
        OR g.risk_severity = 'critical'
    )
ORDER BY d.created_at DESC;

-- Recent emotion patterns view
CREATE OR REPLACE VIEW sfds_recent_emotion_patterns AS
SELECT 
    el.emotion_type,
    COUNT(*) AS occurrence_count,
    AVG(el.intensity) AS avg_intensity,
    MAX(el.recorded_at) AS last_occurrence,
    COUNT(DISTINCT el.decision_id) AS affected_decisions,
    STRING_AGG(DISTINCT d.category, ', ' ORDER BY d.category) AS affected_categories
FROM sfds_emotion_logs el
JOIN sfds_decision_events d ON el.decision_id = d.id
WHERE el.recorded_at > NOW() - INTERVAL '30 days'
GROUP BY el.emotion_type
ORDER BY occurrence_count DESC;

-- Spiritual health trends view
CREATE OR REPLACE VIEW sfds_spiritual_health_trends AS
SELECT 
    m.user_id,
    u.email,
    u.nickname,
    DATE_TRUNC('week', m.metric_date) AS week,
    AVG(m.overall_spiritual_health) AS avg_health_score,
    AVG(m.prayer_consistency) AS avg_prayer,
    AVG(m.scripture_engagement) AS avg_scripture,
    AVG(m.community_connection) AS avg_community,
    AVG(m.emotional_regulation) AS avg_emotional_regulation,
    AVG(m.spiritual_vitality) AS avg_vitality,
    COUNT(*) AS entry_count
FROM sfds_spiritual_metrics m
JOIN sfds_users u ON m.user_id = u.id
WHERE m.metric_date > NOW() - INTERVAL '90 days'
GROUP BY m.user_id, u.email, u.nickname, DATE_TRUNC('week', m.metric_date)
ORDER BY m.user_id, week DESC;

-- Motive distribution view
CREATE OR REPLACE VIEW sfds_motive_distribution AS
SELECT 
    primary_motive,
    COUNT(*) AS decision_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
    AVG(fear_driven_score) AS avg_fear,
    AVG(pride_driven_score) AS avg_pride,
    AVG(love_driven_score) AS avg_love,
    AVG(desire_driven_score) AS avg_desire
FROM sfds_motive_analyses
GROUP BY primary_motive
ORDER BY decision_count DESC;

-- Source distribution view
CREATE OR REPLACE VIEW sfds_source_distribution AS
SELECT 
    primary_source,
    COUNT(*) AS decision_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS percentage,
    AVG(source_confidence) AS avg_confidence,
    AVG(biblical_alignment_score) AS avg_alignment,
    AVG(long_term_fruit_prediction) AS avg_fruit_prediction
FROM sfds_discernment_results
GROUP BY primary_source
ORDER BY decision_count DESC;

-- Principle effectiveness view
CREATE OR REPLACE VIEW sfds_principle_effectiveness AS
SELECT 
    p.id AS principle_id,
    p.principle_text,
    p.category,
    p.reference_count,
    COUNT(DISTINCT dp.decision_id) AS applied_to_decisions,
    AVG(dp.relevance_score) AS avg_relevance,
    COUNT(DISTINCT CASE WHEN dr.outcome_category = 'positive' THEN dr.id END) AS positive_outcomes,
    COUNT(DISTINCT CASE WHEN dr.outcome_category = 'negative' THEN dr.id END) AS negative_outcomes,
    COUNT(DISTINCT dr.id) FILTER (WHERE dr.id IS NOT NULL) AS total_reviewed
FROM sfds_spiritual_principles p
LEFT JOIN sfds_decision_principles dp ON p.id = dp.principle_id
LEFT JOIN sfds_decision_reviews dr ON dp.decision_id = dr.decision_id
WHERE p.is_active = true
GROUP BY p.id, p.principle_text, p.category, p.reference_count
ORDER BY p.reference_count DESC;
