import { rectPolygon } from '../lib/geojson'
import type { BibleTerritoryDTO, TerritoryStatus } from '../domain/types'

interface TribeDef {
  id: string
  name: string
  nameZh: string
  bbox: [number, number, number, number] // west,south,east,north
  controlScore: number
  status: TerritoryStatus
}

const TRIBES: TribeDef[] = [
  { id: 'judah', name: 'Judah', nameZh: '犹大', bbox: [34.85, 31.0, 35.4, 31.65], controlScore: 85, status: 'stable' },
  { id: 'benjamin', name: 'Benjamin', nameZh: '便雅悯', bbox: [35.1, 31.7, 35.45, 31.95], controlScore: 62, status: 'disputed' },
  { id: 'ephraim', name: 'Ephraim', nameZh: '以法莲', bbox: [34.95, 31.95, 35.4, 32.25], controlScore: 78, status: 'stable' },
  { id: 'manasseh-west', name: 'Manasseh (West)', nameZh: '西玛拿西', bbox: [34.95, 32.25, 35.45, 32.65], controlScore: 70, status: 'stable' },
  { id: 'manasseh-east', name: 'Manasseh (East)', nameZh: '东玛拿西', bbox: [35.65, 32.4, 36.1, 32.9], controlScore: 55, status: 'disputed' },
  { id: 'dan', name: 'Dan', nameZh: '但', bbox: [34.8, 31.85, 35.1, 32.1], controlScore: 42, status: 'oppressed' },
  { id: 'asher', name: 'Asher', nameZh: '亚设', bbox: [35.0, 32.85, 35.3, 33.15], controlScore: 40, status: 'lost' },
  { id: 'naphtali', name: 'Naphtali', nameZh: '拿弗他利', bbox: [35.35, 32.85, 35.65, 33.3], controlScore: 58, status: 'disputed' },
  { id: 'zebulun', name: 'Zebulun', nameZh: '西布伦', bbox: [35.1, 32.65, 35.45, 32.95], controlScore: 66, status: 'stable' },
  { id: 'issachar', name: 'Issachar', nameZh: '以萨迦', bbox: [35.2, 32.5, 35.6, 32.78], controlScore: 60, status: 'stable' },
  { id: 'gad', name: 'Gad', nameZh: '迦得', bbox: [35.55, 31.85, 35.95, 32.4], controlScore: 60, status: 'disputed' },
  { id: 'reuben', name: 'Reuben', nameZh: '流便', bbox: [35.5, 31.3, 35.95, 31.85], controlScore: 54, status: 'disputed' },
  { id: 'simeon', name: 'Simeon', nameZh: '西缅', bbox: [34.55, 30.95, 35.0, 31.3], controlScore: 45, status: 'oppressed' },
]

const tribeTerritories: BibleTerritoryDTO[] = TRIBES.map((t) => ({
  id: `tribe-${t.id}`,
  name: t.name,
  nameZh: t.nameZh,
  ownerType: 'tribe',
  ownerId: t.id,
  ownerName: t.nameZh,
  period: 'tribal_allotment',
  startYear: -1400,
  endYear: -1050,
  controlScore: t.controlScore,
  status: t.status,
  color: null,
  geojson: rectPolygon(...t.bbox),
  description: `${t.nameZh}支派（${t.name}）在约书亚分地中所得的地业（教学示意范围）。`,
}))

interface EmpireDef {
  id: string
  name: string
  nameZh: string
  bbox: [number, number, number, number]
  startYear: number
  endYear: number
  controlScore: number
}

const EMPIRES: EmpireDef[] = [
  { id: 'assyria', name: 'Assyria', nameZh: '亚述', bbox: [37.5, 31.5, 49.0, 38.0], startYear: -900, endYear: -612, controlScore: 88 },
  { id: 'babylon', name: 'Babylon', nameZh: '巴比伦', bbox: [39.5, 29.5, 48.5, 36.5], startYear: -626, endYear: -539, controlScore: 90 },
  { id: 'persia', name: 'Persia', nameZh: '波斯', bbox: [34.0, 25.0, 63.0, 41.0], startYear: -550, endYear: -330, controlScore: 92 },
  { id: 'greece', name: 'Greece', nameZh: '希腊', bbox: [20.0, 30.0, 40.0, 42.0], startYear: -336, endYear: -146, controlScore: 86 },
  { id: 'rome', name: 'Rome', nameZh: '罗马', bbox: [9.0, 29.0, 40.0, 47.0], startYear: -27, endYear: 476, controlScore: 94 },
]

const empireTerritories: BibleTerritoryDTO[] = EMPIRES.map((e) => ({
  id: `empire-${e.id}`,
  name: e.name,
  nameZh: e.nameZh,
  ownerType: 'empire',
  ownerId: e.id,
  ownerName: e.nameZh,
  period: 'empire',
  startYear: e.startYear,
  endYear: e.endYear,
  controlScore: e.controlScore,
  status: 'empire',
  color: null,
  geojson: rectPolygon(...e.bbox),
  description: `${e.nameZh}帝国的大致势力范围（教学示意），影响圣经历史的列国之一。`,
}))

export const seedTribes: BibleTerritoryDTO[] = tribeTerritories
export const seedEmpires: BibleTerritoryDTO[] = empireTerritories
export const seedTerritories: BibleTerritoryDTO[] = [...tribeTerritories, ...empireTerritories]
