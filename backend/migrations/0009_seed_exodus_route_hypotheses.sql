-- Migration 0009: Seed 出埃及多路线假说（北方沿海 / 沙特阿拉伯）到 historical_routes
-- 传统南方路线(Exodus_Traditional)已由 0008 种子。幂等：route_name 已存在则跳过。
-- Depends on 0007 (PostGIS) + 0008.

INSERT INTO historical_routes(route_name, valid_time, geom_line)
SELECT 'Exodus_Northern', int4range(-1446, -1406), ST_SetSRID(ST_GeomFromText('LINESTRING(31.83 30.8, 32.3 31, 33 31.1, 33.6 30.9, 34.05 30.62, 34.43 30.65, 34.976 29.54, 35.4 30.32, 35.5 30.62, 35.78 31.5, 35.73 31.77, 35.62 31.83)'), 4326)
WHERE NOT EXISTS (SELECT 1 FROM historical_routes WHERE route_name = 'Exodus_Northern');

INSERT INTO historical_routes(route_name, valid_time, geom_line)
SELECT 'Exodus_SaudiArabia', int4range(-1446, -1406), ST_SetSRID(ST_GeomFromText('LINESTRING(31.83 30.8, 32.1 30.55, 32.8 30, 33.5 29.4, 34.2 29.2, 34.67 28.97, 34.85 28.85, 35.3 28.65, 35.1 29.2, 34.976 29.54, 34.43 30.65, 35.4 30.32, 35.5 30.62, 35.78 31.5, 35.73 31.77, 35.62 31.83)'), 4326)
WHERE NOT EXISTS (SELECT 1 FROM historical_routes WHERE route_name = 'Exodus_SaudiArabia');

