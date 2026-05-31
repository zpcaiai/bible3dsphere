// MapScenes.jsx — 内联 SVG 插图场景库（离线、零依赖）
// 每个地点据 point.scene 或关键词自动匹配一幅主题插图。
// 用法：<MapScene scene={resolveScene(point, mapId)} color="#e8b04b" />

// 关键词 → 场景。顺序敏感（先匹配更具体的）。
const RULES = [
  [/复活|空了|坟墓里没有|不在这里/, 'tomb'],
  [/十字架|各各他|钉|受难|被钉/, 'cross'],
  [/铜蛇|火蛇|蛇/, 'serpent'],
  [/红海|海水分开|过海|分开成垒|约旦河水/, 'sea'],
  [/十诫|律法|诫命|立约|西奈|何烈山领/, 'tablets'],
  [/圣殿|建殿|献殿|殿宇|会幕|至圣所/, 'temple'],
  [/荆棘|火焰中|火中/, 'bush'],
  [/云柱|火柱|降火|火降下/, 'fire'],
  [/吗哪|鹌鹑/, 'manna'],
  [/城墙|攻取|攻破|陷落|绕城|耶利哥|焚烧/, 'walls'],
  [/灯台|七教会|教会/, 'lampstand'],
  [/书信|写《|写信|腓立比书|罗马书|哥林多/, 'scroll'],
  [/船|海难|航|港口|宣教|旅程|起航|过来帮助/, 'boat'],
  [/受膏|膏立|作王|国位|登基|君王|王国|宝座|冠冕/, 'crown'],
  [/星|伯利恒之星|有星要出/, 'star'],
  [/水泉|井|泉|得水|出水|苦水变甜/, 'well'],
  [/筑坛|坛|燔祭|献以撒|以勒/, 'altar'],
  [/山顶|上山|遥望|山/, 'mountain'],
]

export function resolveScene(point, mapId) {
  if (point && point.scene) return point.scene
  if (mapId === 'seven-churches') return 'lampstand'
  const hay = [
    point?.name_zh || '',
    point?.altar ? '筑坛' : '',
    point?.promise || '',
    ...(point?.events || []).flatMap(e => [e.title || '', e.summary || '']),
  ].join(' ')
  for (const [re, key] of RULES) if (re.test(hay)) return key
  return 'journey'
}

export const SCENE_LABEL = {
  altar: '筑坛献祭', temple: '圣殿', tablets: '律法之约', crown: '君王', scroll: '书信',
  bush: '荆棘火焰', star: '伯利恒之星', cross: '十字架', tomb: '空坟复活', walls: '城邑征战',
  sea: '分海开路', fire: '云柱火柱', serpent: '铜蛇', lampstand: '七金灯台', boat: '航海宣教',
  well: '活水之井', manna: '天降吗哪', mountain: '高山', journey: '旅程足迹',
}

// 每个场景：返回 <g> 内的图形。统一 viewBox 0 0 120 120，主色用 currentColor 由外层 stroke/fill 控制。
function Art({ scene }) {
  const c = 'currentColor'
  switch (scene) {
    case 'altar': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <rect x="38" y="58" width="44" height="34" rx="2" /><path d="M30 58h60" />
      <path d="M60 58V40M52 40q8-14 16 0M48 30c4 8 24 8 24-6" strokeLinecap="round" />
      <path d="M50 30q10 8 20 0" /></g>)
    case 'temple': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M30 50 60 30 90 50" /><path d="M34 50v40M46 50v40M60 50v40M74 50v40M86 50v40" />
      <path d="M26 92h68M28 50h64" strokeLinecap="round" /></g>)
    case 'tablets': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M40 32h16a4 4 0 0 1 4 4v54H40a4 4 0 0 1-4-4V36a4 4 0 0 1 4-4Z" />
      <path d="M64 32h16a4 4 0 0 1 4 4v50a4 4 0 0 1-4 4H64" />
      <path d="M44 46h10M44 56h10M44 66h10M70 46h10M70 56h10M70 66h10" strokeWidth="2.4" /></g>)
    case 'crown': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M32 78 28 44l16 14 16-22 16 22 16-14-4 34Z" /><path d="M32 86h56" strokeLinecap="round" />
      <circle cx="28" cy="42" r="3" fill={c} /><circle cx="60" cy="32" r="3" fill={c} /><circle cx="92" cy="42" r="3" fill={c} /></g>)
    case 'scroll': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M40 34h44a6 6 0 0 1 6 6v44" /><path d="M36 40a6 6 0 0 1 12 0v46h36a6 6 0 0 1-12 0V40" />
      <path d="M52 50h26M52 60h26M52 70h18" strokeWidth="2.4" strokeLinecap="round" /></g>)
    case 'bush': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M60 92V64" /><path d="M60 66c-14 0-22-10-18-22 6 4 10 2 12-4 4 10 12 6 14-2 6 8 14 8 12 18-4 12-18 12-32 12Z" strokeLinecap="round" />
      <path d="M48 50q4-6 0-12M72 52q4-8-2-14" strokeWidth="2.2" /></g>)
    case 'star': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M60 26 67 50 92 50 72 65 79 90 60 75 41 90 48 65 28 50 53 50Z" /></g>)
    case 'cross': return (<g fill="none" stroke={c} strokeWidth="4" strokeLinecap="round">
      <path d="M60 28v64M40 50h40" /></g>)
    case 'tomb': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M34 88a26 26 0 0 1 52 0Z" /><circle cx="58" cy="64" r="16" />
      <path d="M86 70 78 64" strokeLinecap="round" /><path d="M66 40l4 8 8 2-6 6 2 8-8-4-8 4 2-8-6-6 8-2Z" strokeWidth="2" /></g>)
    case 'walls': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M30 92V52h8v-8h10v8h12v-8h10v8h10v-8h10v8h0v40Z" />
      <path d="M44 92V74h12v18M70 92V74h12" strokeWidth="2.4" /></g>)
    case 'sea': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinecap="round">
      <path d="M30 50q8-8 16 0t16 0 16 0 16 0" /><path d="M30 64q8-8 16 0t16 0 16 0 16 0" />
      <path d="M58 40v44M62 40v44" strokeWidth="2.4" /></g>)
    case 'fire': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M60 28c10 14 18 18 18 34a18 18 0 0 1-36 0c0-8 4-12 8-16 2 6 6 6 6 2 0-8-4-12 4-24Z" strokeLinecap="round" /></g>)
    case 'serpent': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M48 30v62" /><path d="M40 38h16" />
      <path d="M56 44c14 0 14 12 0 12s-14 12 0 12 14 10 0 12" strokeWidth="2.6" /></g>)
    case 'lampstand': return (<g fill="none" stroke={c} strokeWidth="2.6" strokeLinejoin="round">
      <path d="M60 60V86M44 90h32" strokeWidth="3" strokeLinecap="round" />
      <path d="M60 60V42M44 60V46M76 60V46M30 62V52M90 62V52M36 60q0-14 24-14M84 60q0-14-24-14M30 62q-2-12 14-16M90 62q2-12-14-16" />
      {[30,44,60,76,90].map((x,i)=>(<circle key={i} cx={x} cy={i===2?40:i===0||i===4?50:44} r="3" fill={c} stroke="none" />))}
      <path d="M30 50q0 6 6 6M90 50q0 6-6 6" /></g>)
    case 'boat': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M28 70h64l-8 18a6 6 0 0 1-6 4H42a6 6 0 0 1-6-4Z" /><path d="M60 70V30" />
      <path d="M60 34h22l-6 9 6 9H60" strokeLinecap="round" /><path d="M24 64q8 6 16 0t16 0 16 0 16 0" strokeWidth="2.2" /></g>)
    case 'well': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M38 60h44v32H38z" /><path d="M34 60 60 44 86 60" /><path d="M60 44V32" />
      <ellipse cx="60" cy="78" rx="12" ry="5" strokeWidth="2.4" /><path d="M60 60v8" strokeWidth="2.2" /></g>)
    case 'manna': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M28 44q8-8 16 0t16 0 16 0 16 0" strokeLinecap="round" />
      {[[42,62],[60,70],[78,62],[52,82],[70,82],[60,52]].map(([x,y],i)=>(<circle key={i} cx={x} cy={y} r="4" />))}</g>)
    case 'mountain': return (<g fill="none" stroke={c} strokeWidth="3" strokeLinejoin="round">
      <path d="M24 88 52 40l16 26 10-14 18 36Z" /><path d="M46 50l6 8 6-6" strokeWidth="2.2" strokeLinecap="round" /></g>)
    default: /* journey */ return (<g fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M30 86c0-16 18-12 26-22 6-8-6-12-2-22 4-9 22-9 30 2" strokeDasharray="2 9" />
      <circle cx="30" cy="86" r="4" fill={c} stroke="none" /><circle cx="86" cy="48" r="5" /></g>)
  }
}

export default function MapScene({ scene = 'journey', color = '#e8b04b' }) {
  return (
    <svg viewBox="0 0 120 120" width="100%" height="100%" preserveAspectRatio="xMidYMid meet"
      style={{ color, display: 'block' }} aria-hidden="true">
      <Art scene={scene} />
    </svg>
  )
}
