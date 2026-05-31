-- Migration 0008: Seed 出埃及与旷野漂流 — 民数记33章 42站 + 路线
-- Generated from emotion-sphere-ui/src/data/exodusStations.js (single source of truth).
-- Idempotent: only seeds if route Exodus_Traditional 不存在。Depends on 0007 (PostGIS).

DO $$
DECLARE v_id INT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM historical_routes WHERE route_name = 'Exodus_Traditional') THEN
    -- 第1站 兰塞 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(31.83, 30.8), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '兰塞', 'Rameses', 'רַעְמְסֵס', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 5, 5, v_id, 'camp');
    -- 第2站 疏割 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(32.1, 30.55), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '疏割', 'Succoth', 'סֻכּוֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 6, 6, v_id, 'camp');
    -- 第3站 以倘 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(32.35, 30.42), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以倘', 'Etham', 'אֵתָם', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 7, 7, v_id, 'camp');
    -- 第4站 比哈希录（过红海） (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(32.55, 30.05), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '比哈希录（过红海）', 'Pi-hahiroth', 'פִּי הַחִירֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 7, 8, v_id, 'camp');
    -- 第5站 玛拉 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.08, 29.22), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '玛拉', 'Marah', 'מָרָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 8, 8, v_id, 'camp');
    -- 第6站 以琳 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.13, 29.1), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以琳', 'Elim', 'אֵילִם', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 9, 9, v_id, 'camp');
    -- 第7站 红海边 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.18, 28.92), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '红海边', 'By the Red Sea', 'יַם סוּף', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 10, 10, v_id, 'camp');
    -- 第8站 汛的旷野 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.42, 28.78), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '汛的旷野', 'Wilderness of Sin', 'מִדְבַּר סִין', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 11, 11, v_id, 'camp');
    -- 第9站 脱加 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.46, 28.9), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '脱加', 'Dophkah', 'דָּפְקָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 12, 12, v_id, 'camp');
    -- 第10站 亚录 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.6, 28.8), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚录', 'Alush', 'אָלוּשׁ', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 13, 13, v_id, 'camp');
    -- 第11站 利非订 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.66, 28.72), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '利非订', 'Rephidim', 'רְפִידִים', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 14, 14, v_id, 'camp');
    -- 第12站 西奈山 (identified)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(33.975, 28.539), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '西奈山', 'Mount Sinai', 'הַר סִינַי', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 15, 15, v_id, 'camp');
    -- 第13站 基博罗哈他瓦（贪欲之坟） (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.1, 28.72), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '基博罗哈他瓦（贪欲之坟）', 'Kibroth-hattaavah', 'קִבְרוֹת הַתַּאֲוָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 16, 16, v_id, 'camp');
    -- 第14站 哈洗录 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.42, 28.92), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '哈洗录', 'Hazeroth', 'חֲצֵרוֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 17, 17, v_id, 'camp');
    -- 第15站 利提玛 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.3, 29.35), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '利提玛', 'Rithmah', 'רִתְמָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 18, 18, v_id, 'camp');
    -- 第16站 临门帕烈 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.4, 29.65), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '临门帕烈', 'Rimmon-perez', 'רִמֹּן פֶּרֶץ', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 19, 19, v_id, 'camp');
    -- 第17站 立拿 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.46, 29.92), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '立拿', 'Libnah', 'לִבְנָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 20, 20, v_id, 'camp');
    -- 第18站 勒撒 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.56, 30.05), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '勒撒', 'Rissah', 'רִסָּה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 21, 21, v_id, 'camp');
    -- 第19站 基希拉他 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.66, 30.1), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '基希拉他', 'Kehelathah', 'קְהֵלָתָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 22, 22, v_id, 'camp');
    -- 第20站 沙斐山 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.76, 30.02), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '沙斐山', 'Mount Shepher', 'הַר שָׁפֶר', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 23, 23, v_id, 'camp');
    -- 第21站 哈拉大 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.82, 29.88), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '哈拉大', 'Haradah', 'חֲרָדָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 24, 24, v_id, 'camp');
    -- 第22站 玛吉希录 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.86, 29.74), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '玛吉希录', 'Makheloth', 'מַקְהֵלֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 25, 25, v_id, 'camp');
    -- 第23站 他哈 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.9, 29.64), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '他哈', 'Tahath', 'תָּחַת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 26, 26, v_id, 'camp');
    -- 第24站 他拉 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.92, 29.55), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '他拉', 'Terah', 'תָּרַח', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 27, 27, v_id, 'camp');
    -- 第25站 密加 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.95, 29.5), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '密加', 'Mithkah', 'מִתְקָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 28, 28, v_id, 'camp');
    -- 第26站 哈摩拿 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.97, 29.48), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '哈摩拿', 'Hashmonah', 'חַשְׁמֹנָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 29, 29, v_id, 'camp');
    -- 第27站 摩西录 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35, 29.46), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '摩西录', 'Moseroth', 'מֹסֵרוֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 30, 30, v_id, 'camp');
    -- 第28站 比尼亚干 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.98, 29.54), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '比尼亚干', 'Bene-jaakan', 'בְּנֵי יַעֲקָן', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 31, 31, v_id, 'camp');
    -- 第29站 曷哈及甲 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.99, 29.51), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '曷哈及甲', 'Hor-haggidgad', 'חֹר הַגִּדְגָּד', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 32, 32, v_id, 'camp');
    -- 第30站 约巴他 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.96, 29.58), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '约巴他', 'Jotbathah', 'יָטְבָתָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 33, 33, v_id, 'camp');
    -- 第31站 阿博拿 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.96, 29.53), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '阿博拿', 'Abronah', 'עַבְרֹנָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 34, 34, v_id, 'camp');
    -- 第32站 以旬迦别 (identified)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.976, 29.54), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以旬迦别', 'Ezion-geber', 'עֶצְיֹן גֶּבֶר', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 35, 35, v_id, 'camp');
    -- 第33站 加低斯（寻的旷野） (identified)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(34.43, 30.65), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '加低斯（寻的旷野）', 'Kadesh', 'קָדֵשׁ', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 36, 36, v_id, 'camp');
    -- 第34站 何珥山 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.4, 30.32), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '何珥山', 'Mount Hor', 'הֹר הָהָר', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 37, 39, v_id, 'camp');
    -- 第35站 撒摩拿（铜蛇事件） (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.45, 30.45), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '撒摩拿（铜蛇事件）', 'Zalmonah', 'צַלְמֹנָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 41, 41, v_id, 'camp');
    -- 第36站 普嫩 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.5, 30.62), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '普嫩', 'Punon', 'פּוּנֹן', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 42, 42, v_id, 'camp');
    -- 第37站 阿伯 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.55, 30.74), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '阿伯', 'Oboth', 'אֹבֹת', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 43, 43, v_id, 'camp');
    -- 第38站 以耶亚巴琳 (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.55, 30.96), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '以耶亚巴琳', 'Iye-abarim', 'עִיֵּי הָעֲבָרִים', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 44, 44, v_id, 'camp');
    -- 第39站 底本迦得 (identified)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.78, 31.5), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '底本迦得', 'Dibon-gad', 'דִּיבֹן גָּד', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 45, 45, v_id, 'camp');
    -- 第40站 亚门低比拉太音 (unknown)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.8, 31.55), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚门低比拉太音', 'Almon-diblathaim', 'עַלְמֹן דִּבְלָתָיְמָה', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 46, 46, v_id, 'camp');
    -- 第41站 亚巴琳山（尼波前） (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.73, 31.77), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '亚巴琳山（尼波前）', 'Mountains of Abarim', 'הָרֵי הָעֲבָרִים', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 47, 47, v_id, 'camp');
    -- 第42站 摩押平原（什亭） (approximate)
    INSERT INTO geo_entities(entity_type) VALUES('camp') RETURNING entity_id INTO v_id;
    INSERT INTO entity_geometries(entity_id, valid_time, geom_point) VALUES (v_id, int4range(-1446, -1406), ST_SetSRID(ST_MakePoint(35.62, 31.83), 4326));
    INSERT INTO entity_names(entity_id, name_zh, name_en, name_hebrew, valid_time) VALUES (v_id, '摩押平原（什亭）', 'Plains of Moab', 'עַרְבֹת מוֹאָב', int4range(-1446, -1406));
    INSERT INTO scripture_geo_mappings(book_code, chapter, verse_start, verse_end, entity_id, association_type) VALUES ('NUM', 33, 48, 49, v_id, 'camp');
    -- 路线轨迹
    INSERT INTO historical_routes(route_name, valid_time, geom_line) VALUES ('Exodus_Traditional', int4range(-1446, -1406), ST_SetSRID(ST_GeomFromText('LINESTRING(31.83 30.8, 32.1 30.55, 32.35 30.42, 32.55 30.05, 33.08 29.22, 33.13 29.1, 33.18 28.92, 33.42 28.78, 33.46 28.9, 33.6 28.8, 33.66 28.72, 33.975 28.539, 34.1 28.72, 34.42 28.92, 34.3 29.35, 34.4 29.65, 34.46 29.92, 34.56 30.05, 34.66 30.1, 34.76 30.02, 34.82 29.88, 34.86 29.74, 34.9 29.64, 34.92 29.55, 34.95 29.5, 34.97 29.48, 35 29.46, 34.98 29.54, 34.99 29.51, 34.96 29.58, 34.96 29.53, 34.976 29.54, 34.43 30.65, 35.4 30.32, 35.45 30.45, 35.5 30.62, 35.55 30.74, 35.55 30.96, 35.78 31.5, 35.8 31.55, 35.73 31.77, 35.62 31.83)'), 4326));
  END IF;
END $$;
