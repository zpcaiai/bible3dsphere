-- Migration 0016: 耶路撒冷城墙精度提升 —— 按各时代考古footprint更新polygon
-- 依 valid_time 起始年匹配 0012 写入的几何快照逐代UPDATE。Depends on 0012。
-- 幂等：UPDATE 本身可重复执行；实体不存在时影响0行。

-- 撒冷（麦基洗德时期）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.2352 31.7705, 35.2367 31.7707, 35.237 31.774, 35.2353 31.7742, 35.2348 31.7723, 35.2352 31.7705))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -2000;

-- 耶布斯（士师时期）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.2352 31.7705, 35.2367 31.7707, 35.237 31.774, 35.2353 31.7742, 35.2348 31.7723, 35.2352 31.7705))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -1400;

-- 大卫城（联合王国）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.235 31.77, 35.2368 31.7702, 35.2372 31.7745, 35.2352 31.7748, 35.2346 31.7725, 35.235 31.77))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -1004;

-- 所罗门的耶路撒冷
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.235 31.77, 35.2368 31.7702, 35.2375 31.7745, 35.2378 31.7785, 35.2335 31.7788, 35.2332 31.7748, 35.2346 31.7725, 35.235 31.77))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -960;

-- 希西家扩建（犹大王国）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.227 31.77, 35.23 31.7685, 35.237 31.77, 35.238 31.7785, 35.233 31.7795, 35.2268 31.778, 35.2262 31.773, 35.227 31.77))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -700;

-- 归回时期（尼希米重建）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.2348 31.7702, 35.2366 31.7704, 35.2374 31.7745, 35.2376 31.7782, 35.2336 31.7785, 35.2333 31.7748, 35.2346 31.7726, 35.2348 31.7702))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -586;

-- 新约时期（希律扩建）
UPDATE entity_geometries SET geom_polygon = ST_SetSRID(ST_GeomFromText('POLYGON((35.2255 31.77, 35.229 31.768, 35.238 31.769, 35.24 31.776, 35.2398 31.781, 35.234 31.783, 35.227 31.7815, 35.225 31.7755, 35.2255 31.77))'), 4326)
WHERE entity_id = (SELECT entity_id FROM geo_entities WHERE slug = 'jerusalem')
  AND lower(valid_time) = -20;

