// 圣经地理数据源 —— 抽象前端取数：优先后端 /api/geo（PostGIS 时效模型），
// 失败/离线时回退到本地静态 GeoJSON。后端只提供几何+时代正确的地名+经文，
// 事件(events)与置信度(confidence)等展示元数据始终来自本地静态文件，按 order 合并。
import { API_BASE } from '../api'
import { exodusStations, exodusRoute, routeHypotheses, confidenceMeta } from './exodusStations'

const LOCAL_STATIONS = exodusStations.features
  .slice()
  .sort((a, b) => a.properties.order - b.properties.order)

// 本地元数据索引（按 order）
const META_BY_ORDER = new Map(
  LOCAL_STATIONS.map((f) => [f.properties.order, f.properties])
)

async function tryFetchExodus() {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const res = await fetch(`${API_BASE}/geo/exodus`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data?.stations?.features?.length) throw new Error('空数据')
    return data
  } finally {
    clearTimeout(t)
  }
}

/**
 * 返回 { stations: Feature[], source: 'api'|'local' }
 * stations 始终带本地 events/confidence；几何与时代地名优先用 API。
 */
export async function loadExodusStations() {
  try {
    const api = await tryFetchExodus()
    const merged = api.stations.features
      .map((f) => {
        const order = f.properties.order
        const meta = META_BY_ORDER.get(order) || {}
        const apiEvents = Array.isArray(f.properties.events) ? f.properties.events : null
        return {
          type: 'Feature',
          geometry: f.geometry || meta?.__geom || null,
          properties: {
            ...meta,                       // 本地兜底：events / confidence / name_he 等
            order,
            name_zh: f.properties.name_zh || meta.name_zh,
            name_en: f.properties.name_en || meta.name_en,
            name_he: f.properties.name_he || meta.name_he,
            scriptureRef: f.properties.scriptureRef || meta.scriptureRef,
            // 数据库为权威：API 提供则覆盖本地
            confidence: f.properties.confidence || meta.confidence,
            events: (apiEvents && apiEvents.length) ? apiEvents : meta.events,
          },
        }
      })
      .sort((a, b) => a.properties.order - b.properties.order)
    return { stations: merged, source: 'api' }
  } catch (e) {
    return { stations: LOCAL_STATIONS, source: 'local' }
  }
}

export { exodusRoute, routeHypotheses, confidenceMeta }

// ── 统一数据集模型 ──────────────────────────────────────────────────────────
// dataset = { id, title, variantLabel, stations:Feature[], variants:[{id,label,short,color,description,route,stationIds?,overrides?}], defaultVariantId, source }
import { paulCities, paulJourneys } from './paulJourneys'
import { JERUSALEM_SLUG, jerusalemPoint, jerusalemEras, landmarksFCForYear, landmarkNoteBySlug } from './jerusalemEras'
import { territoryEras, colorBySlug, regionsFCForYear } from './territories'
import { JOURNEY_DATASETS } from './bibleJourneys'
import { kingsEras } from './kingsTimeline'

async function buildExodusDataset() {
  const { stations, source } = await loadExodusStations()
  return {
    id: 'exodus',
    title: '出埃及与旷野漂流',
    subtitle: '民数记33章 · 42个安营点',
    variantLabel: '路线假说',
    stations,
    variants: routeHypotheses,            // 含 route + overrides
    defaultVariantId: 'traditional-south',
    source,
  }
}

async function tryFetchPaul() {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const res = await fetch(`${API_BASE}/geo/paul`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data?.features?.length) throw new Error('空数据')
    return data
  } finally { clearTimeout(t) }
}

async function buildPaulDataset() {
  // 旅程结构(stationIds/顺序/颜色)为前端结构性元数据；城市几何/事件/置信度优先取自后端。
  let apiByName = null
  let source = 'local'
  try {
    const data = await tryFetchPaul()
    apiByName = new Map(data.features.map((f) => [f.properties.name_zh, f]))
    source = 'api'
  } catch (e) { /* 回退本地 */ }

  const merged = paulCities.map((c) => {
    const api = apiByName?.get(c.name_zh)
    const coords = api?.geometry?.coordinates || [c.lng, c.lat]
    const events = (api && Array.isArray(api.properties.events) && api.properties.events.length)
      ? api.properties.events : c.events
    return {
      id: c.id, name_zh: c.name_zh, name_en: c.name_en, lng: coords[0], lat: coords[1],
      confidence: api?.properties.confidence || c.confidence, events,
    }
  })
  const byId = new Map(merged.map((c) => [c.id, c]))
  const stations = merged.map((c) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [c.lng, c.lat] },
    properties: {
      id: c.id, name_zh: c.name_zh, name_en: c.name_en, name_he: '',
      confidence: c.confidence, events: c.events,
      scriptureRef: c.events?.[0]?.ref || '',
    },
  }))
  const variants = paulJourneys.map((j) => ({
    id: j.id, label: j.label, short: j.short, color: j.color, description: j.description,
    startYear: j.startYear, endYear: j.endYear,
    stationIds: j.stationIds,
    route: j.stationIds.map((id) => { const c = byId.get(id); return [c.lng, c.lat] }),
  }))
  return {
    id: 'paul',
    title: '保罗宣教旅程',
    subtitle: '使徒行传 · 三次旅程 + 押往罗马',
    variantLabel: '宣教旅程',
    stations,
    variants,
    defaultVariantId: 'journey-1',
    source,
  }
}

function buildJerusalemDataset() {
  return {
    id: 'jerusalem',
    title: '耶路撒冷时代演变',
    subtitle: '一地多名 · 城墙疆域随时代演变',
    temporal: true,
    slug: JERUSALEM_SLUG,
    point: jerusalemPoint,
    eras: jerusalemEras,
    source: 'local',
  }
}

// 时空切片：取某年该地点的疆域(polygon)与当时名称。失败返回 null（组件回退本地）。
export async function fetchLandmarks(year) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const res = await fetch(`${API_BASE}/geo/landmarks?year=${year}`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const fc = await res.json()
    return { fc, source: 'api' }
  } catch (e) {
    return { fc: landmarksFCForYear(year), source: 'local' }
  } finally { clearTimeout(t) }
}

export { landmarkNoteBySlug }

export async function fetchTimeSlice(slug, year) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const res = await fetch(`${API_BASE}/geo/timeline?slug=${encodeURIComponent(slug)}&year=${year}`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (!data?.geometry) throw new Error('空')
    return data
  } catch (e) {
    return null
  } finally { clearTimeout(t) }
}

function buildTerritoriesDataset() {
  return {
    id: 'territories',
    title: '支派与王国疆域',
    subtitle: '十二支派分地 vs 联合王国',
    temporal: true,
    kind: 'regions',
    eras: territoryEras,
    colorBySlug,
    source: 'local',
  }
}

// 取某年的政治疆域（FeatureCollection）。失败回退本地示意多边形。
export async function fetchRegions(year) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const res = await fetch(`${API_BASE}/geo/regions?year=${year}`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const fc = await res.json()
    if (!fc?.features?.length) throw new Error('空')
    return { fc, source: 'api' }
  } catch (e) {
    return { fc: regionsFCForYear(year), source: 'local' }
  } finally { clearTimeout(t) }
}

// 取某实体的拓扑关系。失败返回 []。
export async function fetchRelations(slug, year) {
  const ctrl = new AbortController()
  const t = setTimeout(() => ctrl.abort(), 3500)
  try {
    const q = year != null ? `?slug=${encodeURIComponent(slug)}&year=${year}` : `?slug=${encodeURIComponent(slug)}`
    const res = await fetch(`${API_BASE}/geo/relations${q}`, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    return data.relations || []
  } catch (e) {
    return []
  } finally { clearTimeout(t) }
}

// 数据集注册表（数据集选择器用）
// 通用行程数据集构建（耶稣/亚伯拉罕/约书亚/大卫/所罗门/七教会/受难周）
function buildJourneyDataset(d) {
  const byId = new Map(d.cities.map((c) => [c.id, c]))
  const stations = d.cities.map((c) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [c.lng, c.lat] },
    properties: {
      id: c.id, name_zh: c.name_zh, name_en: c.name_en, name_he: '',
      confidence: c.confidence || 'identified', events: c.events || [],
      scriptureRef: c.events && c.events[0] ? c.events[0].ref : '',
    },
  }))
  const variants = d.variants.map((v) => ({
    id: v.id, label: v.label, short: v.short, color: v.color, description: v.description,
    startYear: v.startYear, endYear: v.endYear, stationIds: v.stationIds,
    route: v.stationIds.map((id) => { const c = byId.get(id); return [c.lng, c.lat] }),
  }))
  return {
    id: d.id, title: d.title, subtitle: d.subtitle, variantLabel: d.variantLabel || '路线',
    stations, variants, defaultVariantId: d.variants[0].id, source: 'local',
  }
}

function buildKingsDataset() {
  return {
    id: 'kings', title: '北国南国列王', subtitle: '分裂王国 · 列王与先知年表',
    temporal: true, kind: 'regions', eras: kingsEras, colorBySlug, source: 'local',
  }
}

export const BIBLE_MAPS = [
  { id: 'jesus', title: '耶稣生平', icon: '✝️' },
  { id: 'abraham', title: '亚伯拉罕迁徙', icon: '🐫' },
  { id: 'exodus', title: '出埃及与旷野漂流', icon: '🏜️' },
  { id: 'joshua', title: '约书亚征服迦南', icon: '⚔️' },
  { id: 'territories', title: '十二支派与王国', icon: '👑' },
  { id: 'david', title: '大卫王国', icon: '🛡️' },
  { id: 'solomon', title: '所罗门王国', icon: '🏺' },
  { id: 'kings', title: '北国南国列王', icon: '📜' },
  { id: 'seven-churches', title: '启示录七教会', icon: '🕯️' },
  { id: 'passion-week', title: '受难周', icon: '🌿' },
  { id: 'paul', title: '保罗宣教旅程', icon: '⛵' },
  { id: 'jerusalem', title: '耶路撒冷演变', icon: '🏙️' },
]

export async function loadBibleMap(datasetId) {
  const journey = JOURNEY_DATASETS.find((d) => d.id === datasetId)
  if (journey) return buildJourneyDataset(journey)
  if (datasetId === 'paul') return await buildPaulDataset()
  if (datasetId === 'jerusalem') return buildJerusalemDataset()
  if (datasetId === 'territories') return buildTerritoriesDataset()
  if (datasetId === 'kings') return buildKingsDataset()
  return buildExodusDataset()
}
