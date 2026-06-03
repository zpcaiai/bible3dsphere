import { NextResponse } from 'next/server'
import { localGraph, localNeighbors } from '@/features/bible-map/data/graph'
import { neighborsFromNeo4j } from '@/features/bible-map/lib/neo4j'
import type { ApiResult, BibleGraph, GraphNeighbors } from '@/features/bible-map/domain/types'

export const dynamic = 'force-dynamic'

// GET /api/bible-map/graph            → 全图 { nodes, edges }
// GET /api/bible-map/graph?node=<id>  → 该节点邻居（Neo4j 优先，回退本地）
export async function GET(
  req: Request,
): Promise<NextResponse<ApiResult<BibleGraph | GraphNeighbors>>> {
  try {
    const { searchParams } = new URL(req.url)
    const node = searchParams.get('node')
    if (!node) {
      return NextResponse.json({ success: true, data: localGraph })
    }
    const fromNeo4j = await neighborsFromNeo4j(node)
    if (fromNeo4j) return NextResponse.json({ success: true, data: fromNeo4j })
    const local = localNeighbors(node)
    if (!local) {
      return NextResponse.json({ success: false, error: `未找到节点 ${node}` }, { status: 404 })
    }
    return NextResponse.json({ success: true, data: local })
  } catch (e) {
    const error = e instanceof Error ? e.message : '未知错误'
    return NextResponse.json({ success: false, error }, { status: 500 })
  }
}
