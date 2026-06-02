'use client'
import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import { getMapboxToken, territoriesToFeatureCollection, SOURCE_IDS, LAYER_IDS } from '../lib/mapbox'
import { featureCollection, feature, point, lineBetween, bboxOf } from '../lib/geojson'
import { PROPHECY_COLORS } from '../lib/colors'
import { DEFAULT_CENTER, DEFAULT_ZOOM, JERUSALEM } from '../domain/constants'
import type {
  BibleCampaignDTO,
  BibleMapEventDTO,
  BibleProphecyDTO,
  BibleTerritoryDTO,
  GeoJsonPoint,
  GeoJsonPosition,
} from '../domain/types'

interface Props {
  territories: BibleTerritoryDTO[]
  prophecy: BibleProphecyDTO | null
  campaign: BibleCampaignDTO | null
  focusEvent: BibleMapEventDTO | null
  activeTerritoryId: string | null
  onTerritoryClick: (id: string) => void
}

const EMPTY_FC: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] }

export function MapCanvas({
  territories, prophecy, campaign, focusEvent, activeTerritoryId, onTerritoryClick,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const loadedRef = useRef(false)
  const onClickRef = useRef(onTerritoryClick)
  onClickRef.current = onTerritoryClick

  const token = getMapboxToken()

  // 初始化（一次）
  useEffect(() => {
    if (!token || !containerRef.current || mapRef.current) return
    mapboxgl.accessToken = token
    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
    })
    mapRef.current = map

    map.on('load', () => {
      map.addSource(SOURCE_IDS.territories, { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: LAYER_IDS.territoryFill, type: 'fill', source: SOURCE_IDS.territories,
        paint: { 'fill-color': ['get', 'color'], 'fill-opacity': ['get', 'fillOpacity'] },
      })
      map.addLayer({
        id: LAYER_IDS.territoryOutline, type: 'line', source: SOURCE_IDS.territories,
        paint: { 'line-color': ['get', 'color'], 'line-width': 1.5 },
      })
      map.addLayer({
        id: LAYER_IDS.territoryActive, type: 'line', source: SOURCE_IDS.territories,
        paint: { 'line-color': '#ffffff', 'line-width': 3 },
        filter: ['==', ['get', 'id'], '__none__'],
      })

      map.addSource(SOURCE_IDS.prophecyLine, { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: LAYER_IDS.prophecyLine, type: 'line', source: SOURCE_IDS.prophecyLine,
        paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-dasharray': [2, 1.5] },
      })
      map.addSource(SOURCE_IDS.prophecyTarget, { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'bm-prophecy-target-layer', type: 'circle', source: SOURCE_IDS.prophecyTarget,
        paint: { 'circle-radius': 7, 'circle-color': ['get', 'color'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
      })

      map.addSource(SOURCE_IDS.campaignRoute, { type: 'geojson', data: EMPTY_FC })
      // TODO(deck.gl): 可用 @deck.gl/layers PathLayer + TripsLayer 做动态流光路线动画；
      // 现阶段先用 Mapbox line layer 保证可运行。
      map.addLayer({
        id: LAYER_IDS.campaignRoute, type: 'line', source: SOURCE_IDS.campaignRoute,
        paint: { 'line-color': '#f59e0b', 'line-width': 4, 'line-opacity': 0.9 },
      })
      map.addSource(SOURCE_IDS.campaignPoints, { type: 'geojson', data: EMPTY_FC })
      map.addLayer({
        id: 'bm-campaign-points-layer', type: 'circle', source: SOURCE_IDS.campaignPoints,
        paint: { 'circle-radius': 6, 'circle-color': ['get', 'color'], 'circle-stroke-color': '#fff', 'circle-stroke-width': 2 },
      })

      map.on('click', LAYER_IDS.territoryFill, (e) => {
        const f = e.features?.[0]
        const props = (f?.properties ?? {}) as { id?: string }
        if (typeof props.id === 'string') onClickRef.current(props.id)
      })
      map.on('mouseenter', LAYER_IDS.territoryFill, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', LAYER_IDS.territoryFill, () => { map.getCanvas().style.cursor = '' })

      loadedRef.current = true
      const src = map.getSource(SOURCE_IDS.territories)
      if (src && 'setData' in src) (src as mapboxgl.GeoJSONSource).setData(territoriesToFeatureCollection(territories))
    })

    return () => {
      loadedRef.current = false
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // 疆域数据更新
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loadedRef.current) return
    const src = map.getSource(SOURCE_IDS.territories)
    if (src) (src as mapboxgl.GeoJSONSource).setData(territoriesToFeatureCollection(territories))
  }, [territories])

  // 高亮选中疆域
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loadedRef.current) return
    map.setFilter(LAYER_IDS.territoryActive, ['==', ['get', 'id'], activeTerritoryId ?? '__none__'])
  }, [activeTerritoryId])

  // 预言射线
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loadedRef.current) return
    const lineSrc = map.getSource(SOURCE_IDS.prophecyLine) as mapboxgl.GeoJSONSource | undefined
    const targetSrc = map.getSource(SOURCE_IDS.prophecyTarget) as mapboxgl.GeoJSONSource | undefined
    if (!lineSrc || !targetSrc) return
    if (!prophecy) {
      lineSrc.setData(EMPTY_FC)
      targetSrc.setData(EMPTY_FC)
      return
    }
    const target: [number, number] = [prophecy.targetLongitude, prophecy.targetLatitude]
    const color = PROPHECY_COLORS[prophecy.prophecyType] ?? '#ef4444'
    lineSrc.setData(featureCollection([feature(lineBetween(JERUSALEM, target), { color })]))
    targetSrc.setData(featureCollection([feature(point(target), { color })]))
    const bounds = bboxOf([JERUSALEM as GeoJsonPosition, target as GeoJsonPosition])
    map.fitBounds(bounds, { padding: 80, duration: 800 })
  }, [prophecy])

  // 战役路线
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loadedRef.current) return
    const routeSrc = map.getSource(SOURCE_IDS.campaignRoute) as mapboxgl.GeoJSONSource | undefined
    const pointsSrc = map.getSource(SOURCE_IDS.campaignPoints) as mapboxgl.GeoJSONSource | undefined
    if (!routeSrc || !pointsSrc) return
    if (!campaign) {
      routeSrc.setData(EMPTY_FC)
      pointsSrc.setData(EMPTY_FC)
      return
    }
    routeSrc.setData(featureCollection([feature(campaign.routeGeojson, { id: campaign.id })]))
    const kindColor: Record<string, string> = { camp: '#22c55e', enemy: '#ef4444', retreat: '#eab308' }
    if (campaign.pointsGeojson) {
      const colored = featureCollection<GeoJsonPoint, { color: string; nameZh: string }>(
        campaign.pointsGeojson.features.map((f) =>
          feature(f.geometry, {
            color: kindColor[String(f.properties.kind)] ?? '#38bdf8',
            nameZh: String(f.properties.nameZh ?? ''),
          }),
        ),
      )
      pointsSrc.setData(colored)
    } else {
      pointsSrc.setData(EMPTY_FC)
    }
    const coords = campaign.routeGeojson.coordinates
    map.fitBounds(bboxOf(coords), { padding: 90, duration: 900 })
  }, [campaign])

  // 事件定位
  useEffect(() => {
    const map = mapRef.current
    if (!map || !loadedRef.current || !focusEvent) return
    if (focusEvent.longitude !== null && focusEvent.latitude !== null) {
      map.flyTo({ center: [focusEvent.longitude, focusEvent.latitude], zoom: 8, duration: 900 })
    }
  }, [focusEvent])

  if (!token) {
    return (
      <div className="flex h-full min-h-[320px] w-full items-center justify-center rounded-xl border border-white/10 bg-white/5 p-6 text-center">
        <div>
          <div className="mb-2 text-3xl">🗺️</div>
          <p className="text-sm text-gray-300">请配置 NEXT_PUBLIC_MAPBOX_TOKEN 以启用地图。</p>
          <p className="mt-1 text-xs text-gray-500">（左侧时间轴、图层、事件与右侧详情仍可正常使用。）</p>
        </div>
      </div>
    )
  }

  return <div ref={containerRef} className="h-full min-h-[320px] w-full rounded-xl" />
}
