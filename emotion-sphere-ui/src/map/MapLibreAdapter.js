// MapLibre GL JS 适配器 —— Mapbox GL v1 的免费开源分支，全部 WebGL 能力、无需令牌。
// 运行时从 CDN 加载；底图用 OSM 栅格瓦片自建 style（免费）。对外坐标 [lng, lat]。
// 与 MapboxAdapter 接口一致，业务组件零改动。VITE_MAP_PROVIDER=maplibre 即启用。
import MapAdapter from './MapAdapter'

const VER = '4.7.1'
const JS = `https://unpkg.com/maplibre-gl@${VER}/dist/maplibre-gl.js`
const CSS = `https://unpkg.com/maplibre-gl@${VER}/dist/maplibre-gl.css`

let _loading = null
function loadMapLibre() {
  if (window.maplibregl) return Promise.resolve(window.maplibregl)
  if (_loading) return _loading
  _loading = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${CSS}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'; link.href = CSS
      document.head.appendChild(link)
    }
    const s = document.createElement('script')
    s.src = JS; s.async = true
    s.onload = () => resolve(window.maplibregl)
    s.onerror = () => reject(new Error('MapLibre GL 加载失败（可能离线）'))
    document.head.appendChild(s)
  })
  return _loading
}

const OSM_STYLE = {
  version: 8,
  sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap' } },
  layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
}

export default class MapLibreAdapter extends MapAdapter {
  constructor() {
    super()
    this.map = null; this.gl = null; this.markers = []; this.sourceIds = []; this._seq = 0
  }

  get ready() { return !!this.map && this.map.isStyleLoaded() }

  async init(container, options = {}) {
    const gl = await loadMapLibre()
    this.gl = gl
    this.map = new gl.Map({
      container,
      style: import.meta.env.VITE_MAPLIBRE_STYLE || OSM_STYLE,
      center: options.center || [34, 31],
      zoom: options.zoom ?? 5,
      scrollZoom: options.scrollWheelZoom ?? true,
      attributionControl: true,
    })
    this.map.addControl(new gl.NavigationControl(), 'top-right')
    await new Promise((res) => this.map.on('load', res))
    return this
  }

  setView(lngLat, zoom, animate = true) {
    if (!this.map) return
    this.map.flyTo({ center: lngLat, zoom: zoom ?? this.map.getZoom(), duration: animate ? 1100 : 0 })
  }

  fitBounds(bounds, options = {}) {
    if (!this.map) return
    this.map.fitBounds(bounds, { padding: 40, duration: 0, ...options })
  }

  addMarker(lngLat, options = {}) {
    if (!this.map) return null
    const { label, color = '#fbbf24', onClick, html, active } = options
    const el = document.createElement('div')
    el.className = 'biblemap-pin-dot' + (active ? ' active' : '')
    const size = active ? 30 : 24
    el.style.cssText = `--pin:${color};width:${size}px;height:${size}px`
    el.textContent = label ?? ''
    const marker = new this.gl.Marker({ element: el }).setLngLat(lngLat).addTo(this.map)
    let popup = null
    if (html) {
      popup = new this.gl.Popup({ offset: 18, className: 'biblemap-popup' }).setHTML(html)
      marker.setPopup(popup)
    }
    if (onClick) el.addEventListener('click', onClick)
    this.markers.push(marker)
    return { raw: marker, openPopup: () => { if (popup && !popup.isOpen()) marker.togglePopup() } }
  }

  addRoute(coordinates, options = {}) {
    if (!this.map) return null
    const id = `route-${++this._seq}`
    this.map.addSource(id, { type: 'geojson', data: { type: 'Feature', geometry: { type: 'LineString', coordinates } } })
    this.map.addLayer({
      id, type: 'line', source: id,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': options.color ?? '#ffd700', 'line-width': options.weight ?? 3, 'line-opacity': options.opacity ?? 0.85, 'line-dasharray': [2, 2] },
    })
    this.sourceIds.push(id)
    return id
  }

  showPopup(lngLat, html) {
    if (!this.map) return
    new this.gl.Popup({ className: 'biblemap-popup' }).setLngLat(lngLat).setHTML(html).addTo(this.map)
  }

  renderGeoJson(geojson, options = {}) {
    if (!this.map) return null
    const id = `geojson-${++this._seq}`
    const feat = geojson.type === 'Feature' ? geojson : { type: 'Feature', geometry: geojson }
    this.map.addSource(id, { type: 'geojson', data: feat })
    const c = options.style?.fillColor || options.paint?.['fill-color'] || '#ffd700'
    if (feat.geometry?.type === 'LineString') {
      this.map.addLayer({ id, type: 'line', source: id, paint: { 'line-color': c, 'line-width': options.style?.weight ?? 2 } })
    } else {
      this.map.addLayer({ id, type: 'fill', source: id, paint: { 'fill-color': c, 'fill-opacity': options.style?.fillOpacity ?? 0.32, 'fill-outline-color': c } })
    }
    this.sourceIds.push(id)
    return id
  }

  clear() {
    if (!this.map) return
    this.markers.forEach((m) => m.remove())
    this.markers = []
    this.sourceIds.forEach((id) => {
      if (this.map.getLayer(id)) this.map.removeLayer(id)
      if (this.map.getSource(id)) this.map.removeSource(id)
    })
    this.sourceIds = []
  }

  destroy() {
    if (this.map) { this.map.remove(); this.map = null }
  }
}
