import { rectPolygon } from '../lib/geojson'
import type { GeoJsonPolygon } from '../domain/types'

export type TempleStructureKind = 'wall' | 'platform' | 'temple'

export interface TempleStructure {
  kind: TempleStructureKind
  height: number // 米（示意）
  polygon: GeoJsonPolygon
}
export interface TempleEra {
  id: string
  label: string
  year: number // 该时代起始（公元前为负）
  note: string
  structures: TempleStructure[]
}

const wall = (b: [number, number, number, number], h: number): TempleStructure => ({ kind: 'wall', height: h, polygon: rectPolygon(...b) })
const platform = (b: [number, number, number, number], h: number): TempleStructure => ({ kind: 'platform', height: h, polygon: rectPolygon(...b) })
const temple = (b: [number, number, number, number], h: number): TempleStructure => ({ kind: 'temple', height: h, polygon: rectPolygon(...b) })

// 圣殿山一带（示意坐标，约 35.234–35.240E, 31.770–31.781N）
export const TEMPLE_CENTER: [number, number] = [35.2354, 31.778]

export const templeEras: TempleEra[] = [
  {
    id: 'david', label: '大卫购阿劳拿禾场', year: -1004,
    note: '大卫在耶布斯人阿劳拿的禾场筑坛献祭（撒下24:18-25），此处日后成为圣殿所在。城仍限于南面的大卫城窄脊。',
    structures: [wall([35.2352, 31.77, 35.2372, 31.7745], 6)],
  },
  {
    id: 'solomon', label: '所罗门第一圣殿', year: -960,
    note: '所罗门历七年建成第一圣殿（王上6），城向北扩展纳入圣殿山，敬拜中心确立。',
    structures: [
      wall([35.235, 31.77, 35.2378, 31.7785], 8),
      platform([35.2345, 31.776, 35.2378, 31.7795], 12),
      temple([35.2352, 31.7772, 35.2366, 31.7786], 22),
    ],
  },
  {
    id: 'hezekiah', label: '希西家扩城', year: -700,
    note: '希西家修筑「宽墙」、开凿水道备战亚述，城扩展至西山，城墙更高厚（代下32:5）。',
    structures: [
      wall([35.23, 31.7695, 35.2385, 31.78], 11),
      platform([35.2345, 31.776, 35.2378, 31.7795], 12),
      temple([35.2352, 31.7772, 35.2366, 31.7786], 22),
    ],
  },
  {
    id: 'destroyed', label: '圣殿被焚（被掳）', year: -586,
    note: '公元前586年巴比伦尼布甲尼撒焚毁圣殿与城墙，犹大被掳（王下25:8-10）。圣殿山只余残垣。',
    structures: [wall([35.233, 31.77, 35.2378, 31.779], 2)],
  },
  {
    id: 'second', label: '第二圣殿（归回重建）', year: -516,
    note: '归回的余民在所罗巴伯带领下重建圣殿（拉6:15），规模虽不及前殿，敬拜得以恢复。',
    structures: [
      wall([35.233, 31.77, 35.2382, 31.7795], 9),
      platform([35.2342, 31.7758, 35.2382, 31.7798], 12),
      temple([35.2352, 31.7772, 35.2366, 31.7786], 20),
    ],
  },
  {
    id: 'herod', label: '希律大扩建（新约时期）', year: -20,
    note: '希律大幅扩建圣殿山平台与殿宇，金碧辉煌，即福音书中的耶路撒冷圣殿；公元70年毁于罗马。',
    structures: [
      wall([35.23, 31.769, 35.24, 31.7815], 14),
      platform([35.233, 31.7755, 35.2392, 31.7808], 18),
      temple([35.235, 31.7775, 35.2368, 31.7792], 45),
    ],
  },
]

export function templeEraForYear(year: number): TempleEra {
  let chosen = templeEras[0]
  for (const e of templeEras) {
    if (year >= e.year) chosen = e
  }
  return chosen
}

export const TEMPLE_COLORS: Record<TempleStructureKind, string> = {
  wall: '#a16207',
  platform: '#ca8a04',
  temple: '#fcd34d',
}
