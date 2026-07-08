import { lineString, featureCollection, feature, point } from '../lib/geojson'
import type { BibleCampaignDTO, GeoJsonPoint } from '../domain/types'

const gideonRoute = lineString([
  [35.33, 32.48], // 俄弗拉 Ophrah（基甸家乡，出发）
  [35.36, 32.55], // 哈律泉 Spring of Harod（三百人集结）
  [35.37, 32.62], // 摩利冈下米甸大营 Midian camp
  [35.55, 32.45], // 夜袭后米甸人溃逃方向
  [35.62, 32.4], // 退向约旦河 retreat to Jordan
])

const gideonPoints = featureCollection<GeoJsonPoint, { id: string; nameZh: string; kind: string }>([
  feature(point([35.36, 32.55]), { id: 'gideon-camp', nameZh: '基甸营（哈律泉）', kind: 'camp' }),
  feature(point([35.37, 32.62]), { id: 'midian-camp', nameZh: '米甸大营（摩利冈）', kind: 'enemy' }),
  feature(point([35.62, 32.4]), { id: 'retreat', nameZh: '米甸退兵点（约旦河）', kind: 'retreat' }),
])

export const seedCampaigns: BibleCampaignDTO[] = [
  {
    id: 'gideon',
    name: 'Gideon 300 Warriors Night Attack',
    nameZh: '基甸三百勇士夜袭',
    commander: 'Gideon',
    commanderZh: '基甸',
    startYear: -1190,
    endYear: -1190,
    book: 'Judges',
    chapter: 7,
    routeGeojson: gideonRoute,
    pointsGeojson: gideonPoints,
    description:
      '神将以色列军减至三百人，夜间各执角与火把瓶子环绕米甸大营，吹角呐喊摔瓶，米甸全军惊乱自相击杀、向约旦河溃逃。彰显「得胜不在乎人多」。',
  },
]
