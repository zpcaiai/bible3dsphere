import type {
  GeoJsonFeature,
  GeoJsonFeatureCollection,
  GeoJsonGeometry,
  GeoJsonLineString,
  GeoJsonMultiPolygon,
  GeoJsonPoint,
  GeoJsonPolygon,
  GeoJsonPosition,
} from '../domain/types'

/**
 * Prisma 的 JsonValue 是结构未知的递归类型。读出 GeoJSON 时用此助手收窄，
 * 通过 unknown 中转避免 any，调用方负责保证存入的就是对应 GeoJSON。
 */
export function asGeoJson<T extends GeoJsonGeometry>(value: unknown): T {
  return value as unknown as T
}

export function asFeatureCollection<
  G extends GeoJsonGeometry,
  P extends Record<string, unknown> = Record<string, unknown>,
>(value: unknown): GeoJsonFeatureCollection<G, P> {
  return value as unknown as GeoJsonFeatureCollection<G, P>
}

export function feature<
  G extends GeoJsonGeometry,
  P extends Record<string, unknown> = Record<string, unknown>,
>(geometry: G, properties: P): GeoJsonFeature<G, P> {
  return { type: 'Feature', geometry, properties }
}

export function featureCollection<
  G extends GeoJsonGeometry,
  P extends Record<string, unknown> = Record<string, unknown>,
>(features: Array<GeoJsonFeature<G, P>>): GeoJsonFeatureCollection<G, P> {
  return { type: 'FeatureCollection', features }
}

export function polygon(coordinates: GeoJsonPosition[][]): GeoJsonPolygon {
  return { type: 'Polygon', coordinates }
}
export function multiPolygon(coordinates: GeoJsonPosition[][][]): GeoJsonMultiPolygon {
  return { type: 'MultiPolygon', coordinates }
}
export function lineString(coordinates: GeoJsonPosition[]): GeoJsonLineString {
  return { type: 'LineString', coordinates }
}
export function point(coordinates: GeoJsonPosition): GeoJsonPoint {
  return { type: 'Point', coordinates }
}

/** 由 bbox [west, south, east, north] 生成闭合矩形 Polygon（教学示意用） */
export function rectPolygon(west: number, south: number, east: number, north: number): GeoJsonPolygon {
  return polygon([[
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
  ]])
}

/** 两点之间的 LineString（预言射线） */
export function lineBetween(a: [number, number], b: [number, number]): GeoJsonLineString {
  return lineString([a, b])
}

/** 计算一组坐标的包围盒，供 fitBounds 使用 */
export function bboxOf(coords: GeoJsonPosition[]): [[number, number], [number, number]] {
  let minLng = Infinity
  let minLat = Infinity
  let maxLng = -Infinity
  let maxLat = -Infinity
  for (const [lng, lat] of coords) {
    if (lng < minLng) minLng = lng
    if (lat < minLat) minLat = lat
    if (lng > maxLng) maxLng = lng
    if (lat > maxLat) maxLat = lat
  }
  return [
    [minLng, minLat],
    [maxLng, maxLat],
  ]
}

/** 射线法判断点是否在单个环内 */
function pointInRing(lng: number, lat: number, ring: GeoJsonPosition[]): boolean {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0]
    const yi = ring[i][1]
    const xj = ring[j][0]
    const yj = ring[j][1]
    const intersect = yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi
    if (intersect) inside = !inside
  }
  return inside
}

/** 点是否落在 Polygon / MultiPolygon 内（含外环，忽略洞，足够教学用） */
export function pointInGeometry(
  lng: number,
  lat: number,
  geometry: GeoJsonPolygon | GeoJsonMultiPolygon,
): boolean {
  if (geometry.type === 'Polygon') {
    return pointInRing(lng, lat, geometry.coordinates[0] ?? [])
  }
  return geometry.coordinates.some((poly) => pointInRing(lng, lat, poly[0] ?? []))
}
