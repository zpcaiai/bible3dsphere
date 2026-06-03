import { seedTribes, seedEmpires } from './seed-territories'
import { seedProphecies } from './seed-prophecies'
import { seedCampaigns } from './seed-campaigns'
import type { BibleGraph, GraphEdge, GraphNeighbors, GraphNode } from '../domain/types'

function nationId(name: string): string {
  return `nation-${name.toLowerCase()}`
}

const nodes: GraphNode[] = []
const edges: GraphEdge[] = []
const seen = new Set<string>()
function addNode(n: GraphNode): void {
  if (seen.has(n.id)) return
  seen.add(n.id)
  nodes.push(n)
}

// 支派 / 帝国
for (const t of seedTribes) addNode({ id: t.id, label: t.nameZh, kind: 'tribe' })
for (const e of seedEmpires) addNode({ id: e.id, label: e.nameZh, kind: 'empire' })

// 预言 → 列国
for (const p of seedProphecies) {
  addNode({ id: p.id, label: `${p.book}${p.chapterStart} 论${p.targetNationZh}`, kind: 'prophecy' })
  addNode({ id: nationId(p.targetNation), label: p.targetNationZh, kind: 'nation' })
  edges.push({ source: p.id, target: nationId(p.targetNation), type: 'AGAINST' })
}

// 战役 → 统帅
for (const c of seedCampaigns) {
  addNode({ id: c.id, label: c.nameZh, kind: 'campaign' })
  if (c.commanderZh) {
    const cid = `commander-${c.id}`
    addNode({ id: cid, label: c.commanderZh, kind: 'commander' })
    edges.push({ source: c.id, target: cid, type: 'LED_BY' })
  }
}

// 帝国征服（教学示意）
const conquests: ReadonlyArray<[string, string]> = [
  ['empire-assyria', nationId('Israel')],
  ['empire-babylon', nationId('Judah')],
  ['empire-babylon', nationId('Tyre')],
  ['empire-babylon', nationId('Nineveh')],
  ['empire-persia', nationId('Babylon')],
]
addNode({ id: nationId('Israel'), label: '北国以色列', kind: 'nation' })
addNode({ id: nationId('Judah'), label: '南国犹大', kind: 'nation' })
for (const [emp, nat] of conquests) edges.push({ source: emp, target: nat, type: 'CONQUERED' })

// 帝国更替
const successions: ReadonlyArray<[string, string]> = [
  ['empire-babylon', 'empire-assyria'],
  ['empire-persia', 'empire-babylon'],
  ['empire-greece', 'empire-persia'],
  ['empire-rome', 'empire-greece'],
]
for (const [next, prev] of successions) edges.push({ source: next, target: prev, type: 'SUCCEEDED' })

// 支派相邻（示意）
const neighbors: ReadonlyArray<[string, string]> = [
  ['tribe-judah', 'tribe-benjamin'],
  ['tribe-judah', 'tribe-simeon'],
  ['tribe-benjamin', 'tribe-ephraim'],
  ['tribe-ephraim', 'tribe-manasseh-west'],
  ['tribe-gad', 'tribe-reuben'],
]
for (const [a, b] of neighbors) edges.push({ source: a, target: b, type: 'NEIGHBORS' })

export const localGraph: BibleGraph = { nodes, edges }

const nodeMap = new Map(nodes.map((n) => [n.id, n]))

export function localNeighbors(nodeId: string): GraphNeighbors | null {
  const node = nodeMap.get(nodeId)
  if (!node) return null
  const neighborsOut = edges
    .filter((e) => e.source === nodeId)
    .map((e) => ({ type: e.type, direction: 'out' as const, node: nodeMap.get(e.target) }))
  const neighborsIn = edges
    .filter((e) => e.target === nodeId)
    .map((e) => ({ type: e.type, direction: 'in' as const, node: nodeMap.get(e.source) }))
  const all = [...neighborsOut, ...neighborsIn].flatMap((x) =>
    x.node ? [{ type: x.type, direction: x.direction, node: x.node }] : [],
  )
  return { node, neighbors: all, source: 'local' }
}
