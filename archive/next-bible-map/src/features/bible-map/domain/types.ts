// 严格类型定义（无 any）。GeoJSON 在 Prisma 中以 Json 存储，读出时经 asGeoJson 收窄。

export type GeoJsonPosition = [number, number] | [number, number, number]

export interface GeoJsonPolygon {
  type: 'Polygon'
  coordinates: GeoJsonPosition[][]
}
export interface GeoJsonMultiPolygon {
  type: 'MultiPolygon'
  coordinates: GeoJsonPosition[][][]
}
export interface GeoJsonLineString {
  type: 'LineString'
  coordinates: GeoJsonPosition[]
}
export interface GeoJsonPoint {
  type: 'Point'
  coordinates: GeoJsonPosition
}
export type GeoJsonGeometry =
  | GeoJsonPolygon
  | GeoJsonMultiPolygon
  | GeoJsonLineString
  | GeoJsonPoint

export interface GeoJsonFeature<
  G extends GeoJsonGeometry = GeoJsonGeometry,
  P extends Record<string, unknown> = Record<string, unknown>,
> {
  type: 'Feature'
  geometry: G
  properties: P
}
export interface GeoJsonFeatureCollection<
  G extends GeoJsonGeometry = GeoJsonGeometry,
  P extends Record<string, unknown> = Record<string, unknown>,
> {
  type: 'FeatureCollection'
  features: Array<GeoJsonFeature<G, P>>
}

export type TerritoryStatus = 'stable' | 'disputed' | 'oppressed' | 'lost' | 'empire'
export type ProphecyType = 'judgment' | 'restoration' | 'warning' | 'messianic'
export type BibleLayer = 'tribes' | 'empires' | 'all' | 'prophecies' | 'campaigns'

export interface BibleTerritoryDTO {
  id: string
  name: string
  nameZh: string
  ownerType: string
  ownerId: string | null
  ownerName: string
  period: string
  startYear: number
  endYear: number | null
  controlScore: number
  status: TerritoryStatus
  color: string | null
  geojson: GeoJsonPolygon | GeoJsonMultiPolygon
  description: string | null
}

export interface BibleMapEventDTO {
  id: string
  title: string
  titleZh: string
  category: string
  book: string | null
  chapter: number | null
  startYear: number
  endYear: number | null
  locationName: string | null
  latitude: number | null
  longitude: number | null
  geojson: GeoJsonGeometry | null
  description: string | null
  spiritualMeaning: string | null
}

export interface BibleProphecyDTO {
  id: string
  book: string
  chapterStart: number
  chapterEnd: number | null
  targetNation: string
  targetNationZh: string
  prophecyType: ProphecyType
  startYear: number | null
  fulfillmentYear: number | null
  sourceLocation: string
  targetLatitude: number
  targetLongitude: number
  description: string
  fulfillmentDescription: string | null
}

export interface BibleCampaignDTO {
  id: string
  name: string
  nameZh: string
  commander: string | null
  commanderZh: string | null
  startYear: number
  endYear: number | null
  book: string | null
  chapter: number | null
  routeGeojson: GeoJsonLineString
  pointsGeojson: GeoJsonFeatureCollection<GeoJsonPoint> | null
  description: string | null
}

export type BibleMapSelectionKind = 'territory' | 'event' | 'prophecy' | 'campaign'
export interface BibleMapSelection {
  kind: BibleMapSelectionKind
  territory?: BibleTerritoryDTO
  event?: BibleMapEventDTO
  prophecy?: BibleProphecyDTO
  campaign?: BibleCampaignDTO
}

export interface ApiOk<T> {
  success: true
  data: T
}
export interface ApiErr {
  success: false
  error: string
}
export type ApiResult<T> = ApiOk<T> | ApiErr

// ── 关系图谱（Neo4j 预留 + 本地 fallback）────────────────────────────────
export type GraphNodeKind = 'tribe' | 'empire' | 'nation' | 'prophecy' | 'campaign' | 'commander'
export type GraphEdgeType = 'AGAINST' | 'LED_BY' | 'CONQUERED' | 'NEIGHBORS' | 'SUCCEEDED'

export interface GraphNode {
  id: string
  label: string
  kind: GraphNodeKind
}
export interface GraphEdge {
  source: string
  target: string
  type: GraphEdgeType
}
export interface BibleGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
export interface GraphNeighborEdge {
  type: GraphEdgeType
  direction: 'out' | 'in'
  node: GraphNode
}
export interface GraphNeighbors {
  node: GraphNode
  neighbors: GraphNeighborEdge[]
  source: 'neo4j' | 'local'
}
