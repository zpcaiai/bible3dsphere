// 数据源：API 优先（Python /api/bible-map/*），失败/离线回退本地 seed。
// 过滤逻辑与后端一致，保证无后端也能完整运行（PWA 离线友好）。
import { seedTerritories } from '../data/seed-territories'
import { seedEvents } from '../data/seed-events'
import { seedProphecies } from '../data/seed-prophecies'
import { seedCampaigns } from '../data/seed-campaigns'
import { localGraph, localNeighbors } from '../data/graph'
import { EVENT_YEAR_WINDOW } from '../domain/constants'
import type {
  BibleCampaignDTO,
  BibleGraph,
  BibleLayer,
  BibleMapEventDTO,
  BibleProphecyDTO,
  BibleTerritoryDTO,
  GraphNeighbors,
} from '../domain/types'

const API_BASE = ((import.meta.env.VITE_API_BASE as string | undefined) ?? '/api').replace(/\/+$/, '')

async function apiGet<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}/bible-map${path}`, { cache: 'no-store' })
    if (!res.ok) return null
    const json = (await res.json()) as { success: boolean; data?: T }
    return json.success && json.data !== undefined ? json.data : null
  } catch {
    return null
  }
}

export async function fetchTerritories(year: number, layer: BibleLayer): Promise<BibleTerritoryDTO[]> {
  const api = await apiGet<BibleTerritoryDTO[]>(`/territories?year=${year}&layer=${layer}`)
  if (api) return api
  return seedTerritories
    .filter((t) => {
      if (layer === 'tribes') return t.ownerType === 'tribe'
      if (layer === 'empires') return t.ownerType === 'empire'
      return t.ownerType === 'tribe' || t.ownerType === 'empire'
    })
    .filter((t) => t.startYear <= year && (t.endYear === null || t.endYear >= year))
}

export async function fetchEvents(year: number): Promise<BibleMapEventDTO[]> {
  const api = await apiGet<BibleMapEventDTO[]>(`/events?year=${year}`)
  if (api) return api
  return seedEvents
    .filter((e) => {
      const end = e.endYear ?? e.startYear
      if (e.startYear <= year && year <= end) return true
      return Math.min(Math.abs(e.startYear - year), Math.abs(end - year)) <= EVENT_YEAR_WINDOW
    })
    .sort((a, b) => a.startYear - b.startYear)
}

export async function fetchProphecies(): Promise<BibleProphecyDTO[]> {
  const api = await apiGet<BibleProphecyDTO[]>('/prophecies')
  return api ?? seedProphecies
}

export async function fetchCampaigns(): Promise<BibleCampaignDTO[]> {
  const api = await apiGet<BibleCampaignDTO[]>('/campaigns')
  return api ?? seedCampaigns
}

export async function fetchGraph(): Promise<BibleGraph> {
  const api = await apiGet<BibleGraph>('/graph')
  return api ?? localGraph
}

export async function fetchGraphNeighbors(node: string): Promise<GraphNeighbors | null> {
  const api = await apiGet<GraphNeighbors>(`/graph?node=${encodeURIComponent(node)}`)
  return api ?? localNeighbors(node)
}

export interface AiData {
  commentary: string
  source: 'llm' | 'template'
}
export async function generateAi(kind: string, name: string): Promise<AiData> {
  try {
    const res = await fetch(`${API_BASE}/bible-map/ai`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, name }),
    })
    if (res.ok) {
      const json = (await res.json()) as { success: boolean; data?: AiData }
      if (json.success && json.data) return json.data
    }
  } catch {
    /* fall through to template */
  }
  return {
    commentary:
      `关于「${name}」，从四个维度作教学性讲解：\n` +
      `① 历史背景　② 地理意义　③ 属灵意义　④ 现代应用。\n` +
      `（配置后端 AI 后将由大模型生成完整讲解。）`,
    source: 'template',
  }
}
