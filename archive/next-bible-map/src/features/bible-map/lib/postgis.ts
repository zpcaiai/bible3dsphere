// 圣经地图 v2 · PostGIS 空间数据访问层。
// 通过 prisma.$queryRawUnsafe 执行 ST_AsGeoJSON / ST_Contains / ST_Intersects 等空间查询。
// 未配置 DATABASE_URL / 未安装 prisma / 几何列不存在 → 返回 null，由调用方回退本地几何计算。
import { asGeoJson } from './geojson'
import type { GeoJsonMultiPolygon, GeoJsonPolygon } from '../domain/types'

interface RawClient {
  $queryRawUnsafe<T = unknown>(query: string, ...values: unknown[]): Promise<T>
}
type GlobalWithRaw = typeof globalThis & { __bmRaw?: RawClient | null }
let initialized = false

export async function getRawClient(): Promise<RawClient | null> {
  const g = globalThis as GlobalWithRaw
  if (initialized) return g.__bmRaw ?? null
  initialized = true
  if (!process.env.DATABASE_URL) {
    g.__bmRaw = null
    return null
  }
  try {
    const mod = (await import('@prisma/client')) as unknown as { PrismaClient: new () => RawClient }
    g.__bmRaw = new mod.PrismaClient()
    return g.__bmRaw
  } catch {
    g.__bmRaw = null
    return null
  }
}

export interface SpatialTerritory {
  id: string
  nameZh: string
  status: string
  controlScore: number
  geojson: GeoJsonPolygon | GeoJsonMultiPolygon
}

interface SpatialRow {
  id: string
  nameZh: string
  status: string
  controlScore: number
  geojson: string
}

function mapRows(rows: SpatialRow[]): SpatialTerritory[] {
  return rows.map((r) => ({
    id: r.id,
    nameZh: r.nameZh,
    status: r.status,
    controlScore: r.controlScore,
    geojson: asGeoJson<GeoJsonPolygon | GeoJsonMultiPolygon>(JSON.parse(r.geojson)),
  }))
}

/** ST_Contains：返回包含给定点、且在该年份有效的 territory（null = 无 DB，调用方回退） */
export async function territoriesAtPoint(
  lng: number,
  lat: number,
  year: number,
): Promise<SpatialTerritory[] | null> {
  const db = await getRawClient()
  if (!db) return null
  try {
    const rows = await db.$queryRawUnsafe<SpatialRow[]>(
      `SELECT id, "nameZh", status, "controlScore", ST_AsGeoJSON(geom) AS geojson
       FROM "BibleTerritory"
       WHERE geom IS NOT NULL
         AND ST_Contains(geom, ST_SetSRID(ST_MakePoint($1, $2), 4326))
         AND "startYear" <= $3 AND ("endYear" IS NULL OR "endYear" >= $3)`,
      lng,
      lat,
      year,
    )
    return mapRows(rows)
  } catch {
    return null
  }
}

/** ST_Intersects：返回与 bbox 相交、且在该年份有效的 territory（含 ST_AsGeoJSON） */
export async function territoriesInBbox(
  west: number,
  south: number,
  east: number,
  north: number,
  year: number,
): Promise<SpatialTerritory[] | null> {
  const db = await getRawClient()
  if (!db) return null
  try {
    const rows = await db.$queryRawUnsafe<SpatialRow[]>(
      `SELECT id, "nameZh", status, "controlScore", ST_AsGeoJSON(geom) AS geojson
       FROM "BibleTerritory"
       WHERE geom IS NOT NULL
         AND ST_Intersects(geom, ST_MakeEnvelope($1, $2, $3, $4, 4326))
         AND "startYear" <= $5 AND ("endYear" IS NULL OR "endYear" >= $5)`,
      west,
      south,
      east,
      north,
      year,
    )
    return mapRows(rows)
  } catch {
    return null
  }
}
