// Prisma 客户端单例 + 优雅降级。
// 用结构化 BmClient 接口而非 @prisma/client 生成类型，使得：
//   1. 即便尚未 `prisma generate`，tsc 也能通过；
//   2. 未配置 DATABASE_URL / 未安装 prisma / 连接失败 → 返回 null，路由回退本地 seed。

export interface TerritoryRow {
  id: string
  name: string
  nameZh: string
  ownerType: string
  ownerId: string | null
  ownerName: string
  period: string
  startYear: number
  endYear: number | null
  controlScore: number
  status: string
  color: string | null
  geojson: unknown
  description: string | null
}
export interface EventRow {
  id: string
  title: string
  titleZh: string
  category: string
  book: string | null
  chapter: number | null
  startYear: number
  endYear: number | null
  locationName: string | null
  latitude: number | null
  longitude: number | null
  geojson: unknown
  description: string | null
  spiritualMeaning: string | null
}
export interface ProphecyRow {
  id: string
  book: string
  chapterStart: number
  chapterEnd: number | null
  targetNation: string
  targetNationZh: string
  prophecyType: string
  startYear: number | null
  fulfillmentYear: number | null
  sourceLocation: string
  targetLatitude: number
  targetLongitude: number
  description: string
  fulfillmentDescription: string | null
}
export interface CampaignRow {
  id: string
  name: string
  nameZh: string
  commander: string | null
  commanderZh: string | null
  startYear: number
  endYear: number | null
  book: string | null
  chapter: number | null
  routeGeojson: unknown
  pointsGeojson: unknown
  description: string | null
}

interface FindManyArgs {
  where?: Record<string, unknown>
  orderBy?: Record<string, 'asc' | 'desc'>
}
interface Delegate<T> {
  findMany(args?: FindManyArgs): Promise<T[]>
}
export interface BmClient {
  bibleTerritory: Delegate<TerritoryRow>
  bibleMapEvent: Delegate<EventRow>
  bibleProphecy: Delegate<ProphecyRow>
  bibleCampaign: Delegate<CampaignRow>
}

type GlobalWithPrisma = typeof globalThis & { __bmPrisma?: BmClient | null }
let initialized = false

export async function getPrisma(): Promise<BmClient | null> {
  const g = globalThis as GlobalWithPrisma
  if (initialized) return g.__bmPrisma ?? null
  initialized = true
  if (!process.env.DATABASE_URL) {
    g.__bmPrisma = null
    return null
  }
  try {
    const mod = (await import('@prisma/client')) as unknown as {
      PrismaClient: new () => unknown
    }
    const client = new mod.PrismaClient() as unknown as BmClient
    g.__bmPrisma = client
    return client
  } catch {
    g.__bmPrisma = null
    return null
  }
}
