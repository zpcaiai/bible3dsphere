-- Migration 0012: 耶路撒冷时代演变 —— 时空切片演示（一地多名 + 城墙polygon随时代变）
-- 为 geo_entities 增加 slug 稳定键；按时代写入多条 entity_names 与 entity_geometries(含polygon)。
-- 幂等：slug=jerusalem 已存在则跳过。Depends on 0007/0011(confidence列)。

ALTER TABLE geo_entities ADD COLUMN IF NOT EXISTS slug VARCHAR(48);
CREATE INDEX IF NOT EXISTS idx_geo_entities_slug ON geo_entities (slug);

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM geo_entities WHERE slug = 'jerusalem') THEN
    INSERT INTO geo_entities(entity_type, slug) VALUES('city', 'jerusalem') RETURNING entity_id INTO v_id;
    -- 撒冷（麦基洗德时期）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '撒冷', 'Salem', '', int4range(-2000, -1400));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-2000, -1400), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.2355 31.7705, 35.2378 31.7705, 35.238 31.7765, 35.2356 31.7765, 35.2355 31.7705))'), 4326), 'approximate');
    -- 耶布斯（士师时期）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶布斯', 'Jebus', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.2355 31.7705, 35.2378 31.7705, 35.238 31.7765, 35.2356 31.7765, 35.2355 31.7705))'), 4326), 'approximate');
    -- 大卫城（联合王国）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '大卫城', 'City of David', '', int4range(-1004, -960));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-1004, -960), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.2352 31.77, 35.2382 31.77, 35.2384 31.7768, 35.2352 31.7768, 35.2352 31.77))'), 4326), 'approximate');
    -- 所罗门的耶路撒冷
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶路撒冷（所罗门）', 'Jerusalem', '', int4range(-960, -700));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-960, -700), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.2352 31.77, 35.2386 31.77, 35.2388 31.7796, 35.2352 31.7796, 35.2352 31.77))'), 4326), 'approximate');
    -- 希西家扩建（犹大王国）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶路撒冷（希西家）', 'Jerusalem', '', int4range(-700, -586));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-700, -586), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.227 31.77, 35.239 31.77, 35.2392 31.78, 35.2268 31.78, 35.227 31.77))'), 4326), 'approximate');
    -- 归回时期（尼希米重建）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶路撒冷（尼希米）', 'Jerusalem', '', int4range(-586, -20));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-586, -20), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.232 31.77, 35.239 31.77, 35.2392 31.78, 35.2318 31.78, 35.232 31.77))'), 4326), 'approximate');
    -- 新约时期（希律扩建）
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶路撒冷（新约）', 'Jerusalem', '', int4range(-20, 100));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, geom_polygon, confidence) VALUES (v_id, int4range(-20, 100), ST_SetSRID(ST_MakePoint(35.2345, 31.7767), 4326), ST_SetSRID(ST_GeomFromText('POLYGON((35.2255 31.7695, 35.2402 31.7695, 35.2404 31.7822, 35.225 31.7822, 35.2255 31.7695))'), 4326), 'approximate');
  END IF;
END $$;
