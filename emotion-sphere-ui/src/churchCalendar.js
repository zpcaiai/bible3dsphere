// 教会历 / 属灵节期（纯计算，含可移动节期：复活节用 Meeus/Jones/Butcher 算法）
function easter(year) {
  const a = year % 19, b = Math.floor(year / 100), c = year % 100
  const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25)
  const g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30
  const i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7
  const m = Math.floor((a + 11 * h + 22 * l) / 451)
  const month = Math.floor((h + l - 7 * m + 114) / 31)
  const day = ((h + l - 7 * m + 114) % 31) + 1
  return new Date(year, month - 1, day)
}
function addDays(date, n) { const d = new Date(date); d.setDate(d.getDate() + n); return d }
function adventStart(year) {
  const d = new Date(year, 11, 24)            // Dec 24
  while (d.getDay() !== 0) d.setDate(d.getDate() - 1)  // Sunday on/before
  return addDays(d, -21)                       // 4 Sundays before Christmas
}
function ymd(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()) }

const SEASONS = {
  advent:    { name: '将临期', color: '#8b5cf6', theme: '在黑暗中等候那将要来的光。预备你的心，迎接基督的降临。', scripture: { ref: '赛9:6', text: '因有一婴孩为我们而生……他名称为奇妙策士、全能的神。' } },
  christmas: { name: '圣诞期', color: '#ffd43b', theme: '道成了肉身，住在我们中间。神竟与我们同在。', scripture: { ref: '约1:14', text: '道成了肉身，住在我们中间，充充满满地有恩典有真理。' } },
  lent:      { name: '大斋期', color: '#7c3aed', theme: '悔改、舍己、节制——预备自己默想十字架的爱。', scripture: { ref: '珥2:13', text: '你们要撕裂心肠，不撕裂衣服，归向耶和华你们的神。' } },
  holyweek:  { name: '受难周', color: '#ef4444', theme: '与主一同走向十字架，默想他为你受的苦。', scripture: { ref: '赛53:5', text: '哪知他为我们的过犯受害，为我们的罪孽压伤……因他受的鞭伤，我们得医治。' } },
  easter:    { name: '复活期', color: '#fbbf24', theme: '基督已经复活了！死亡被吞灭，盼望与新生命临到。', scripture: { ref: '林前15:20', text: '但基督已经从死里复活，成为睡了之人初熟的果子。' } },
  pentecost: { name: '五旬节 · 常年期', color: '#22c55e', theme: '圣灵降临，赐下能力。在日常中作主的见证，结出圣灵的果子。', scripture: { ref: '徒1:8', text: '但圣灵降临在你们身上，你们就必得着能力……作我的见证。' } },
  ordinary:  { name: '常年期', color: '#34c759', theme: '在平常的日子里跟随主，让信心在忠心的小事中成长。', scripture: { ref: '太4:19', text: '来跟从我，我要叫你们得人如得鱼一样。' } },
}

export function currentSeason(today = new Date()) {
  const t = ymd(today), y = t.getFullYear()
  const e = easter(y), ash = addDays(e, -46), hw = addDays(e, -7), pent = addDays(e, 49)
  const adv = adventStart(y)
  let key
  if (t.getMonth() === 0 && t.getDate() <= 5) key = 'christmas'
  else if (t >= adv && t <= new Date(y, 11, 24)) key = 'advent'
  else if (t >= new Date(y, 11, 25)) key = 'christmas'
  else if (t >= hw && t < e) key = 'holyweek'
  else if (t >= ash && t < hw) key = 'lent'
  else if (t >= e && t <= pent) key = 'easter'
  else if (t > pent && t < adv) key = 'pentecost'
  else key = 'ordinary'
  return { key, ...SEASONS[key] }
}
