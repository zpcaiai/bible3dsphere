import { NextResponse } from 'next/server'
import { getPrisma, type CampaignRow } from '@/features/bible-map/lib/db'
import { seedCampaigns } from '@/features/bible-map/data/seed-campaigns'
import { asGeoJson, asFeatureCollection } from '@/features/bible-map/lib/geojson'
import type {
  ApiResult,
  BibleCampaignDTO,
  GeoJsonLineString,
  GeoJsonPoint,
} from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

function mapRow(r: CampaignRow): BibleCampaignDTO {
  return {
    id: r.id, name: r.name, nameZh: r.nameZh, commander: r.commander,
    commanderZh: r.commanderZh, startYear: r.startYear, endYear: r.endYear,
    book: r.book, chapter: r.chapter,
    routeGeojson: asGeoJson<GeoJsonLineString>(r.routeGeojson),
    pointsGeojson:
      r.pointsGeojson === null
        ? null
        : asFeatureCollection<GeoJsonPoint>(r.pointsGeojson),
    description: r.description,
  }
}

export async function GET(req: Request): Promise<NextResponse<ApiResult<BibleCampaignDTO[]>>> {
  try {
    const { searchParams } = new URL(req.url)
    const id = searchParams.get('id')

    let all: BibleCampaignDTO[] = seedCampaigns
    const db = await getPrisma()
    if (db) {
      try {
        const rows = await db.bibleCampaign.findMany()
        if (rows.length > 0) all = rows.map(mapRow)
      } catch {
        all = seedCampaigns
      }
    }
    const data = id ? all.filter((c) => c.id === id) : all
    return NextResponse.json({ success: true, data })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
