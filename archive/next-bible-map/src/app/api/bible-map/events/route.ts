import { NextResponse } from 'next/server'
import { getPrisma, type EventRow } from '@/features/bible-map/lib/db'
import { seedEvents } from '@/features/bible-map/data/seed-events'
import { asGeoJson } from '@/features/bible-map/lib/geojson'
import { DEFAULT_YEAR, EVENT_YEAR_WINDOW } from '@/features/bible-map/domain/constants'
import type {
  ApiResult,
  BibleMapEventDTO,
  GeoJsonGeometry,
} from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

function mapRow(r: EventRow): BibleMapEventDTO {
  return {
    id: r.id, title: r.title, titleZh: r.titleZh, category: r.category,
    book: r.book, chapter: r.chapter, startYear: r.startYear, endYear: r.endYear,
    locationName: r.locationName, latitude: r.latitude, longitude: r.longitude,
    geojson: r.geojson === null ? null : asGeoJson<GeoJsonGeometry>(r.geojson),
    description: r.description, spiritualMeaning: r.spiritualMeaning,
  }
}

function nearYear(e: BibleMapEventDTO, year: number): boolean {
  const end = e.endYear ?? e.startYear
  if (e.startYear <= year && year <= end) return true
  const dist = Math.min(Math.abs(e.startYear - year), Math.abs(end - year))
  return dist <= EVENT_YEAR_WINDOW
}

export async function GET(req: Request): Promise<NextResponse<ApiResult<BibleMapEventDTO[]>>> {
  try {
    const { searchParams } = new URL(req.url)
    const year = Number.parseInt(searchParams.get('year') ?? String(DEFAULT_YEAR), 10)

    let all: BibleMapEventDTO[] = seedEvents
    const db = await getPrisma()
    if (db) {
      try {
        const rows = await db.bibleMapEvent.findMany()
        if (rows.length > 0) all = rows.map(mapRow)
      } catch {
        all = seedEvents
      }
    }
    const data = all
      .filter((e) => nearYear(e, year))
      .sort((a, b) => a.startYear - b.startYear)
    return NextResponse.json({ success: true, data })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
