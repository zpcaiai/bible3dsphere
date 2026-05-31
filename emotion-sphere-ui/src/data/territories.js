// 政治疆域演变：十二支派分地（约书亚）vs 联合王国（大卫·所罗门）。
// 同一片土地在不同时代归属剧烈变化——用于演示时空多对多 + 拓扑关系。
// 疆域多边形为示意性近似（bbox 矩形），非精确考古边界。坐标 [lng, lat]。

const ringFromBbox = ([w, s, e, n]) => [[w, s], [e, s], [e, n], [w, n], [w, s]]

// 十二支派（利未支派无地业，只有城邑，故不含多边形）
const TRIBE_DEFS = [
  ['judah','犹大','Judah',[34.85,31.00,35.40,31.65],'#fbbf24'],
  ['simeon','西缅','Simeon',[34.55,30.95,35.00,31.30],'#f59e0b'],
  ['benjamin','便雅悯','Benjamin',[35.10,31.70,35.45,31.95],'#fb7185'],
  ['dan','但','Dan',[34.80,31.85,35.10,32.10],'#f472b6'],
  ['ephraim','以法莲','Ephraim',[34.95,31.95,35.40,32.25],'#34d399'],
  ['manasseh-west','玛拿西（西）','Manasseh (W)',[34.95,32.25,35.45,32.65],'#10b981'],
  ['issachar','以萨迦','Issachar',[35.20,32.50,35.60,32.78],'#22d3ee'],
  ['zebulun','西布伦','Zebulun',[35.10,32.65,35.45,32.95],'#38bdf8'],
  ['asher','亚设','Asher',[35.00,32.85,35.30,33.15],'#818cf8'],
  ['naphtali','拿弗他利','Naphtali',[35.35,32.85,35.65,33.30],'#a78bfa'],
  ['reuben','流便','Reuben',[35.50,31.30,35.95,31.85],'#c084fc'],
  ['gad','迦得','Gad',[35.55,31.85,35.95,32.40],'#e879f9'],
  ['manasseh-east','玛拿西（东·半支派）','Manasseh (E)',[35.65,32.40,36.10,32.90],'#2dd4bf'],
]

export const tribes = TRIBE_DEFS.map(([id, name_zh, name_en, bbox, color]) => ({
  id, slug: `tribe-${id}`, name_zh, name_en, color, bbox, polygon: ringFromBbox(bbox),
}))

// 联合王国（一个大疆域）
export const unitedKingdom = {
  id: 'united-kingdom', slug: 'united-kingdom', name_zh: '以色列联合王国', name_en: 'United Kingdom of Israel',
  color: '#ffd700', bbox: [34.55, 30.80, 36.15, 33.35], polygon: ringFromBbox([34.55, 30.80, 36.15, 33.35]),
}

// 分裂王国：北国以色列（都撒玛利亚）与南国犹大（都耶路撒冷）
export const israelNorth = {
  id: 'israel-north', slug: 'israel-north', name_zh: '北国以色列', name_en: 'Kingdom of Israel',
  color: '#60a5fa', start: -930, end: -722,
  bbox: [34.90, 31.97, 36.10, 33.35], polygon: ringFromBbox([34.90, 31.97, 36.10, 33.35]),
}
export const judahSouth = {
  id: 'judah-south', slug: 'judah-south', name_zh: '南国犹大', name_en: 'Kingdom of Judah',
  color: '#f87171', start: -930, end: -586,
  bbox: [34.60, 30.80, 35.55, 31.97], polygon: ringFromBbox([34.60, 30.80, 35.55, 31.97]),
}
export const dividedRegions = [israelNorth, judahSouth]

// 两个时代
export const territoryEras = [
  { id: 'tribes',      label: '支派分地（约书亚分地）', start: -1400, end: -1004, ref: '书13-19',     note: '约书亚带领以色列人得地为业，按支派抽签分配迦南，十二支派各得疆界。' },
  { id: 'kingdom',     label: '联合王国（大卫·所罗门）', start: -1004, end: -930,  ref: '撒下5; 王上4', note: '扫罗、大卫、所罗门统一以色列；大卫定都耶路撒冷，疆域达到鼎盛。' },
  { id: 'divided',     label: '分裂王国（南北分立）',   start: -930,  end: -722,  ref: '王上12',      note: '所罗门死后王国分裂：北国以色列（都撒玛利亚，十支派）与南国犹大（都耶路撒冷，犹大与便雅悯）。' },
  { id: 'judah-alone', label: '独存的犹大（北国已亡）', start: -722,  end: -586,  ref: '王下17:6',    note: '公元前722年北国以色列被亚述所灭、人民被掳；仅余南国犹大延续至公元前586年被巴比伦所灭。' },
]

// 某年有效的疆域要素（本地兜底用）
export function regionsForYear(year) {
  if (year >= -722) return [judahSouth]                  // 北国已亡，仅余犹大
  if (year >= -930) return [israelNorth, judahSouth]     // 分裂王国
  if (year >= -1004) return [unitedKingdom]              // 联合王国
  return tribes                                          // 支派分地
}

export const colorBySlug = Object.fromEntries([
  ...tribes.map((t) => [t.slug, t.color]),
  [unitedKingdom.slug, unitedKingdom.color],
  [israelNorth.slug, israelNorth.color],
  [judahSouth.slug, judahSouth.color],
])

export function regionsFCForYear(year) {
  return {
    type: 'FeatureCollection',
    features: regionsForYear(year).map((r) => ({
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [r.polygon] },
      properties: { slug: r.slug, name_zh: r.name_zh, name_en: r.name_en },
    })),
  }
}
