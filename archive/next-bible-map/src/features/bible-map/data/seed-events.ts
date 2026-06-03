import type { BibleMapEventDTO } from '../domain/types'

// 士师时代事件（年代为近似教学值）。category: 'judge'。
export const seedEvents: BibleMapEventDTO[] = [
  {
    id: 'judge-othniel', title: 'Othniel', titleZh: '俄陀聂', category: 'judge',
    book: 'Judges', chapter: 3, startYear: -1370, endYear: -1330,
    locationName: '南地 / Debir', latitude: 31.4, longitude: 34.9,
    geojson: null,
    description: '以色列受古珊利萨田欺压，迦勒的侄子俄陀聂被神兴起拯救以色列。',
    spiritualMeaning: '神听见百姓哀求，兴起拯救者；得救始于回转呼求神。',
  },
  {
    id: 'judge-ehud', title: 'Ehud', titleZh: '以笏', category: 'judge',
    book: 'Judges', chapter: 3, startYear: -1300, endYear: -1260,
    locationName: '耶利哥 / 摩押', latitude: 31.87, longitude: 35.5,
    geojson: null,
    description: '左手便利的以笏刺杀摩押王伊矶伦，使以色列脱离摩押的辖制。',
    spiritualMeaning: '神能使用被人轻看的「不合常规」之人成就拯救。',
  },
  {
    id: 'judge-deborah', title: 'Deborah and Barak', titleZh: '底波拉与巴拉', category: 'judge',
    book: 'Judges', chapter: 4, startYear: -1200, endYear: -1160,
    locationName: '他泊山 / 基顺河', latitude: 32.69, longitude: 35.39,
    geojson: null,
    description: '女先知底波拉激励巴拉，在基顺河边大败迦南王耶宾的元帅西西拉。',
    spiritualMeaning: '神不轻看性别与软弱，信心顺服带来全地的安息。',
  },
  {
    id: 'judge-gideon', title: 'Gideon', titleZh: '基甸', category: 'judge',
    book: 'Judges', chapter: 7, startYear: -1190, endYear: -1150,
    locationName: 'Jezreel Valley / 耶斯列平原', latitude: 32.6, longitude: 35.3,
    geojson: null,
    description: '米甸人压制以色列，基甸率三百人夜袭。',
    spiritualMeaning: '人的软弱中显出神的拯救。',
  },
  {
    id: 'judge-jephthah', title: 'Jephthah', titleZh: '耶弗他', category: 'judge',
    book: 'Judges', chapter: 11, startYear: -1100, endYear: -1070,
    locationName: '基列 / 米斯巴', latitude: 32.0, longitude: 35.7,
    geojson: null,
    description: '被弟兄赶出的耶弗他被基列长老请回，击败亚扪人，却因轻率许愿付上代价。',
    spiritualMeaning: '神能高举被弃绝的人，但向神许愿当谨慎敬畏。',
  },
  {
    id: 'judge-samson', title: 'Samson', titleZh: '参孙', category: 'judge',
    book: 'Judges', chapter: 13, startYear: -1075, endYear: -1055,
    locationName: '梭烈谷 / 非利士边境', latitude: 31.7, longitude: 34.9,
    geojson: null,
    description: '拿细耳人参孙力大无穷，独自与非利士人争战，临终同归于尽拯救以色列。',
    spiritualMeaning: '恩赐若离弃分别为圣终必失去能力，神的恩典仍在悔改中成就。',
  },
]
