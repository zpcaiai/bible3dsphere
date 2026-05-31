-- Migration 0007: Biblical geography — temporal/spatial model (PostGIS)
-- Supports "时空多对多" relationships: one coordinate carries different names across
-- eras (Salem→Jebus→City of David→Jerusalem), and political boundaries evolve over time.
-- Uses PostGIS geometry + int4range temporal bounds (years; BC negative, AD positive)
-- with GiST spatio-temporal indexes for fast era+region queries.

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Geo-Entities — abstract geographic existence, era-independent
CREATE TABLE IF NOT EXISTS geo_entities (
    entity_id    SERIAL PRIMARY KEY,
    entity_type  VARCHAR(32) NOT NULL,   -- 'city','mountain','river','region','boundary','camp'
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Entity Geometry Snapshots — spatial form valid within a time interval
CREATE TABLE IF NOT EXISTS entity_geometries (
    geometry_id  SERIAL PRIMARY KEY,
    entity_id    INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    valid_time   INT4RANGE NOT NULL,                 -- e.g. '[-1000,-586)'
    geom_point   GEOMETRY(Point, 4326),              -- macro pin
    geom_polygon GEOMETRY(Polygon, 4326),            -- walls / territory boundary
    CONSTRAINT check_geometry_exists
        CHECK (geom_point IS NOT NULL OR geom_polygon IS NOT NULL)
);

-- 3. Entity Names Timeline — "一地多名" across eras
CREATE TABLE IF NOT EXISTS entity_names (
    name_id      SERIAL PRIMARY KEY,
    entity_id    INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    name_zh      VARCHAR(64) NOT NULL,               -- 中文圣经译名（耶布斯）
    name_en      VARCHAR(64),                        -- 英文译名（Jebus）
    name_hebrew  VARCHAR(64),                        -- 希伯来原文
    valid_time   INT4RANGE NOT NULL                  -- 该名称生效时间段
);

-- 4. Scripture↔Geo Mapping — 读经时地图联动的核心关联
CREATE TABLE IF NOT EXISTS scripture_geo_mappings (
    mapping_id        SERIAL PRIMARY KEY,
    book_code         VARCHAR(8) NOT NULL,           -- 'GEN','NUM','ACT' ...
    chapter           INT NOT NULL,
    verse_start       INT NOT NULL,
    verse_end         INT NOT NULL,
    entity_id         INT REFERENCES geo_entities(entity_id) ON DELETE CASCADE,
    association_type  VARCHAR(32)                    -- 'mention','battle_site','camp'
);

-- 5. Historical Routes — 出埃及路线 / 保罗行踪 等动态路径
CREATE TABLE IF NOT EXISTS historical_routes (
    route_id    SERIAL PRIMARY KEY,
    route_name  VARCHAR(64) NOT NULL UNIQUE,         -- 'Exodus_Traditional','Paul_Journey_1'
    valid_time  INT4RANGE,
    geom_line   GEOMETRY(LineString, 4326)
);

-- ── Spatio-temporal indexes (GiST) ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_entity_geom_spatiotemporal
    ON entity_geometries USING gist (valid_time, geom_point);
CREATE INDEX IF NOT EXISTS idx_entity_poly_spatiotemporal
    ON entity_geometries USING gist (valid_time, geom_polygon);
CREATE INDEX IF NOT EXISTS idx_entity_names_time
    ON entity_names USING gist (valid_time);
CREATE INDEX IF NOT EXISTS idx_entity_names_entity
    ON entity_names (entity_id);
CREATE INDEX IF NOT EXISTS idx_scripture_lookup
    ON scripture_geo_mappings (book_code, chapter, verse_start);
CREATE INDEX IF NOT EXISTS idx_routes_geom
    ON historical_routes USING gist (geom_line);
