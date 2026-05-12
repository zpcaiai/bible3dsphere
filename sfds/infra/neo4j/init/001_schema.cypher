// ============================================================
// SFDS v3 — Neo4j Graph Schema Bootstrap
// Run once on fresh instance to establish constraints + indexes
// ============================================================

// ── Constraints ───────────────────────────────────────────────
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
    FOR (u:UserStateNode) REQUIRE u.user_id IS UNIQUE;

CREATE CONSTRAINT emotion_type_unique IF NOT EXISTS
    FOR (e:EmotionNode) REQUIRE e.type IS UNIQUE;

CREATE CONSTRAINT motive_type_unique IF NOT EXISTS
    FOR (m:MotiveNode) REQUIRE m.type IS UNIQUE;

CREATE CONSTRAINT behavior_type_unique IF NOT EXISTS
    FOR (b:BehaviorNode) REQUIRE b.type IS UNIQUE;

CREATE CONSTRAINT outcome_type_unique IF NOT EXISTS
    FOR (o:OutcomeNode) REQUIRE o.type IS UNIQUE;

CREATE CONSTRAINT principle_id_unique IF NOT EXISTS
    FOR (p:PrincipleNode) REQUIRE p.id IS UNIQUE;

// ── Indexes ───────────────────────────────────────────────────
CREATE INDEX emotion_category IF NOT EXISTS FOR (e:EmotionNode) ON (e.category);
CREATE INDEX motive_category  IF NOT EXISTS FOR (m:MotiveNode)  ON (m.category);
CREATE INDEX behavior_pattern IF NOT EXISTS FOR (b:BehaviorNode) ON (b.pattern_id);

// ── Seed: Core Emotion Nodes ──────────────────────────────────
MERGE (e:EmotionNode {type: "fear"})       SET e.category = "fear",    e.label = "Fear";
MERGE (e:EmotionNode {type: "anxiety"})    SET e.category = "fear",    e.label = "Anxiety";
MERGE (e:EmotionNode {type: "shame"})      SET e.category = "shame",   e.label = "Shame";
MERGE (e:EmotionNode {type: "pride"})      SET e.category = "pride",   e.label = "Pride";
MERGE (e:EmotionNode {type: "peace"})      SET e.category = "clarity", e.label = "Peace";
MERGE (e:EmotionNode {type: "grief"})      SET e.category = "relational", e.label = "Grief";
MERGE (e:EmotionNode {type: "joy"})        SET e.category = "growth",  e.label = "Joy";

// ── Seed: Core Motive Nodes ───────────────────────────────────
MERGE (m:MotiveNode {type: "control_drive"})   SET m.category = "fear",   m.label = "Control Drive";
MERGE (m:MotiveNode {type: "self_protection"}) SET m.category = "pride",  m.label = "Self-Protection";
MERGE (m:MotiveNode {type: "avoidance"})       SET m.category = "shame",  m.label = "Avoidance";
MERGE (m:MotiveNode {type: "truth_seeking"})   SET m.category = "growth", m.label = "Truth Seeking";
MERGE (m:MotiveNode {type: "love_orientation"})SET m.category = "growth", m.label = "Love Orientation";

// ── Seed: Core Behavior Nodes ─────────────────────────────────
MERGE (b:BehaviorNode {type: "overwork"})        SET b.category = "fear";
MERGE (b:BehaviorNode {type: "perfectionism"})   SET b.category = "shame";
MERGE (b:BehaviorNode {type: "comparison"})      SET b.category = "pride";
MERGE (b:BehaviorNode {type: "reflection"})      SET b.category = "growth";
MERGE (b:BehaviorNode {type: "truth_facing"})    SET b.category = "growth";

// ── Seed: Core Principle Nodes ────────────────────────────────
MERGE (p:PrincipleNode {id: "humility_01"})
    SET p.label = "Humility opens the path to truth",
        p.category = "humility", p.action_type = "BREAKS";

MERGE (p:PrincipleNode {id: "rest_01"})
    SET p.label = "Rest is not weakness — it interrupts the burnout loop",
        p.category = "resilience", p.action_type = "BREAKS";

MERGE (p:PrincipleNode {id: "truth_01"})
    SET p.label = "Truth-facing reduces the power of shame",
        p.category = "truth", p.action_type = "BREAKS";
