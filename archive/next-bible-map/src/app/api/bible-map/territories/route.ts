import { NextResponse } from 'next/server'
import { getPrisma, type TerritoryRow } from '@/features/bible-map/lib/db'
import { seedTerritories } from '@/features/bible-map/data/seed-territories'
import { asGeoJson } from '@/features/bible-map/lib/geojson'
import { DEFAULT_YEAR } from '@/features/bible-map/domain/constants'
import type {
  ApiResult,
  BibleTerritoryDTO,
  GeoJsonMultiPolygon,
  GeoJsonPolygon,
  TerritoryStatus,
} from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

function mapRow(r: TerritoryRow): BibleTerritoryDTO {
  return {
    id: r.id, name: r.name, nameZh: r.nameZh, ownerType: r.ownerType,
    ownerId: r.ownerId, ownerName: r.ownerName, period: r.period,
    startYear: r.startYear, endYear: r.endYear, controlScore: r.controlScore,
    status: r.status as TerritoryStatus, color: r.color,
    geojson: asGeoJson<GeoJsonPolygon | GeoJsonMultiPolygon>(r.geojson),
    description: r.description,
  }
}

function activeInYear(t: BibleTerritoryDTO, year: number): boolean {
  return t.startYear <= year && (t.endYear === null || t.endYear >= year)
}

export async function GET(req: Request): Promise<NextResponse<ApiResult<BibleTerritoryDTO[]>>> {
  try {
    const { searchParams } = new URL(req.url)
    const year = Number.parseInt(searchParams.get('year') ?? String(DEFAULT_YEAR), 10)
    const layer = searchParams.get('layer') ?? 'all'

    let all: BibleTerritoryDTO[] = seedTerritories
    const db = await getPrisma()
    if (db) {
      try {
        const rows = await db.bibleTerritory.findMany()
        if (rows.length > 0) all = rows.map(mapRow)
      } catch {
        all = seedTerritories
      }
    }

    const byLayer = all.filter((t) => {
      if (layer === 'tribes') return t.ownerType === 'tribe'
      if (layer === 'empires') return t.ownerType === 'empire'
      if (layer === 'all') return t.ownerType === 'tribe' || t.ownerType === 'empire'
      return false // prophecies / campaigns 由各自端点提供
    })
    const data = byLayer.filter((t) => activeInYear(t, year))
    return NextResponse.json({ success: true, data })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
