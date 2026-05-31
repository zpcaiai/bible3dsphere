-- Migration 0014: 政治疆域演变 —— 十二支派分地 + 联合王国（region 实体 + polygon + 拓扑关系）
-- 演示同一土地不同时代归属剧烈演变。幂等：slug=united-kingdom 已存在则跳过。
-- Depends on 0007/0012(slug列)/0013(geo_relations)。

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM geo_entities WHERE slug = 'united-kingdom') THEN
    -- 支派 犹大
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-judah') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '犹大', 'Judah', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((34.85 31, 35.4 31, 35.4 31.65, 34.85 31.65, 34.85 31))'), 4326), 'approximate');
    -- 支派 西缅
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-simeon') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西缅', 'Simeon', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((34.55 30.95, 35 30.95, 35 31.3, 34.55 31.3, 34.55 30.95))'), 4326), 'approximate');
    -- 支派 便雅悯
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-benjamin') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '便雅悯', 'Benjamin', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.1 31.7, 35.45 31.7, 35.45 31.95, 35.1 31.95, 35.1 31.7))'), 4326), 'approximate');
    -- 支派 但
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-dan') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '但', 'Dan', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((34.8 31.85, 35.1 31.85, 35.1 32.1, 34.8 32.1, 34.8 31.85))'), 4326), 'approximate');
    -- 支派 以法莲
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-ephraim') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以法莲', 'Ephraim', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((34.95 31.95, 35.4 31.95, 35.4 32.25, 34.95 32.25, 34.95 31.95))'), 4326), 'approximate');
    -- 支派 玛拿西（西）
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-manasseh-west') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '玛拿西（西）', 'Manasseh (W)', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((34.95 32.25, 35.45 32.25, 35.45 32.65, 34.95 32.65, 34.95 32.25))'), 4326), 'approximate');
    -- 支派 以萨迦
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-issachar') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以萨迦', 'Issachar', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.2 32.5, 35.6 32.5, 35.6 32.78, 35.2 32.78, 35.2 32.5))'), 4326), 'approximate');
    -- 支派 西布伦
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-zebulun') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西布伦', 'Zebulun', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.1 32.65, 35.45 32.65, 35.45 32.95, 35.1 32.95, 35.1 32.65))'), 4326), 'approximate');
    -- 支派 亚设
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-asher') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚设', 'Asher', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35 32.85, 35.3 32.85, 35.3 33.15, 35 33.15, 35 32.85))'), 4326), 'approximate');
    -- 支派 拿弗他利
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-naphtali') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '拿弗他利', 'Naphtali', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.35 32.85, 35.65 32.85, 35.65 33.3, 35.35 33.3, 35.35 32.85))'), 4326), 'approximate');
    -- 支派 流便
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-reuben') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '流便', 'Reuben', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.5 31.3, 35.95 31.3, 35.95 31.85, 35.5 31.85, 35.5 31.3))'), 4326), 'approximate');
    -- 支派 迦得
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-gad') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '迦得', 'Gad', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.55 31.85, 35.95 31.85, 35.95 32.4, 35.55 32.4, 35.55 31.85))'), 4326), 'approximate');
    -- 支派 玛拿西（东·半支派）
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'tribe-manasseh-east') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '玛拿西（东·半支派）', 'Manasseh (E)', '', int4range(-1400, -1004));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1400, -1004), ST_SetSRID(ST_GeomFromText('POLYGON((35.65 32.4, 36.1 32.4, 36.1 32.9, 35.65 32.9, 35.65 32.4))'), 4326), 'approximate');
    -- 以色列联合王国
    INSERT INTO geo_entities(entity_type, slug) VALUES('region', 'united-kingdom') RETURNING entity_id INTO v_id;
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以色列联合王国', 'United Kingdom of Israel', '', int4range(-1004, -930));
    INSERT INTO entity_geometries(entity_id, valid_time, geom_polygon, confidence) VALUES (v_id, int4range(-1004, -930), ST_SetSRID(ST_GeomFromText('POLYGON((34.55 30.8, 36.15 30.8, 36.15 33.35, 34.55 33.35, 34.55 30.8))'), 4326), 'approximate');
    -- 拓扑关系：联合王国包含诸支派
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-judah';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-simeon';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-benjamin';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-dan';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-ephraim';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-manasseh-west';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-issachar';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-zebulun';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-asher';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-naphtali';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-reuben';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-gad';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'contains', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='united-kingdom' AND b.slug='tribe-manasseh-east';
    -- 首都与隶属
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'capital_of', int4range(-1004, -930) FROM geo_entities a, geo_entities b WHERE a.slug='jerusalem' AND b.slug='united-kingdom';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'within', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='jerusalem' AND b.slug='tribe-benjamin';
    -- 支派相邻（示意）
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-judah' AND b.slug='tribe-benjamin';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-judah' AND b.slug='tribe-simeon';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-benjamin' AND b.slug='tribe-ephraim';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-ephraim' AND b.slug='tribe-manasseh-west';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-manasseh-west' AND b.slug='tribe-issachar';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-issachar' AND b.slug='tribe-zebulun';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-zebulun' AND b.slug='tribe-asher';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-asher' AND b.slug='tribe-naphtali';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-reuben' AND b.slug='tribe-gad';
    INSERT INTO geo_relations(src_entity_id, dst_entity_id, relation_type, valid_time) SELECT a.entity_id, b.entity_id, 'adjacent', int4range(-1400, -1004) FROM geo_entities a, geo_entities b WHERE a.slug='tribe-gad' AND b.slug='tribe-manasseh-east';
  END IF;
END $$;
