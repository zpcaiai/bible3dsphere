import { PrismaClient, Prisma } from '@prisma/client'
import { seedTerritories } from '../src/features/bible-map/data/seed-territories'
import { seedEvents } from '../src/features/bible-map/data/seed-events'
import { seedProphecies } from '../src/features/bible-map/data/seed-prophecies'
import { seedCampaigns } from '../src/features/bible-map/data/seed-campaigns'

const prisma = new PrismaClient()

function json(value: unknown): Prisma.InputJsonValue {
  return value as Prisma.InputJsonValue
}

async function main(): Promise<void> {
  for (const t of seedTerritories) {
    const data = {
      name: t.name, nameZh: t.nameZh, ownerType: t.ownerType, ownerId: t.ownerId,
      ownerName: t.ownerName, period: t.period, startYear: t.startYear, endYear: t.endYear,
      controlScore: t.controlScore, status: t.status, color: t.color,
      geojson: json(t.geojson), description: t.description,
    }
    await prisma.bibleTerritory.upsert({ where: { id: t.id }, create: { id: t.id, ...data }, update: data })
  }
  for (const e of seedEvents) {
    const data = {
      title: e.title, titleZh: e.titleZh, category: e.category, book: e.book, chapter: e.chapter,
      startYear: e.startYear, endYear: e.endYear, locationName: e.locationName,
      latitude: e.latitude, longitude: e.longitude,
      geojson: e.geojson === null ? Prisma.JsonNull : json(e.geojson),
      description: e.description, spiritualMeaning: e.spiritualMeaning,
    }
    await prisma.bibleMapEvent.upsert({ where: { id: e.id }, create: { id: e.id, ...data }, update: data })
  }
  for (const p of seedProphecies) {
    const data = {
      book: p.book, chapterStart: p.chapterStart, chapterEnd: p.chapterEnd,
      targetNation: p.targetNation, targetNationZh: p.targetNationZh, prophecyType: p.prophecyType,
      startYear: p.startYear, fulfillmentYear: p.fulfillmentYear, sourceLocation: p.sourceLocation,
      targetLatitude: p.targetLatitude, targetLongitude: p.targetLongitude,
      description: p.description, fulfillmentDescription: p.fulfillmentDescription,
    }
    await prisma.bibleProphecy.upsert({ where: { id: p.id }, create: { id: p.id, ...data }, update: data })
  }
  for (const c of seedCampaigns) {
    const data = {
      name: c.name, nameZh: c.nameZh, commander: c.commander, commanderZh: c.commanderZh,
      startYear: c.startYear, endYear: c.endYear, book: c.book, chapter: c.chapter,
      routeGeojson: json(c.routeGeojson),
      pointsGeojson: c.pointsGeojson === null ? Prisma.JsonNull : json(c.pointsGeojson),
      description: c.description,
    }
    await prisma.bibleCampaign.upsert({ where: { id: c.id }, create: { id: c.id, ...data }, update: data })
  }
  const counts = {
    territories: seedTerritories.length, events: seedEvents.length,
    prophecies: seedProphecies.length, campaigns: seedCampaigns.length,
  }
  console.log('[seed] bible-map done:', counts)
}

main()
  .catch((e) => { console.error(e); process.exit(1) })
  .finally(() => { void prisma.$disconnect() })
