// Leaflet 实现的地图适配器。Leaflet 从 CDN 运行时按需加载（不进 npm 依赖，PWA 体积零增加）。
// 对外坐标统一 [lng, lat]；内部转换为 Leaflet 的 [lat, lng]。
import MapAdapter from './MapAdapter'

const LEAFLET_JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
const LEAFLET_CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'

let _loading = null
function loadLeaflet() {
  if (window.L) return Promise.resolve(window.L)
  if (_loading) return _loading
  _loading = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${LEAFLET_CSS}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'; link.href = LEAFLET_CSS
      document.head.appendChild(link)
    }
    const script = document.createElement('script')
    script.src = LEAFLET_JS
    script.async = true
    script.onload = () => resolve(window.L)
    script.onerror = () => reject(new Error('Leaflet 加载失败（可能离线）'))
    document.head.appendChild(script)
  })
  return _loading
}

const lonlat = ([lng, lat]) => [lat, lng] // GeoJSON -> Leaflet

export default class LeafletAdapter extends MapAdapter {
  constructor() { super(); this.map = null; this.L = null; this.layers = [] }

  get ready() { return !!this.map }

  async init(container, options = {}) {
    const L = await loadLeaflet()
    this.L = L
    const center = options.center ? lonlat(options.center) : [29.5, 34]
    this.map = L.map(container, {
      center,
      zoom: options.zoom ?? 6,
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: options.scrollWheelZoom ?? true,
    })
    // 底图图层：标准 OSM + 复古怀旧风（CSS 滤镜在 .biblemap-map 上叠加）
    const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; OpenStreetMap',
    })
    const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, attribution: '&copy; OpenTopoMap',
    })
    osm.addTo(this.map)
    L.control.layers(
      { '怀旧地图': osm, '地形图': topo },
      {},
      { position: 'topright', collapsed: true },
    ).addTo(this.map)
    // 容器在子tab切换后才可见，确保尺寸正确（多次触发以覆盖 visibility 过渡）
    setTimeout(() => { try { this.map && this.map.invalidateSize() } catch (e) {} }, 200)
    setTimeout(() => { try { this.map && this.map.invalidateSize() } catch (e) {} }, 800)
    return this
  }

  setView(lngLat, zoom, animate = true) {
    if (!this.map) return
    this.map.flyTo(lonlat(lngLat), zoom ?? this.map.getZoom(), { duration: animate ? 1.1 : 0 })
  }

  fitBounds(bounds, options = {}) {
    if (!this.map) return
    const [sw, ne] = bounds
    this.map.fitBounds([lonlat(sw), lonlat(ne)], { padding: [30, 30], ...options })
  }

  addMarker(lngLat, options = {}) {
    if (!this.map) return null
    const L = this.L
    const { label, color = '#fbbf24', onClick, html, active } = options
    const size = active ? 30 : 24
    const icon = L.divIcon({
      className: 'biblemap-pin',
      html: `<div class="biblemap-pin-dot${active ? ' active' : ''}" style="--pin:${color};width:${size}px;height:${size}px">${label ?? ''}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
    const m = L.marker(lonlat(lngLat), { icon }).addTo(this.map)
    if (html) m.bindPopup(html, { className: 'biblemap-popup' })
    if (onClick) m.on('click', onClick)
    this.layers.push(m)
    return m
  }

  addRoute(coordinates, options = {}) {
    if (!this.map) return null
    const L = this.L
    const latlngs = coordinates.map(lonlat)
    const line = L.polyline(latlngs, {
      color: options.color ?? '#ffd700',
      weight: options.weight ?? 3,
      opacity: options.opacity ?? 0.8,
      dashArray: options.dashArray ?? '6 8',
    }).addTo(this.map)
    this.layers.push(line)
    return line
  }

  showPopup(lngLat, html) {
    if (!this.map) return
    this.L.popup({ className: 'biblemap-popup' }).setLatLng(lonlat(lngLat)).setContent(html).openOn(this.map)
  }

  renderGeoJson(geojson, options = {}) {
    if (!this.map) return null
    const layer = this.L.geoJSON(geojson, options).addTo(this.map)
    this.layers.push(layer)
    return layer
  }

  clear() {
    if (!this.map) return
    this.layers.forEach(l => this.map.removeLayer(l))
    this.layers = []
  }

  destroy() {
    if (this.map) { this.map.remove(); this.map = null }
  }
}
