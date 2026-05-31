// 耶路撒冷的时代演变 —— 同一地点跨时代的"一地多名 + 疆域多边形"演示。
// 城墙多边形为示意性近似（环绕大卫城山脊向西、向北逐代扩展），用于展示时空切片。
// 坐标 [lng, lat]；多边形为闭合环。年份：公元前为负。

export const JERUSALEM_SLUG = 'jerusalem'
export const jerusalemPoint = [35.2345, 31.7767] // 大卫城/圣殿山一带

// 各时代城墙范围（依考古footprint近似细化；仍为示意，非测绘精度）
// 大卫城=Kidron(东)与Tyropoeon(西)两谷之间的南北向窄脊；圣殿山在其北；西山(上城/锡安)在其西。
const RING_JEBUS     = [[35.2352,31.7705],[35.2367,31.7707],[35.2370,31.7740],[35.2353,31.7742],[35.2348,31.7723],[35.2352,31.7705]]
const RING_DAVID     = [[35.2350,31.7700],[35.2368,31.7702],[35.2372,31.7745],[35.2352,31.7748],[35.2346,31.7725],[35.2350,31.7700]]
const RING_SOLOMON   = [[35.2350,31.7700],[35.2368,31.7702],[35.2375,31.7745],[35.2378,31.7785],[35.2335,31.7788],[35.2332,31.7748],[35.2346,31.7725],[35.2350,31.7700]]
const RING_HEZEKIAH  = [[35.2270,31.7700],[35.2300,31.7685],[35.2370,31.7700],[35.2380,31.7785],[35.2330,31.7795],[35.2268,31.7780],[35.2262,31.7730],[35.2270,31.7700]]
const RING_NEHEMIAH  = [[35.2348,31.7702],[35.2366,31.7704],[35.2374,31.7745],[35.2376,31.7782],[35.2336,31.7785],[35.2333,31.7748],[35.2346,31.7726],[35.2348,31.7702]]
const RING_HERODIAN  = [[35.2255,31.7700],[35.2290,31.7680],[35.2380,31.7690],[35.2400,31.7760],[35.2398,31.7810],[35.2340,31.7830],[35.2270,31.7815],[35.2250,31.7755],[35.2255,31.7700]]

// 连续时间区间覆盖 公元前2000 — 公元100
export const jerusalemEras = [
  { id:'salem',    label:'撒冷（麦基洗德时期）', name_zh:'撒冷',                 name_en:'Salem',               start:-2000, end:-1400, ref:'创14:18', note:'至高神的祭司、撒冷王麦基洗德带着饼酒迎接亚伯兰。', polygon:RING_JEBUS },
  { id:'jebus',    label:'耶布斯（士师时期）',   name_zh:'耶布斯',               name_en:'Jebus',               start:-1400, end:-1004, ref:'士19:10', note:'耶布斯人居住的坚固城，以色列人未能赶出他们。', polygon:RING_JEBUS },
  { id:'david',    label:'大卫城（联合王国）',   name_zh:'大卫城',               name_en:'City of David',       start:-1004, end:-960,  ref:'撒下5:6-9', note:'大卫攻取锡安的保障，定为京城，称"大卫的城"。', polygon:RING_DAVID },
  { id:'solomon',  label:'所罗门的耶路撒冷',     name_zh:'耶路撒冷（所罗门）',   name_en:'Jerusalem',           start:-960,  end:-700,  ref:'王上6:1', note:'所罗门建造圣殿，城向北扩展至圣殿山。', polygon:RING_SOLOMON },
  { id:'hezekiah', label:'希西家扩建（犹大王国）', name_zh:'耶路撒冷（希西家）', name_en:'Jerusalem',           start:-700,  end:-586,  ref:'代下32:5', note:'希西家修筑"宽墙"，城扩展至西山，备战亚述。', polygon:RING_HEZEKIAH },
  { id:'nehemiah', label:'归回时期（尼希米重建）', name_zh:'耶路撒冷（尼希米）', name_en:'Jerusalem',           start:-586,  end:-20,   ref:'尼6:15', note:'公元前586年被巴比伦焚毁；归回后尼希米52天重建城墙。', polygon:RING_NEHEMIAH },
  { id:'herodian', label:'新约时期（希律扩建）', name_zh:'耶路撒冷（新约）',     name_en:'Jerusalem',           start:-20,   end:100,   ref:'路2:22', note:'希律大幅扩建圣殿与城区，即福音书中的耶路撒冷。', polygon:RING_HERODIAN },
]

export function eraForYear(year) {
  return jerusalemEras.find((e) => year >= e.start && year < e.end) || jerusalemEras[jerusalemEras.length - 1]
}

// 耶路撒冷关键地标（带时效性；随年份出现/消失）。坐标 [lng, lat]，示意位置。
export const jerusalemLandmarks = [
  { id:'gihon',   slug:'gihon-spring',   name_zh:'基训泉',   name_en:'Gihon Spring',   lng:35.2365, lat:31.7735, start:-2000, end:100,  note:'耶路撒冷的主要活水源头，所罗门曾在此受膏立王（王上1:38-39）。' },
  { id:'davidpal',slug:'davids-palace',  name_zh:'大卫王宫',  name_en:"David's Palace",  lng:35.2356, lat:31.7745, start:-1004, end:-586, note:'大卫城北端的宫殿区，大卫定都于此（撒下5:11）。' },
  { id:'temple',  slug:'temple-mount',   name_zh:'圣殿山',   name_en:'Temple Mount',   lng:35.2354, lat:31.7780, start:-960,  end:100,  note:'所罗门圣殿与第二圣殿的所在；信仰与敬拜的中心（王上6）。' },
  { id:'broadwall',slug:'broad-wall',    name_zh:'宽墙',     name_en:'Broad Wall',     lng:35.2300, lat:31.7765, start:-700,  end:-586, note:'希西家为防御亚述而加筑的宽厚城墙（赛22:10；尼3:8）。' },
  { id:'siloam',  slug:'pool-of-siloam', name_zh:'西罗亚池', name_en:'Pool of Siloam', lng:35.2354, lat:31.7705, start:-700,  end:100,  note:'希西家凿水道把基训泉水引入城内的水池（王下20:20；约9:7）。' },
]

export const landmarkNoteBySlug = Object.fromEntries(jerusalemLandmarks.map((l) => [l.slug, l.note]))

export function landmarksFCForYear(year) {
  return {
    type: 'FeatureCollection',
    features: jerusalemLandmarks.filter((l) => year >= l.start && year < l.end).map((l) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [l.lng, l.lat] },
      properties: { slug: l.slug, name_zh: l.name_zh, name_en: l.name_en },
    })),
  }
}
