import { NextResponse } from 'next/server'
import { territoriesAtPoint, type SpatialTerritory } from '@/features/bible-map/lib/postgis'
import { seedTerritories } from '@/features/bible-map/data/seed-territories'
import { pointInGeometry } from '@/features/bible-map/lib/geojson'
import { DEFAULT_YEAR } from '@/features/bible-map/domain/constants'
import type { ApiResult } from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

// GET /api/bible-map/territories/at?lng=35.2&lat=31.8&year=-1200
// v2：优先 PostGIS ST_Contains；无数据库时回退本地 point-in-polygon。
export async function GET(req: Request): Promise<NextResponse<ApiResult<SpatialTerritory[]>>> {
  try {
    const { searchParams } = new URL(req.url)
    const lng = Number.parseFloat(searchParams.get('lng') ?? '')
    const lat = Number.parseFloat(searchParams.get('lat') ?? '')
    const year = Number.parseInt(searchParams.get('year') ?? String(DEFAULT_YEAR), 10)
    if (Number.isNaN(lng) || Number.isNaN(lat)) {
      return NextResponse.json({ success: false, error: '缺少有效的 lng / lat 参数' }, { status: 400 })
    }

    const spatial = await territoriesAtPoint(lng, lat, year)
    if (spatial !== null) {
      return NextResponse.json({ success: true, data: spatial })
    }

    // 本地回退
    const data: SpatialTerritory[] = seedTerritories
      .filter((t) => t.startYear <= year && (t.endYear === null || t.endYear >= year))
      .filter((t) => pointInGeometry(lng, lat, t.geojson))
      .map((t) => ({
        id: t.id,
        nameZh: t.nameZh,
        status: t.status,
        controlScore: t.controlScore,
        geojson: t.geojson,
      }))
    return NextResponse.json({ success: true, data })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
