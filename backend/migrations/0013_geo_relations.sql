-- Migration 0013: 拓扑图谱 geo_relations —— 实体间的时空关系图
-- 支撑"时空多对多"：城市隶属某支派、支派彼此相邻、王国包含诸支派、某城为某国首都等，
-- 且关系本身带 valid_time（同一城在不同时代可隶属不同政治实体）。
-- Depends on 0007 (geo_entities)。

CREATE TABLE IF NOT EXISTS geo_relations (
    relation_id   SERIAL PRIMARY KEY,
    src_entity_id INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    dst_entity_id INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    relation_type VARCHAR(24) NOT NULL,   -- 'within','contains','adjacent','capital_of','borders'
    valid_time    INT4RANGE,
    CONSTRAINT chk_rel_distinct CHECK (src_entity_id <> dst_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_geo_relations_src  ON geo_relations (src_entity_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_geo_relations_dst  ON geo_relations (dst_entity_id, relation_type);
CREATE INDEX IF NOT EXISTS idx_geo_relations_time ON geo_relations USING gist (valid_time);
