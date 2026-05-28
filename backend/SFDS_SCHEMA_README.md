# SFDS PostgreSQL Schema Documentation

## Overview

This directory contains the complete PostgreSQL schema for the **Spiritual Formation & Discernment System (SFDS)** - a full-stack system for Christian decision support and spiritual growth tracking.

## File Structure

```
backend/
├── sfds_schema_core.sql              # Core tables and relationships
├── sfds_schema_indexes_triggers.sql  # Indexes, triggers, functions, views
├── sfds_schema_seed_data.sql         # 30 principles + example dataset
├── sfds_migration.sh                 # Migration/Setup script
└── SFDS_SCHEMA_README.md           # This documentation
```

## Quick Start

```bash
# Full setup (creates tables, indexes, seed data)
./sfds_migration.sh setup

# Or step by step:
./sfds_migration.sh migrate   # Schema only
./sfds_migration.sh seed      # Seed data only
./sfds_migration.sh verify    # Check installation
```

## Schema Architecture

### 1. Core Domain Tables

#### `sfds_users`
User profile with spiritual maturity tracking and personality insights.

```sql
- UUID primary key
- Spiritual maturity score (0-10)
- Personality/decision style profiling
- Soft delete support
```

#### `sfds_decision_events`
Central decision tracking with full audit trail.

```sql
- Decision metadata (title, category, urgency, importance)
- Outcome tracking (status, final decision, review date)
- JSONB storage for analysis results (motive, discernment, guidance)
- Full timestamp audit trail
```

#### `sfds_state_snapshots`
Psychological/spiritual state at decision time.

```sql
- 5 core dimensions: stress, anxiety, fatigue, spiritual dryness, emotional stability
- Composite scores: wellbeing, decision readiness
- Additional context: sleep, health, relationships, financial pressure
```

#### `sfds_emotion_logs`
Detailed emotion tracking linked to decisions.

```sql
- 30+ emotion types (joy, fear, anger, shame, etc.)
- Intensity tracking (0-10)
- Trigger categorization (internal, external, relational, etc.)
- Duration tracking
```

### 2. Analysis Result Tables

#### `sfds_motive_analyses`
Normalized motive analysis with scores.

```sql
- 6 motive dimensions: fear, pride, love, desire, duty, ambition
- Primary/secondary motive classification
- Confidence scoring
- NLP features (keywords, sentiment)
```

#### `sfds_discernment_results`
Source discernment with probabilistic interpretation.

```sql
- Source classification (Holy Spirit, fear, pride, trauma, etc.)
- Biblical alignment score
- Long-term fruit prediction (-1 to 1)
- Warning flags (spiritual, psychological, practical)
```

#### `sfds_guidance_outputs`
Structured guidance with risk assessment.

```sql
- Structured advice (primary output)
- Risk levels and alternative interpretations
- Actionable steps (immediate, short-term, long-term)
- Spiritual resources (scriptures, practices, readings)
- Follow-up questions
```

### 3. Spiritual Principles (pgvector)

#### `sfds_spiritual_principles`
Vector-embeddable spiritual principles with full-text search.

```sql
- 1536-dimension vector embeddings (OpenAI compatible)
- Full-text search vectors (tsvector)
- Applicability tags (contexts, emotions)
- Usage tracking
- 20 categories (discernment, love, humility, courage, etc.)
```

#### `sfds_decision_principles`
Many-to-many junction with relevance scoring.

### 4. Time-Series Tracking

#### `sfds_spiritual_metrics`
Daily/weekly/monthly spiritual health tracking.

```sql
- Spiritual disciplines: prayer, scripture, meditation, fasting
- Community & service metrics
- Character formation scores (humility, patience, self-control, etc.)
- Emotional/spiritual health
- Growth trajectory tracking
```

### 5. Pattern Recognition

#### `sfds_user_patterns`
Detected patterns for long-term insights.

```sql
- Pattern types: decision bias, emotional cycle, spiritual season
- Confidence scoring
- Related decision linking
- Addressed/unaddressed tracking
```

## 30 Spiritual Principles (Seed Data)

| # | Category | Principle | Scripture |
|---|----------|-----------|-----------|
| 1 | Discernment | 凡事察验，善美的要持守 | 帖前 5:21 |
| 2 | Discernment | 你要保守你心，胜过保守一切 | 箴 4:23 |
| 3 | Discernment | 不要效法这个世界 | 罗 12:2 |
| 4 | Discernment | 凭果子认出他们来 | 太 7:20 |
| 5 | Discernment | 有两三个人奉我的名聚会 | 太 18:20 |
| 6 | Truth | 真理必叫你们得以自由 | 约 8:32 |
| 7 | Truth | 是，就说是；不是，就说不是 | 太 5:37 |
| 8 | Truth | 你们要弃绝谎言 | 弗 4:25 |
| 9 | Truth | 不可偷盗，不可欺骗 | 利 19:11 |
| 10 | Truth | 惟独我的仆人迦勒 | 民 14:24 |
| 11 | Love | 我若能说万人的方言 | 林前 13:1-3 |
| 12 | Love | 爱人如己 | 太 22:39 |
| 13 | Love | 不求自己的益处 | 腓 2:4 |
| 14 | Love | 总要彼此包容 | 西 3:13 |
| 15 | Love | 你们愿意人怎样待你们 | 路 6:31 |
| 16 | Humility | 凡自高的，必降为卑 | 太 23:12 |
| 17 | Humility | 看别人比自己强 | 腓 2:3 |
| 18 | Humility | 虚心的人有福了 | 太 5:3 |
| 19 | Humility | 以谦卑束腰 | 彼前 5:5 |
| 20 | Humility | 神赐恩给谦卑的人 | 雅 4:6 |
| 21 | Faith | 不要恐惧，因为我与你同在 | 赛 41:10 |
| 22 | Peace | 我留下平安给你们 | 约 14:27 |
| 23 | Peace | 应当一无挂虑 | 腓 4:6 |
| 24 | Peace | 神所赐出人意外的平安 | 腓 4:7 |
| 25 | Faith | 你们这小群，不要惧怕 | 路 12:32 |
| 26 | Patience | 患难生忍耐 | 罗 5:3-4 |
| 27 | Resistance | 你们所受的试探 | 林前 10:13 |
| 28 | Resistance | 务要谨守，警醒 | 彼前 5:8 |
| 29 | Resistance | 务要抵挡魔鬼 | 雅 4:7 |
| 30 | Character | 不可为恶所胜 | 罗 12:21 |

## Indexes & Performance

### Key Indexes

```sql
-- Decision queries
CREATE INDEX idx_decisions_user_created ON sfds_decision_events(user_id, created_at DESC);
CREATE INDEX idx_decisions_status ON sfds_decision_events(processing_status);

-- Emotion analysis
CREATE INDEX idx_emotions_decision_type ON sfds_emotion_logs(decision_id, emotion_type);
CREATE INDEX idx_emotions_high_intensity ON sfds_emotion_logs(intensity) WHERE intensity >= 7;

-- pgvector semantic search
CREATE INDEX idx_principles_embedding ON sfds_spiritual_principles 
    USING IVFFLAT (embedding vector_cosine_ops) WITH (lists = 100);

-- Full-text search
CREATE INDEX idx_principles_text_search ON sfds_spiritual_principles USING GIN(search_vectors);

-- Time-series queries
CREATE INDEX idx_metrics_user_date ON sfds_spiritual_metrics(user_id, metric_date DESC);
```

## Views for Analytics

### `sfds_user_decision_summary`
User-level decision statistics and motive averages.

### `sfds_high_risk_decisions`
Identifies decisions with high stress/anxiety/fear requiring attention.

### `sfds_recent_emotion_patterns`
Emotion occurrence trends over last 30 days.

### `sfds_spiritual_health_trends`
Weekly spiritual health trends by user.

### `sfds_motive_distribution`
Aggregate motive classification distribution.

### `sfds_source_distribution`
Discernment source classification distribution.

### `sfds_principle_effectiveness`
Principle application and outcome correlation.

## Triggers & Automation

### Auto-updating Timestamps
```sql
-- All tables with updated_at auto-update on modification
CREATE TRIGGER update_sfds_decision_events_updated_at
    BEFORE UPDATE ON sfds_decision_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### User Statistics
```sql
-- Auto-increment user's decision count
CREATE TRIGGER increment_user_decision_count
    AFTER INSERT ON sfds_decision_events
    FOR EACH ROW EXECUTE FUNCTION update_user_decision_count();
```

### Search Vector Updates
```sql
-- Auto-update principle search vectors
CREATE TRIGGER update_principle_search_vector_trigger
    BEFORE INSERT OR UPDATE ON sfds_spiritual_principles
    FOR EACH ROW EXECUTE FUNCTION update_principle_search_vector();
```

## Example Usage

### Create New Decision
```sql
WITH new_decision AS (
    INSERT INTO sfds_decision_events (user_id, title, description, category, urgency_level, importance_level)
    VALUES ('uuid-here', '工作选择', '描述...', 'career', 4, 5)
    RETURNING id
)
INSERT INTO sfds_state_snapshots (decision_id, stress_level, anxiety_level, fatigue_level, spiritual_dryness_level, emotional_stability_level)
SELECT id, 7, 6, 5, 4, 6 FROM new_decision;
```

### Semantic Principle Search
```sql
-- Find principles similar to query embedding
SELECT principle_text, scripture_reference,
       1 - (embedding <=> query_embedding) AS similarity
FROM sfds_spiritual_principles
WHERE 1 - (embedding <=> query_embedding) > 0.8
ORDER BY embedding <=> query_embedding
LIMIT 5;
```

### Full-Text Search
```sql
-- Search principles by keyword
SELECT principle_text, scripture_reference
FROM sfds_spiritual_principles
WHERE search_vectors @@ plainto_tsquery('simple', '饶恕')
ORDER BY ts_rank(search_vectors, plainto_tsquery('simple', '饶恕')) DESC;
```

### User Decision History
```sql
SELECT * FROM sfds_user_decision_summary
WHERE user_id = 'uuid-here';
```

### High-Risk Decisions Alert
```sql
SELECT * FROM sfds_high_risk_decisions
WHERE user_id = 'uuid-here'
ORDER BY created_at DESC;
```

## Requirements

- PostgreSQL 14+
- pgvector extension
- uuid-ossp extension
- pg_trgm extension (for text search)

## Migration Commands

```bash
# Full setup
./sfds_migration.sh setup

# Verify installation
./sfds_migration.sh verify

# Reset (WARNING: Deletes data)
./sfds_migration.sh reset
```

## Database Schema Diagram

```
sfds_users
    │
    ├──► sfds_decision_events
    │       ├──► sfds_state_snapshots
    │       ├──► sfds_emotion_logs
    │       ├──► sfds_motive_analyses
    │       ├──► sfds_discernment_results
    │       ├──► sfds_guidance_outputs
    │       ├──► sfds_decision_reviews
    │       └──► sfds_decision_principles ◄──────┐
    │                                             │
    ├──► sfds_spiritual_metrics                   │
    │                                             │
    ├──► sfds_user_patterns                       │
    │                                             │
    └──► sfds_spiritual_principles ◄──────────────┘
```

## API Integration

The schema supports the FastAPI backend in `decision_support.py` with:

- Async PostgreSQL via asyncpg
- Pydantic models mapping to tables
- Automatic JSONB serialization for complex types
- Vector search integration

## License

Part of Bible Emotion Sphere project.
