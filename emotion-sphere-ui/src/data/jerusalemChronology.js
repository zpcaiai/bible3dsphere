// jerusalemChronology.js — 耶路撒冷圣城变迁 + 圣殿结构 数字孪生数据
// 坐标 [lng, lat]（GeoJSON / Mapbox / MapLibre 标准）。
// ⚠ 城墙与建筑轮廓为「示意性复原」(schematic reconstruction)，用于教学呈现各时期相对范围，
//   非精确考古测绘；高度(米)为传统记载/合理估算，用于 3D fill-extrusion。

export const TEMPLE_CENTER = [35.23540, 31.77810] // 圣殿山中心（磐石圆顶附近）

// 矩形/多边形辅助：传入若干 [lng,lat] 顶点，自动闭合成 Polygon 环
function poly(coords) { const r = coords.slice(); if (r[0][0] !== r[r.length - 1][0] || r[0][1] !== r[r.length - 1][1]) r.push(r[0]); return [r] }

function feat(kind, name, coords, height, props) {
  return { type: 'Feature', properties: { kind, name, height: height || 0, ...(props || {}) }, geometry: { type: 'Polygon', coordinates: poly(coords) } }
}
function line(name, coords, props) {
  return { type: 'Feature', properties: { kind: 'wall', name, ...(props || {}) }, geometry: { type: 'LineString', coordinates: coords } }
}

// —— 各时期建筑/城墙轮廓（示意） ——
// 圣殿山平台（随时期扩大）
const PLATFORM = {
  solomon: [[35.23495,31.77860],[35.23610,31.77860],[35.23625,31.77760],[35.23510,31.77760]],
  herod:   [[35.23440,31.78010],[35.23720,31.78005],[35.23770,31.77470],[35.23500,31.77460]], // 希律大平台(近今圣殿山梯形)
}
// 圣殿主体建筑（圣所）
const TEMPLE_BUILDING = {
  solomon: [[35.23548,31.77835],[35.23578,31.77833],[35.23576,31.77805],[35.23546,31.77807]], // 第一圣殿(约30m高)
  herod:   [[35.23544,31.77840],[35.23582,31.77837],[35.23580,31.77798],[35.23542,31.77801]], // 第二圣殿希律重建(圣所约45m)
}
// 大卫城 / 俄斐勒（圣殿山以南的窄长山脊）
const CITY_OF_DAVID = [[35.23560,31.77460],[35.23660,31.77460],[35.23630,31.77040],[35.23520,31.77050]]
// 希西家扩建：西山（今犹太区/亚美尼亚区一带）
const WESTERN_HILL = [[35.22700,31.77820],[35.23500,31.77820],[35.23500,31.77150],[35.22720,31.77200]]
// 现代老城（奥斯曼城墙，1538）大致矩形
const OLD_CITY = [[35.22560,31.78230],[35.23800,31.78200],[35.23820,31.77150],[35.22570,31.77170]]

// 汲沦溪（东侧河谷，示意线）
const KIDRON = [[35.23820,31.78100],[35.23760,31.77700],[35.23700,31.77300],[35.23660,31.77000]]

export const JERU_ERAS = [
  {
    id: 'david', year: -1000, label: '大卫之城', en: "David's City",
    desc: '大卫攻取耶布斯人的锡安保障，定为京城（撒下5:6-9）。城限于圣殿山以南的窄长山脊（俄斐勒），并向亚劳拿购买禾场作将来建殿之地（撒下24:18-25）。',
    ref: '撒下5:6-9；24:18-25',
    features: [
      feat('district', '大卫城（锡安/俄斐勒）', CITY_OF_DAVID, 6, { fill: '#c98b3a' }),
      feat('threshing', '亚劳拿禾场（将来殿址）', PLATFORM.solomon, 2, { fill: '#7a6a3a', note: '大卫在此筑坛献祭，止住瘟疫；即日后圣殿所在。' }),
      line('大卫城城墙', CITY_OF_DAVID.concat([CITY_OF_DAVID[0]])),
    ],
  },
  {
    id: 'solomon', year: -960, label: '所罗门第一圣殿', en: "Solomon's Temple",
    desc: '所罗门在亚劳拿禾场（摩利亚山）建造第一圣殿，历时七年；又建王宫。圣殿山首次出现人工平台与圣所建筑。',
    ref: '王上6-8',
    features: [
      feat('district', '大卫城', CITY_OF_DAVID, 6, { fill: '#c98b3a' }),
      feat('platform', '圣殿山平台（所罗门）', PLATFORM.solomon, 8, { fill: '#9a8b5a' }),
      feat('temple', '第一圣殿（圣所）', TEMPLE_BUILDING.solomon, 30, { fill: '#f0d79b', sacred: true, note: '至圣所安放约柜；献殿时云彩充满（王上8:10-11）。' }),
      line('所罗门城墙', CITY_OF_DAVID.concat([CITY_OF_DAVID[0]])),
    ],
  },
  {
    id: 'hezekiah', year: -700, label: '希西家扩建', en: 'Hezekiah Expansion',
    desc: '面对亚述威胁，希西家向西扩城纳入「西山」，加筑「宽墙」（尼3:8 考古实证厚约7m），并开凿希西家水道引基训泉水入西罗亚池（王下20:20；代下32:30）。',
    ref: '王下20:20；代下32:2-5,30',
    features: [
      feat('district', '大卫城', CITY_OF_DAVID, 6, { fill: '#c98b3a' }),
      feat('district', '西山扩建区', WESTERN_HILL, 7, { fill: '#b07a4a' }),
      feat('platform', '圣殿山平台', PLATFORM.solomon, 8, { fill: '#9a8b5a' }),
      feat('temple', '第一圣殿', TEMPLE_BUILDING.solomon, 30, { fill: '#f0d79b', sacred: true }),
      line('宽墙（希西家）', [[35.22720,31.77820],[35.23500,31.77820]], { broad: true }),
      line('希西家水道', [[35.23640,31.77360],[35.23560,31.77140],[35.23520,31.77050]], { tunnel: true }),
    ],
  },
  {
    id: 'nehemiah', year: -445, label: '尼希米重建', en: 'Nehemiah Rebuild',
    desc: '被掳归回后，城垣荒废。尼希米五十二天内重建城墙（尼6:15），范围收缩回大卫城与圣殿山；第二圣殿（所罗巴伯所建）规模朴素，远不及第一殿的荣华。',
    ref: '尼2-6；拉3',
    features: [
      feat('district', '大卫城（重建）', CITY_OF_DAVID, 6, { fill: '#c98b3a' }),
      feat('platform', '圣殿山平台', PLATFORM.solomon, 8, { fill: '#9a8b5a' }),
      feat('temple', '第二圣殿（所罗巴伯）', TEMPLE_BUILDING.solomon, 24, { fill: '#d8c79a', sacred: true, note: '老年人见此殿想起昔日荣华而哭（拉3:12）。' }),
      line('尼希米城墙', CITY_OF_DAVID.concat([CITY_OF_DAVID[0]])),
    ],
  },
  {
    id: 'herod', year: -20, label: '希律大扩建 · 第二圣殿', en: "Herod's Temple",
    desc: '希律王大规模扩建圣殿山平台至约 480m×300m 的梯形大台（今圣殿山范围），重建华丽的第二圣殿（圣所约45m高），北建安东尼亚堡，西扩「上城」。这是耶稣时代所见的耶路撒冷。',
    ref: '约2:20；可13:1-2',
    features: [
      feat('district', '大卫城（下城）', CITY_OF_DAVID, 6, { fill: '#c98b3a' }),
      feat('district', '上城（希律富人区）', WESTERN_HILL, 10, { fill: '#a06a6a' }),
      feat('platform', '圣殿山大平台（希律）', PLATFORM.herod, 12, { fill: '#8a8b6a' }),
      feat('temple', '第二圣殿 · 希律圣所', TEMPLE_BUILDING.herod, 45, { fill: '#f5e3b0', sacred: true, note: '"将来在这里没有一块石头留在石头上"（可13:2），主后70年被罗马焚毁。' }),
      feat('fortress', '安东尼亚堡', [[35.23720,31.78030],[35.23800,31.78028],[35.23802,31.77975],[35.23722,31.77977]], 28, { fill: '#8a93a8', note: '罗马驻军要塞；传统认为彼拉多在此审问耶稣（铺华石处）。' }),
      line('希律城墙（第二/第三墙示意）', OLD_CITY.flat().length ? [[35.22560,31.78230],[35.23800,31.78200],[35.23820,31.77150],[35.23560,31.77040],[35.23520,31.77050],[35.22720,31.77200],[35.22700,31.77820],[35.22560,31.78230]] : []),
    ],
  },
  {
    id: 'modern', year: 1538, label: '现代老城', en: 'Old City Today',
    desc: '主后70年与135年城两度被毁。今日所见的老城城墙为奥斯曼苏莱曼一世于1538年所建；圣殿山上自691年起为磐石圆顶（金顶）。可作今昔对照的空间参照。',
    ref: '今日地理参照',
    features: [
      feat('district', '老城（四区）', OLD_CITY, 9, { fill: '#6b7a8a' }),
      feat('platform', '圣殿山（今 Haram）', PLATFORM.herod, 11, { fill: '#7a8b6a' }),
      feat('temple', '磐石圆顶（示意）', [[35.23520,31.77840],[35.23560,31.77840],[35.23560,31.77800],[35.23520,31.77800]], 35, { fill: '#e0c060', sacred: false, note: '691年建成的伊斯兰圣所，位于昔日圣殿山平台上。' }),
      line('奥斯曼城墙（1538）', OLD_CITY.concat([OLD_CITY[0]])),
    ],
  },
]

// —— 关键地点（点） eras 标明在哪些时期已存在 ——
export const JERU_LOCATIONS = [
  { id: 'temple-mount', name_zh: '圣殿山 / 摩利亚山', name_en: 'Temple Mount', coord: [35.23540,31.77810], eras: ['david','solomon','hezekiah','nehemiah','herod','modern'], ref: '代下3:1', note: '亚伯拉罕献以撒之摩利亚山；历代圣殿所在的圣山。' },
  { id: 'city-of-david', name_zh: '大卫城', name_en: 'City of David', coord: [35.23590,31.77250], eras: ['david','solomon','hezekiah','nehemiah','herod'], ref: '撒下5:7', note: '耶路撒冷最古老的核心，南向的窄长山脊。' },
  { id: 'gihon', name_zh: '基训泉', name_en: 'Gihon Spring', coord: [35.23660,31.77360], eras: ['david','solomon','hezekiah','nehemiah','herod'], ref: '王上1:38-39', note: '城的主要活水源；所罗门在此受膏为王。希西家凿水道由此引水。' },
  { id: 'siloam', name_zh: '西罗亚池', name_en: 'Pool of Siloam', coord: [35.23530,31.77040], eras: ['hezekiah','nehemiah','herod','modern'], ref: '约9:7', note: '希西家水道的出水口；耶稣医好生来瞎眼者，命他往西罗亚池洗。' },
  { id: 'kidron', name_zh: '汲沦溪', name_en: 'Kidron Valley', coord: [35.23740,31.77600], eras: ['david','solomon','hezekiah','nehemiah','herod','modern'], ref: '撒下15:23；约18:1', note: '城东的河谷；大卫逃避押沙龙、耶稣往客西马尼都曾过汲沦溪。' },
  { id: 'bethesda', name_zh: '毕士大池', name_en: 'Pool of Bethesda', coord: [35.23650,31.78150], eras: ['herod','modern'], ref: '约5:2-9', note: '羊门旁有五个廊子的池子；耶稣在此医好卧了三十八年的病人。' },
  { id: 'antonia', name_zh: '安东尼亚堡（铺华石）', name_en: 'Antonia Fortress', coord: [35.23760,31.78000], eras: ['herod'], ref: '约19:13', note: '罗马要塞；传统认为彼拉多在「铺华石」（厄巴大）处定耶稣的罪。' },
  { id: 'gethsemane', name_zh: '客西马尼园', name_en: 'Gethsemane', coord: [35.23980,31.77940], eras: ['herod','modern'], ref: '太26:36', note: '橄榄山脚的园子；耶稣在此恳切祷告、被卖被捕。' },
  { id: 'olives', name_zh: '橄榄山', name_en: 'Mount of Olives', coord: [35.24520,31.77850], eras: ['david','herod','modern'], ref: '亚14:4；徒1:12', note: '城东高地；耶稣升天处，预言再来时脚踏此山。' },
  { id: 'golgotha', name_zh: '各各他（髑髅地）', name_en: 'Golgotha', coord: [35.22980,31.77840], eras: ['herod','modern'], ref: '约19:17', note: '城门外的刑场；耶稣被钉十字架之处（今圣墓教堂一带）。' },
  { id: 'tomb', name_zh: '园中坟墓', name_en: 'Garden Tomb', coord: [35.22950,31.77870], eras: ['herod','modern'], ref: '约19:41-42', note: '钉十字架处附近的新坟墓；第三日空了，主复活。' },
  { id: 'caiaphas', name_zh: '该亚法的宅院', name_en: "Caiaphas' House", coord: [35.22900,31.77200], eras: ['herod'], ref: '太26:57', note: '大祭司宅；耶稣在此受公会审问，彼得三次不认主。' },
  { id: 'upper-room', name_zh: '马可楼（最后晚餐）', name_en: 'Upper Room', coord: [35.22930,31.77150], eras: ['herod'], ref: '可14:15', note: '设最后晚餐的楼房；五旬节圣灵降临亦在此处。' },
]

// —— 受难周 FPV 步行巡游（希律时期）——
export const PASSION_WEEK = [
  { day: '主日', title: '荣入圣城', coord: [35.24520,31.77850], ref: '太21:1-11', summary: '耶稣从橄榄山骑驴进城，众人将衣服与棕树枝铺在路上高呼"和散那"。' },
  { day: '周一', title: '洁净圣殿', coord: [35.23560,31.77790], ref: '可11:15-17', summary: '进入圣殿，推倒兑换银钱之人的桌子："我的殿必称为祷告的殿。"' },
  { day: '周四晚', title: '最后晚餐', coord: [35.22930,31.77150], ref: '路22:14-20', summary: '在马可楼设立圣餐："这是我的身体，为你们舍的。"' },
  { day: '周四夜', title: '客西马尼祷告与被捕', coord: [35.23980,31.77940], ref: '太26:36-50', summary: '过汲沦溪到园中祷告："不要照我的意思，只要照你的意思。"随后被犹大出卖被捕。' },
  { day: '周五凌晨', title: '该亚法宅受审', coord: [35.22900,31.77200], ref: '太26:57-68', summary: '在大祭司宅被公会审问、定为僭妄；彼得在院中三次不认主。' },
  { day: '周五晨', title: '彼拉多定罪', coord: [35.23760,31.78000], ref: '约19:13-16', summary: '在安东尼亚堡铺华石处，彼拉多将耶稣交给众人钉十字架。' },
  { day: '周五午', title: '各各他受难', coord: [35.22980,31.77840], ref: '路23:33-46', summary: '在髑髅地被钉十字架；遍地黑暗，耶稣说"成了"，气就断了。' },
  { day: '主日清晨', title: '空坟与复活', coord: [35.22950,31.77870], ref: '路24:1-6', summary: '妇女清晨到坟墓，石头已滚开："为什么在死人中找活人？他不在这里，已经复活了！"' },
]

// 取某时期的 GeoJSON（建筑面 + 城墙线分开，便于不同图层）
export function eraGeoJSON(eraId) {
  const era = JERU_ERAS.find(e => e.id === eraId) || JERU_ERAS[0]
  const polys = era.features.filter(f => f.geometry.type === 'Polygon')
  const lines = era.features.filter(f => f.geometry.type === 'LineString')
  return {
    polygons: { type: 'FeatureCollection', features: polys },
    walls: { type: 'FeatureCollection', features: lines },
  }
}

export function locationsFor(eraId) {
  return {
    type: 'FeatureCollection',
    features: JERU_LOCATIONS.filter(l => l.eras.includes(eraId)).map(l => ({
      type: 'Feature',
      properties: { id: l.id, name_zh: l.name_zh, name_en: l.name_en, ref: l.ref, note: l.note },
      geometry: { type: 'Point', coordinates: l.coord },
    })),
  }
}
