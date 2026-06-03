-- 圣经地图 v2：PostGIS geometry 列 + 回填 + GIST 索引。
-- 运行（Neon/Postgres）：
--   npx prisma db execute --file prisma/sql/postgis_geometry.sql --schema prisma/schema.prisma
-- 顺序建议：先确保已 `prisma migrate`（建好基础表），再执行本文件。

CREATE EXTENSION IF NOT EXISTS postgis;

ALTER TABLE "BibleTerritory" ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326);
ALTER TABLE "BibleMapEvent"  ADD COLUMN IF NOT EXISTS geom geometry(Point, 4326);
ALTER TABLE "BibleProphecy"  ADD COLUMN IF NOT EXISTS geom_target geometry(Point, 4326);
ALTER TABLE "BibleCampaign"  ADD COLUMN IF NOT EXISTS geom_route geometry(LineString, 4326);

-- 由已有 Json 列回填 geometry（territory 的 geojson 可能是 Polygon/MultiPolygon，统一为 Multi）
UPDATE "BibleTerritory"
  SET geom = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(geojson::text), 4326))
  WHERE geom IS NULL AND geojson IS NOT NULL;
UPDATE "BibleCampaign"
  SET geom_route = ST_SetSRID(ST_GeomFromGeoJSON("routeGeojson"::text), 4326)
  WHERE geom_route IS NULL AND "routeGeojson" IS NOT NULL;
UPDATE "BibleMapEvent"
  SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
  WHERE geom IS NULL AND longitude IS NOT NULL AND latitude IS NOT NULL;
UPDATE "BibleProphecy"
  SET geom_target = ST_SetSRID(ST_MakePoint("targetLongitude", "targetLatitude"), 4326)
  WHERE geom_target IS NULL;

CREATE INDEX IF NOT EXISTS idx_territory_geom ON "BibleTerritory" USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_event_geom     ON "BibleMapEvent"  USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_prophecy_geom  ON "BibleProphecy"  USING GIST (geom_target);
CREATE INDEX IF NOT EXISTS idx_campaign_geom  ON "BibleCampaign"  USING GIST (geom_route);
