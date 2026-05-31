-- Migration 0017: 耶路撒冷地标（landmark 实体，带 valid_time，随年份出现/消失）
-- 基训泉/大卫王宫/圣殿山/宽墙/西罗亚池。幂等：slug=gihon-spring 已存在则跳过。
-- Depends on 0007/0012(slug列)/0011(confidence列)。

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM geo_entities WHERE slug = 'gihon-spring') THEN
    -- 基训泉
    INSERT INTO geo_entities(entity_type, slug) VALUES('landmark', 'gihon-spring') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '基训泉', 'Gihon Spring', '', int4range(-2000, 100));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, confidence) VALUES (v_id, int4range(-2000, 100), ST_SetSRID(ST_MakePoint(35.2365, 31.7735), 4326), 'approximate');
    -- 大卫王宫
    INSERT INTO geo_entities(entity_type, slug) VALUES('landmark', 'davids-palace') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '大卫王宫', 'David''s Palace', '', int4range(-1004, -586));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, confidence) VALUES (v_id, int4range(-1004, -586), ST_SetSRID(ST_MakePoint(35.2356, 31.7745), 4326), 'approximate');
    -- 圣殿山
    INSERT INTO geo_entities(entity_type, slug) VALUES('landmark', 'temple-mount') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '圣殿山', 'Temple Mount', '', int4range(-960, 100));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, confidence) VALUES (v_id, int4range(-960, 100), ST_SetSRID(ST_MakePoint(35.2354, 31.778), 4326), 'approximate');
    -- 宽墙
    INSERT INTO geo_entities(entity_type, slug) VALUES('landmark', 'broad-wall') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '宽墙', 'Broad Wall', '', int4range(-700, -586));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, confidence) VALUES (v_id, int4range(-700, -586), ST_SetSRID(ST_MakePoint(35.23, 31.7765), 4326), 'approximate');
    -- 西罗亚池
    INSERT INTO geo_entities(entity_type, slug) VALUES('landmark', 'pool-of-siloam') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西罗亚池', 'Pool of Siloam', '', int4range(-700, 100));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point, confidence) VALUES (v_id, int4range(-700, 100), ST_SetSRID(ST_MakePoint(35.2354, 31.7705), 4326), 'approximate');
  END IF;
END $$;
