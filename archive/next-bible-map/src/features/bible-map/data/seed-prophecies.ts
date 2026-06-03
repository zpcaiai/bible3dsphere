import type { BibleProphecyDTO } from '../domain/types'

// 先知预言（射线由耶路撒冷指向受审判/应许的列国）。年代为近似教学值。
export const seedProphecies: BibleProphecyDTO[] = [
  {
    id: 'isaiah-13-babylon', book: 'Isaiah', chapterStart: 13, chapterEnd: 14,
    targetNation: 'Babylon', targetNationZh: '巴比伦', prophecyType: 'judgment',
    startYear: -740, fulfillmentYear: -539,
    sourceLocation: 'Jerusalem', targetLatitude: 32.54, targetLongitude: 44.42,
    description: '以赛亚预言巴比伦必倾覆，如所多玛蛾摩拉，永无人烟。',
    fulfillmentDescription: '公元前539年波斯王古列攻取巴比伦，帝国终告衰亡。',
  },
  {
    id: 'isaiah-15-moab', book: 'Isaiah', chapterStart: 15, chapterEnd: 16,
    targetNation: 'Moab', targetNationZh: '摩押', prophecyType: 'judgment',
    startYear: -730, fulfillmentYear: null,
    sourceLocation: 'Jerusalem', targetLatitude: 31.5, targetLongitude: 35.78,
    description: '论摩押的默示：一夜之间，摩押的城邑荒废败落，举国哀号。',
    fulfillmentDescription: null,
  },
  {
    id: 'isaiah-19-egypt', book: 'Isaiah', chapterStart: 19, chapterEnd: null,
    targetNation: 'Egypt', targetNationZh: '埃及', prophecyType: 'judgment',
    startYear: -720, fulfillmentYear: null,
    sourceLocation: 'Jerusalem', targetLatitude: 30.05, targetLongitude: 31.25,
    description: '论埃及：耶和华使埃及内乱、河水干涸；末了埃及与亚述将一同敬拜神。',
    fulfillmentDescription: null,
  },
  {
    id: 'ezekiel-26-tyre', book: 'Ezekiel', chapterStart: 26, chapterEnd: 28,
    targetNation: 'Tyre', targetNationZh: '推罗', prophecyType: 'judgment',
    startYear: -586, fulfillmentYear: -332,
    sourceLocation: 'Jerusalem', targetLatitude: 33.27, targetLongitude: 35.2,
    description: '以西结预言推罗必被列国攻破、刮净如净光的磐石，渔人晒网之处。',
    fulfillmentDescription: '巴比伦围困十三年，后亚历山大于公元前332年填海攻破推罗岛城。',
  },
  {
    id: 'nahum-nineveh', book: 'Nahum', chapterStart: 1, chapterEnd: 3,
    targetNation: 'Nineveh', targetNationZh: '尼尼微', prophecyType: 'judgment',
    startYear: -660, fulfillmentYear: -612,
    sourceLocation: 'Jerusalem', targetLatitude: 36.36, targetLongitude: 43.15,
    description: '那鸿预言亚述京城尼尼微必被洪水与刀剑倾覆，永远荒凉。',
    fulfillmentDescription: '公元前612年巴比伦与玛代联军攻陷尼尼微，亚述帝国崩溃。',
  },
  {
    id: 'jeremiah-46-egypt', book: 'Jeremiah', chapterStart: 46, chapterEnd: null,
    targetNation: 'Egypt', targetNationZh: '埃及', prophecyType: 'judgment',
    startYear: -605, fulfillmentYear: -568,
    sourceLocation: 'Jerusalem', targetLatitude: 30.05, targetLongitude: 31.25,
    description: '耶利米论埃及法老尼哥的军队必在伯拉河边迦基米施败于巴比伦。',
    fulfillmentDescription: '公元前605年迦基米施之役，尼布甲尼撒大败埃及军。',
  },
]
