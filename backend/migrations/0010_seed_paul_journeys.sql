-- Migration 0010: Seed 保罗宣教旅程 — 城市(geo_entities) + 地名 + 经文映射(ACT) + 四条路线
-- Generated from emotion-sphere-ui/src/data/paulJourneys.js。幂等：路线 Paul_Journey_1 已存在则跳过。
-- Depends on 0007 (PostGIS).

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM historical_routes WHERE route_name = 'Paul_Journey_1') THEN
    -- 安提阿（叙利亚）
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(36.16, 36.2), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '安提阿（叙利亚）', 'Antioch (Syria)', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 13, 1, 3, v_id, 'mention');
    -- 西流基
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(35.93, 36.12), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西流基', 'Seleucia', '', int4range(40, 63));
    -- 撒拉米
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(33.9, 35.18), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '撒拉米', 'Salamis', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 13, 5, 5, v_id, 'mention');
    -- 帕弗
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(32.41, 34.77), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '帕弗', 'Paphos', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 13, 6, 12, v_id, 'mention');
    -- 别加
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(30.85, 36.96), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '别加', 'Perga', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 13, 13, 13, v_id, 'mention');
    -- 亚大利
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(30.7, 36.88), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚大利', 'Attalia', '', int4range(40, 63));
    -- 彼西底的安提阿
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(31.19, 38.3), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '彼西底的安提阿', 'Pisidian Antioch', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 13, 16, 48, v_id, 'mention');
    -- 以哥念
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(32.49, 37.87), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以哥念', 'Iconium', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 14, 1, 6, v_id, 'mention');
    -- 路司得
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(32.45, 37.58), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '路司得', 'Lystra', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 14, 8, 18, v_id, 'mention');
    -- 特庇
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(33.3, 37.35), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '特庇', 'Derbe', '', int4range(40, 63));
    -- 特罗亚
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(26.16, 39.75), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '特罗亚', 'Troas', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 16, 9, 10, v_id, 'mention');
    -- 撒摩特喇
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(25.53, 40.46), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '撒摩特喇', 'Samothrace', '', int4range(40, 63));
    -- 尼亚波利
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(24.41, 40.94), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '尼亚波利', 'Neapolis', '', int4range(40, 63));
    -- 腓立比
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(24.29, 41.01), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '腓立比', 'Philippi', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 16, 13, 15, v_id, 'mention');
    -- 暗妃波里
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(23.83, 40.82), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '暗妃波里', 'Amphipolis', '', int4range(40, 63));
    -- 亚波罗尼亚
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(23.45, 40.78), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚波罗尼亚', 'Apollonia', '', int4range(40, 63));
    -- 帖撒罗尼迦
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(22.94, 40.64), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '帖撒罗尼迦', 'Thessalonica', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 17, 1, 9, v_id, 'mention');
    -- 庇哩亚
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(22.2, 40.52), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '庇哩亚', 'Berea', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 17, 10, 12, v_id, 'mention');
    -- 雅典
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(23.73, 37.98), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '雅典', 'Athens', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 17, 22, 31, v_id, 'mention');
    -- 哥林多
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(22.93, 37.94), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '哥林多', 'Corinth', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 18, 1, 11, v_id, 'mention');
    -- 坚革哩
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(22.99, 37.89), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '坚革哩', 'Cenchreae', '', int4range(40, 63));
    -- 以弗所
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(27.34, 37.94), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以弗所', 'Ephesus', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 19, 8, 10, v_id, 'mention');
    -- 米利都
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(27.28, 37.53), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '米利都', 'Miletus', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 20, 17, 38, v_id, 'mention');
    -- 推罗
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(35.2, 33.27), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '推罗', 'Tyre', '', int4range(40, 63));
    -- 凯撒利亚
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(34.89, 32.5), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '凯撒利亚', 'Caesarea Maritima', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 27, 1, 1, v_id, 'mention');
    -- 耶路撒冷
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(35.23, 31.78), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '耶路撒冷', 'Jerusalem', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 21, 17, 33, v_id, 'mention');
    -- 西顿
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(35.37, 33.56), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西顿', 'Sidon', '', int4range(40, 63));
    -- 每拉
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(29.98, 36.26), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '每拉', 'Myra', '', int4range(40, 63));
    -- 佳澳（革哩底）
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(24.8, 34.9), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '佳澳（革哩底）', 'Fair Havens', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 27, 9, 12, v_id, 'mention');
    -- 米利大（马耳他）
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(14.45, 35.9), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '米利大（马耳他）', 'Malta', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 28, 1, 6, v_id, 'mention');
    -- 叙拉古
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(15.29, 37.07), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '叙拉古', 'Syracuse', '', int4range(40, 63));
    -- 利基翁
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(15.65, 38.11), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '利基翁', 'Rhegium', '', int4range(40, 63));
    -- 部丢利
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(14.12, 40.82), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '部丢利', 'Puteoli', '', int4range(40, 63));
    -- 罗马
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(12.5, 41.89), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '罗马', 'Rome', '', int4range(40, 63));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('ACT', 28, 30, 31, v_id, 'mention');
    -- 亚朔
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(26.34, 39.49), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚朔', 'Assos', '', int4range(40, 63));
    -- 米推利尼
    INSERT INTO geo_entities(entity_type) VALUES('city') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(40, 63), ST_SetSRID(ST_MakePoint(26.55, 39.11), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '米推利尼', 'Mitylene', '', int4range(40, 63));
    -- 路线 第一次旅程
    INSERT INTO historical_routes(route_name, valid_time, geom_line) VALUES ('Paul_Journey_1', int4range(40, 63), ST_SetSRID(ST_GeomFromText('LINESTRING(36.16 36.2, 35.93 36.12, 33.9 35.18, 32.41 34.77, 30.85 36.96, 31.19 38.3, 32.49 37.87, 32.45 37.58, 33.3 37.35, 30.7 36.88)'), 4326));
    -- 路线 第二次旅程
    INSERT INTO historical_routes(route_name, valid_time, geom_line) VALUES ('Paul_Journey_2', int4range(40, 63), ST_SetSRID(ST_GeomFromText('LINESTRING(36.16 36.2, 33.3 37.35, 32.45 37.58, 26.16 39.75, 25.53 40.46, 24.41 40.94, 24.29 41.01, 23.83 40.82, 23.45 40.78, 22.94 40.64, 22.2 40.52, 23.73 37.98, 22.93 37.94, 22.99 37.89, 27.34 37.94, 34.89 32.5, 35.23 31.78)'), 4326));
    -- 路线 第三次旅程
    INSERT INTO historical_routes(route_name, valid_time, geom_line) VALUES ('Paul_Journey_3', int4range(40, 63), ST_SetSRID(ST_GeomFromText('LINESTRING(36.16 36.2, 27.34 37.94, 26.16 39.75, 24.29 41.01, 22.93 37.94, 26.34 39.49, 26.55 39.11, 27.28 37.53, 35.2 33.27, 34.89 32.5, 35.23 31.78)'), 4326));
    -- 路线 押往罗马
    INSERT INTO historical_routes(route_name, valid_time, geom_line) VALUES ('Paul_Voyage_Rome', int4range(40, 63), ST_SetSRID(ST_GeomFromText('LINESTRING(34.89 32.5, 35.37 33.56, 29.98 36.26, 24.8 34.9, 14.45 35.9, 15.29 37.07, 15.65 38.11, 14.12 40.82, 12.5 41.89)'), 4326));
  END IF;
END $$;
