-- Migration 0015: 分裂王国 —— 北国以色列 + 南国犹大（region + polygon + 关系）
-- 北国 valid_time 止于公元前722(亚述灭国)，南国延续至前586；演示疆域随时代消失。
-- 幂等：slug=judah-south 已存在则跳过。Depends on 0007/0012(slug)/0013(geo_relations)/0014。

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM geo_entities WHERE slug = 'judah-south') THEN
    -- 北国以色列
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'israel-north') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '北国以色列', 'Kingdom of Israel', '', int4range(-930, -722));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-930, -722), ST_SetSRID(ST_GeomFromText('POLYGON((34.9 31.97, 36.1 31.97, 36.1 33.35, 34.9 33.35, 34.9 31.97))'), 4326), 'approximate');
    -- 南国犹大
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'judah-south') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '南国犹大', 'Kingdom of Judah', '', int4range(-930, -586));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-930, -586), ST_SetSRID(ST_GeomFromText('POLYGON((34.6 30.8, 35.55 30.8, 35.55 31.97, 34.6 31.97, 34.6 30.8))'), 4326), 'approximate');
    -- 拓扑关系
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'capital_of', int4range(-930, -586) FROM geo_entities a, geo_entities b WHERE a.slug='jerusalem' AND b.slug='judah-south';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-930, -722) FROM geo_entities a, geo_entities b WHERE a.slug='israel-north' AND b.slug='judah-south';
  END IF;
END $$;
