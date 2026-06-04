// templeStructure.js — 所罗门第一圣殿精细结构（王上6-7；代下3-4）
// 用于 Mapbox GL v3 / MapLibre GL v1 的 fill-extrusion（base/height 单位米）。
// 以圣殿山真实坐标为原点、殿门朝东（面向橄榄山，符合历史方位）；1肘≈0.45m，按比例。
// 几何为教学示意复原，尺寸取经文记载。
import { TEMPLE_CENTER } from './jerusalemChronology'

const CU = 0.45                               // 1肘 ≈ 0.45 米
const LAT0 = TEMPLE_CENTER[1]
const LNG0 = TEMPLE_CENTER[0]
const M_LAT = 1 / 111320
const M_LNG = 1 / (111320 * Math.cos((LAT0 * Math.PI) / 180))

// x=向东米数, z=向北米数 → [lng,lat]
const pt = (x, z) => [LNG0 + x * M_LNG, LAT0 + z * M_LAT]
// 以肘为单位的矩形/圆（中心 cx,cz，宽w(东西) 深d(南北)）
function rectC(cx, cz, w, d) {
  const x = cx * CU, z = cz * CU, hw = (w * CU) / 2, hd = (d * CU) / 2
  return [[pt(x - hw, z - hd), pt(x + hw, z - hd), pt(x + hw, z + hd), pt(x - hw, z + hd), pt(x - hw, z - hd)]]
}
function circleC(cx, cz, r, n = 16) {
  const x = cx * CU, z = cz * CU, rm = r * CU
  const ring = []
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * 2 * Math.PI
    ring.push(pt(x + rm * Math.cos(a), z + rm * Math.sin(a)))
  }
  return [ring]
}
// 高度（肘→米）
const H = (c) => c * CU

function F(id, color, coords, baseC, heightC, cut) {
  return {
    type: 'Feature',
    properties: { id, color, base: H(baseC), height: H(heightC), cut: cut ? 1 : 0 },
    geometry: { type: 'Polygon', coordinates: coords },
  }
}

// ── 部件几何（坐标轴：x 东(+)/西(−)，z 北(+)/南(−)，单位肘）──
// 殿身内部：至圣所 x∈[-50,-30]，圣所 x∈[-30,10]，墙厚2；廊子 x∈[12,22]；门朝东(+x)
const features = []

// 内院（祭司院）台基
features.push(F('court', '#8d7f63', rectC(5, 0, 190, 110), 0, 1))
// 殿墙（凿成的石头，王上6:7）
features.push(F('walls', '#cfc5b0', rectC(-51, 0, 2, 24), 0, 30))            // 西墙
features.push(F('walls', '#cfc5b0', rectC(-20, 11, 64, 2), 0, 30))           // 北墙
features.push(F('walls', '#cfc5b0', rectC(-20, -11, 64, 2), 0, 30, true))    // 南墙（剖视隐藏）
features.push(F('walls', '#cfc5b0', rectC(11, 8.5, 2, 7), 0, 30))            // 东墙北段
features.push(F('walls', '#cfc5b0', rectC(11, -8.5, 2, 7), 0, 30))           // 东墙南段
features.push(F('walls', '#cfc5b0', rectC(11, 0, 2, 10), 20, 30))            // 门楣
// 幔子/隔断（圣所↔至圣所，代下3:14）
features.push(F('veil', '#5a4a8a', rectC(-30, 0, 0.8, 20), 0, 30))
// 殿顶（香柏木，王上6:9）
features.push(F('roof', '#7a5c3a', rectC(-20, 0, 68, 28), 30, 32, true))
// 廊子（王上6:3）
features.push(F('porch', '#cfc5b0', rectC(17, 11, 10, 2), 0, 30))
features.push(F('porch', '#cfc5b0', rectC(17, -11, 10, 2), 0, 30, true))
features.push(F('roof', '#7a5c3a', rectC(17, 0, 12, 28), 30, 32, true))
// 铜柱 雅斤(南)/波阿斯(北)（王上7:15-22）
features.push(F('jachin', '#b87333', circleC(24, -7, 1.9), 0, 18))
features.push(F('jachin', '#a8632a', circleC(24, -7, 2.5), 18, 23))
features.push(F('boaz', '#b87333', circleC(24, 7, 1.9), 0, 18))
features.push(F('boaz', '#a8632a', circleC(24, 7, 2.5), 18, 23))
// 三层旁屋（王上6:5-8）
features.push(F('chambers', '#bfae90', rectC(-20, 14, 64, 4), 0, 15))
features.push(F('chambers', '#bfae90', rectC(-20, -14, 64, 4), 0, 15, true))
features.push(F('chambers', '#bfae90', rectC(-54.5, 0, 5, 32), 0, 15))
// 铜祭坛（代下4:1）
features.push(F('altar', '#a8642a', rectC(45, 0, 20, 20), 0, 10))
// 铜海＋牛座（王上7:23-26,39 置于殿东南）
features.push(F('sea-base', '#8a5a2a', circleC(40, -25, 3), 0, 2.5))
features.push(F('sea', '#b87333', circleC(40, -25, 5), 2.5, 7.5))
// 至圣所内：约柜 + 基路伯（出25:10-22；王上6:23-28）
features.push(F('ark', '#e8c050', rectC(-40, 0, 2.5, 1.5), 0, 1.5))
features.push(F('cherubim', '#d8b040', rectC(-40, 4, 1.5, 1.5), 0, 10))
features.push(F('cherubim', '#d8b040', rectC(-40, -4, 1.5, 1.5), 0, 10))
features.push(F('cherubim', '#d8b040', rectC(-40, 0, 4, 18), 8, 9))          // 翅膀相接、达于两墙
// 圣所内：金香坛（王上6:22）＋金灯台×10（王上7:49）＋陈设饼桌×10（代下4:8）
features.push(F('incense', '#e8c050', rectC(-28, 0, 1, 1), 0, 2))
for (let i = 0; i < 5; i++) {
  const x = -26 + i * 6
  features.push(F('lampstand', '#f0d060', circleC(x, 6, 0.5, 10), 0, 3))
  features.push(F('lampstand', '#f0d060', circleC(x, -6, 0.5, 10), 0, 3))
  features.push(F('table', '#c8a060', rectC(x + 3, 3, 2, 1.2), 0, 1.5))
  features.push(F('table', '#c8a060', rectC(x + 3, -3, 2, 1.2), 0, 1.5))
}

export const TEMPLE_GEOJSON = { type: 'FeatureCollection', features }

// ── 部件资料（点击展示）──
export const TEMPLE_PARTS = {
  court:     { name: '内院（祭司院）', ref: '王上6:36', dims: '三层凿成的石头、一层香柏木围成', desc: '祭司供职之处；铜祭坛与铜海设于此院，百姓在外院敬拜。' },
  walls:     { name: '殿墙', ref: '王上6:7', dims: '殿身长60肘×宽20肘×高30肘(约27×9×13.5米)，墙厚约2肘', desc: '建殿用的是山中凿成的石头，建殿时锤子斧子并别样铁器的响声都没有听见——安静中成圣工。' },
  veil:      { name: '幔子（隔断）', ref: '代下3:14', dims: '蓝色紫色朱红色线和细麻织成，绣上基路伯', desc: '分隔圣所与至圣所。主受难时圣殿幔子从上到下裂为两半（太27:51），开了又新又活的路。' },
  roof:      { name: '殿顶', ref: '王上6:9', dims: '香柏木栋梁与望板遮盖', desc: '殿顶以香柏木建造。点「剖视」可揭开殿顶察看圣所与至圣所内部。' },
  porch:     { name: '廊子', ref: '王上6:3', dims: '长20肘×深10肘(约9×4.5米)', desc: '殿前的门廊，入殿必经之处，朝东面向橄榄山。' },
  jachin:    { name: '铜柱·雅斤（南）', ref: '王上7:15-22', dims: '高18肘＋柱顶5肘(共约10.4米)，围12肘', desc: '"雅斤"意为「他必坚立」。户兰所铸两铜柱立于廊前，柱顶有百合花与石榴网子装饰。' },
  boaz:      { name: '铜柱·波阿斯（北）', ref: '王上7:21', dims: '高18肘＋柱顶5肘，围12肘', desc: '"波阿斯"意为「在他有能力」。与雅斤一同见证：殿的坚立在乎耶和华。' },
  chambers:  { name: '三层旁屋', ref: '王上6:5-8', dims: '下层宽5肘、中层6肘、上层7肘，每层高5肘', desc: '环绕殿墙的库房，收藏圣殿器物与奉献；旋螺梯上到中层与上层。' },
  altar:     { name: '铜祭坛', ref: '代下4:1', dims: '长20肘×宽20肘×高10肘(约9×9×4.5米)', desc: '献燔祭之坛——进殿事奉先经祭坛：没有流血的代赎，就不能亲近神。' },
  sea:       { name: '铜海', ref: '王上7:23-26', dims: '径10肘、高5肘、围30肘，容2000罢特，立于12铜牛之上', desc: '祭司供职前在此洗濯，预表洁净；置于殿的东南。' },
  'sea-base':{ name: '十二铜牛座', ref: '王上7:25', dims: '三向北、三向西、三向南、三向东', desc: '十二只铜牛驮着铜海，牛尾向内，或喻十二支派共擎洁净之恩。' },
  ark:       { name: '约柜', ref: '出25:10-22；王上8:6-9', dims: '长2.5肘×宽1.5肘×高1.5肘，皂荚木包精金', desc: '至圣所唯一的家具。内有两块法版；柜上施恩座是神与人相会之处。' },
  cherubim:  { name: '基路伯', ref: '王上6:23-28', dims: '橄榄木贴金，高10肘，翅膀各展5肘，彼此相接又达两墙', desc: '两个巨型基路伯张翼遮掩约柜，象征神荣耀的守护与同在。' },
  incense:   { name: '金香坛', ref: '王上6:22；出30:1-8', dims: '1肘见方、高2肘，贴精金', desc: '立于幔子前，早晚烧香——圣徒的祈祷如香升到神面前（启8:3-4）。' },
  lampstand: { name: '金灯台（共十个）', ref: '王上7:49', dims: '精金灯台，右五个、左五个', desc: '圣所内唯一的光源，长明不灭——预表那真光，照亮一切生在世上的人。' },
  table:     { name: '陈设饼桌（共十张）', ref: '代下4:8；利24:5-9', dims: '桌上常摆十二个陈设饼，每安息日更换', desc: '十二个饼代表十二支派常在神面前——主说：我就是生命的粮。' },
}

// 主要部件 DOM 标注位置（米坐标→经纬度）
export const TEMPLE_LABELS = [
  { id: 'mostholy', name: '至圣所', coord: pt(-40 * CU, 0) },
  { id: 'holy',     name: '圣所',   coord: pt(-10 * CU, 0) },
  { id: 'porch',    name: '廊子',   coord: pt(17 * CU, 0) },
  { id: 'jachin',   name: '雅斤',   coord: pt(24 * CU, -7 * CU) },
  { id: 'boaz',     name: '波阿斯', coord: pt(24 * CU, 7 * CU) },
  { id: 'altar',    name: '铜祭坛', coord: pt(45 * CU, 0) },
  { id: 'sea',      name: '铜海',   coord: pt(40 * CU, -25 * CU) },
]
// 至圣所/圣所作为可点信息（无独立几何，与墙体共享空间）
TEMPLE_PARTS.mostholy = { name: '至圣所（内殿）', ref: '王上6:19-20；利16', dims: '长宽高各20肘(约9米)的精金立方', desc: '安放约柜之处，神荣耀同在的居所；唯大祭司每年赎罪日带血进入一次。新约里幔子已裂，信徒可坦然进入至圣所（来10:19-20）。' }
TEMPLE_PARTS.holy = { name: '圣所（外殿）', ref: '王上6:17', dims: '长40肘×宽20肘×高30肘', desc: '祭司每日供职之处：点灯、烧香、更换陈设饼——灯台、香坛、饼桌各有属灵预表。' }

// 进殿相机
export const TEMPLE_CAMERA = { center: pt(-6, -3), zoom: 18.35, pitch: 66, bearing: 18 }
