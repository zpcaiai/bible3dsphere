// Neo4j 关系图谱接口（预留，不强依赖启动）。
// 未配置 NEO4J_URI / 未安装 neo4j-driver / 连接失败 → 返回 null，由调用方回退本地图谱。
import type {
  GraphNeighborEdge,
  GraphNeighbors,
  GraphNodeKind,
  GraphEdgeType,
} from '../domain/types'

interface Neo4jNode {
  properties?: { id?: unknown; label?: unknown; kind?: unknown }
}
interface Neo4jRel {
  type?: unknown
  start?: unknown
  startNodeElementId?: unknown
}
interface Neo4jRecord {
  get(key: string): unknown
}
interface Neo4jResult {
  records: Neo4jRecord[]
}
interface Neo4jSession {
  run(query: string, params?: Record<string, unknown>): Promise<Neo4jResult>
  close(): Promise<void>
}
interface Neo4jDriver {
  session(): Neo4jSession
}
interface Neo4jModule {
  driver(uri: string, auth: unknown): Neo4jDriver
  auth: { basic(user: string, password: string): unknown }
}

function isConfigured(): boolean {
  return Boolean(process.env.NEO4J_URI && process.env.NEO4J_USER && process.env.NEO4J_PASSWORD)
}

async function getDriver(): Promise<Neo4jDriver | null> {
  if (!isConfigured()) return null
  try {
    const mod = (await import('neo4j-driver')) as unknown as { default?: Neo4jModule } & Partial<Neo4jModule>
    const neo4j = (mod.default ?? mod) as Neo4jModule
    return neo4j.driver(
      process.env.NEO4J_URI as string,
      neo4j.auth.basic(process.env.NEO4J_USER as string, process.env.NEO4J_PASSWORD as string),
    )
  } catch {
    return null
  }
}

function asString(v: unknown, fallback = ''): string {
  return typeof v === 'string' ? v : fallback
}

export async function neighborsFromNeo4j(nodeId: string): Promise<GraphNeighbors | null> {
  const driver = await getDriver()
  if (!driver) return null
  const session = driver.session()
  try {
    const result = await session.run(
      'MATCH (n {id: $id})-[r]-(m) RETURN n, r, m',
      { id: nodeId },
    )
    if (result.records.length === 0) return null
    const first = result.records[0].get('n') as Neo4jNode
    const node = {
      id: asString(first.properties?.id, nodeId),
      label: asString(first.properties?.label, nodeId),
      kind: asString(first.properties?.kind, 'nation') as GraphNodeKind,
    }
    const neighbors: GraphNeighborEdge[] = result.records.map((rec) => {
      const m = rec.get('m') as Neo4jNode
      const r = rec.get('r') as Neo4jRel
      return {
        type: asString(r.type, 'AGAINST') as GraphEdgeType,
        direction: 'out' as const,
        node: {
          id: asString(m.properties?.id),
          label: asString(m.properties?.label),
          kind: asString(m.properties?.kind, 'nation') as GraphNodeKind,
        },
      }
    })
    return { node, neighbors, source: 'neo4j' }
  } catch {
    return null
  } finally {
    await session.close()
  }
}
