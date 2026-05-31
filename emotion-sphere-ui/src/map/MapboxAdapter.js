// Mapbox GL 实现的地图适配器（与 LeafletAdapter 接口一致）。
// Mapbox GL 原生使用 [lng, lat]，与本项目对外坐标一致，无需翻转。
// 运行时从 CDN 加载；需访问令牌 import.meta.env.VITE_MAPBOX_TOKEN。
import MapAdapter from './MapAdapter'

const GL_JS = 'https://api.mapbox.com/mapbox-gl-js/v3.6.0/mapbox-gl.js'
const GL_CSS = 'https://api.mapbox.com/mapbox-gl-js/v3.6.0/mapbox-gl.css'

let _loading = null
function loadMapbox() {
  if (window.mapboxgl) return Promise.resolve(window.mapboxgl)
  if (_loading) return _loading
  _loading = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${GL_CSS}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'; link.href = GL_CSS
      document.head.appendChild(link)
    }
    const s = document.createElement('script')
    s.src = GL_JS; s.async = true
    s.onload = () => resolve(window.mapboxgl)
    s.onerror = () => reject(new Error('Mapbox GL 加载失败（可能离线）'))
    document.head.appendChild(s)
  })
  return _loading
}

export default class MapboxAdapter extends MapAdapter {
  constructor() {
    super()
    this.map = null; this.gl = null
    this.markers = []; this.sourceIds = []; this._seq = 0
  }

  get ready() { return !!this.map && this.map.isStyleLoaded() }

  async init(container, options = {}) {
    const gl = await loadMapbox()
    this.gl = gl
    const token = import.meta.env.VITE_MAPBOX_TOKEN
    if (!token) throw new Error('缺少 VITE_MAPBOX_TOKEN')
    gl.accessToken = token
    this.map = new gl.Map({
      container,
      style: options.style || 'mapbox://styles/mapbox/light-v11',
      center: options.center || [34, 29.5],
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
    return {
      raw: marker,
      openPopup: () => { if (popup && !popup.isOpen()) marker.togglePopup() },
    }
  }

  addRoute(coordinates, options = {}) {
    if (!this.map) return null
    const id = `route-${++this._seq}`
    this.map.addSource(id, {
      type: 'geojson',
      data: { type: 'Feature', geometry: { type: 'LineString', coordinates } },
    })
    this.map.addLayer({
      id, type: 'line', source: id,
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': options.color ?? '#ffd700',
        'line-width': options.weight ?? 3,
        'line-opacity': options.opacity ?? 0.85,
        'line-dasharray': [2, 2],
      },
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
    this.map.addSource(id, { type: 'geojson', data: geojson })
    this.map.addLayer({ id, type: options.type || 'fill', source: id, paint: options.paint || {} })
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
