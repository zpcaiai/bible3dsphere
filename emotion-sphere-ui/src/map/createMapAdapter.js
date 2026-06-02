// 地图适配器工厂 —— 业务组件只依赖此处，切换底层地图库无需改组件。
// 选择策略：VITE_MAP_PROVIDER=mapbox 且有 VITE_MAPBOX_TOKEN 时用 Mapbox，否则 Leaflet。
import LeafletAdapter from './LeafletAdapter'
import MapboxAdapter from './MapboxAdapter'
import CesiumAdapter from './CesiumAdapter'
import MapLibreAdapter from './MapLibreAdapter'

export function createMapAdapter() {
  const provider = (import.meta.env.VITE_MAP_PROVIDER || 'leaflet').toLowerCase()
  if (provider === 'cesium') return new CesiumAdapter()
  if (provider === 'maplibre') return new MapLibreAdapter()
  if (provider === 'mapbox' && import.meta.env.VITE_MAPBOX_TOKEN) {
    return new MapboxAdapter()
  }
  return new LeafletAdapter()
}

export { LeafletAdapter, MapboxAdapter, CesiumAdapter, MapLibreAdapter }
