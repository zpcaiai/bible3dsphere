import { NextResponse } from 'next/server'
import { getPrisma, type ProphecyRow } from '@/features/bible-map/lib/db'
import { seedProphecies } from '@/features/bible-map/data/seed-prophecies'
import type {
  ApiResult,
  BibleProphecyDTO,
  ProphecyType,
} from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

function mapRow(r: ProphecyRow): BibleProphecyDTO {
  return {
    id: r.id, book: r.book, chapterStart: r.chapterStart, chapterEnd: r.chapterEnd,
    targetNation: r.targetNation, targetNationZh: r.targetNationZh,
    prophecyType: r.prophecyType as ProphecyType,
    startYear: r.startYear, fulfillmentYear: r.fulfillmentYear,
    sourceLocation: r.sourceLocation, targetLatitude: r.targetLatitude,
    targetLongitude: r.targetLongitude, description: r.description,
    fulfillmentDescription: r.fulfillmentDescription,
  }
}

export async function GET(req: Request): Promise<NextResponse<ApiResult<BibleProphecyDTO[]>>> {
  try {
    const { searchParams } = new URL(req.url)
    const book = searchParams.get('book')
    const chapterRaw = searchParams.get('chapter')
    const chapter = chapterRaw === null ? null : Number.parseInt(chapterRaw, 10)

    let all: BibleProphecyDTO[] = seedProphecies
    const db = await getPrisma()
    if (db) {
      try {
        const rows = await db.bibleProphecy.findMany()
        if (rows.length > 0) all = rows.map(mapRow)
      } catch {
        all = seedProphecies
      }
    }

    const data = all.filter((p) => {
      if (book && p.book.toLowerCase() !== book.toLowerCase()) return false
      if (chapter !== null && !Number.isNaN(chapter)) {
        const end = p.chapterEnd ?? p.chapterStart
        if (!(p.chapterStart <= chapter && chapter <= end)) return false
      }
      return true
    })
    return NextResponse.json({ success: true, data })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
