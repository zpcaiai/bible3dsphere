// Cesium 3D 实现的地图适配器（与 LeafletAdapter / MapboxAdapter 接口一致）。
// 运行时从 CDN 加载 CesiumJS；默认用 OpenStreetMap 影像，免 Ion 令牌即可运行。
// 若提供 import.meta.env.VITE_CESIUM_TOKEN 则启用 Ion（可换世界地形）。
// 对外坐标 [lng, lat]，与 Cesium 的 fromDegrees(lng, lat) 一致。
import MapAdapter from './MapAdapter'

const VER = '1.118'
const BASE = `https://cdn.jsdelivr.net/npm/cesium@${VER}/Build/Cesium/`
const JS = BASE + 'Cesium.js'
const CSS = BASE + 'Widgets/widgets.css'

let _loading = null
function loadCesium() {
  if (window.Cesium) return Promise.resolve(window.Cesium)
  if (_loading) return _loading
  window.CESIUM_BASE_URL = BASE
  _loading = new Promise((resolve, reject) => {
    if (!document.querySelector(`link[href="${CSS}"]`)) {
      const link = document.createElement('link')
      link.rel = 'stylesheet'; link.href = CSS
      document.head.appendChild(link)
    }
    const s = document.createElement('script')
    s.src = JS; s.async = true
    s.onload = () => resolve(window.Cesium)
    s.onerror = () => reject(new Error('CesiumJS 加载失败（可能离线）'))
    document.head.appendChild(s)
  })
  return _loading
}

const heightForZoom = (zoom) => Math.max(800, 50000000 / Math.pow(2, zoom ?? 6))

export default class CesiumAdapter extends MapAdapter {
  constructor() {
    super()
    this.viewer = null; this.Cesium = null; this._handler = null
  }

  get ready() { return !!this.viewer }

  async init(container, options = {}) {
    const Cesium = await loadCesium()
    this.Cesium = Cesium
    const token = import.meta.env.VITE_CESIUM_TOKEN
    if (token) Cesium.Ion.defaultAccessToken = token

    this.viewer = new Cesium.Viewer(container, {
      baseLayer: false,
      baseLayerPicker: false, geocoder: false, timeline: false, animation: false,
      homeButton: false, sceneModePicker: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: true, selectionIndicator: true,
    })
    // OpenStreetMap 影像（免 Ion）
    this.viewer.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({
      url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      maximumLevel: 19, credit: 'OpenStreetMap',
    }))
    this.viewer.scene.globe.enableLighting = false

    const c = options.center || [34, 31]
    this.viewer.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(c[0], c[1], heightForZoom(options.zoom)) })

    // 点击标记 → 触发其 onClick
    this._handler = new Cesium.ScreenSpaceEventHandler(this.viewer.scene.canvas)
    this._handler.setInputAction((movement) => {
      const picked = this.viewer.scene.pick(movement.position)
      if (picked && picked.id && typeof picked.id._onClick === 'function') picked.id._onClick()
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)
    return this
  }

  setView(lngLat, zoom, animate = true) {
    if (!this.viewer) return
    const C = this.Cesium
    this.viewer.camera.flyTo({
      destination: C.Cartesian3.fromDegrees(lngLat[0], lngLat[1], heightForZoom(zoom)),
      duration: animate ? 1.1 : 0,
    })
  }

  fitBounds(bounds, options = {}) {
    if (!this.viewer) return
    const C = this.Cesium
    let [[w, s], [e, n]] = bounds
    if (Math.abs(e - w) < 0.02) { w -= 0.05; e += 0.05 }
    if (Math.abs(n - s) < 0.02) { s -= 0.05; n += 0.05 }
    this.viewer.camera.flyTo({ destination: C.Rectangle.fromDegrees(w, s, e, n), duration: options.duration ?? 0.8 })
  }

  addMarker(lngLat, options = {}) {
    if (!this.viewer) return null
    const C = this.Cesium
    const { label, color = '#fbbf24', onClick, html, active } = options
    const ent = this.viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lngLat[0], lngLat[1]),
      point: {
        pixelSize: active ? 14 : 10,
        color: C.Color.fromCssColorString(color),
        outlineColor: C.Color.WHITE, outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: (label !== '' && label != null) ? {
        text: String(label), font: 'bold 11px sans-serif',
        fillColor: C.Color.BLACK, showBackground: false,
        verticalOrigin: C.VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      } : undefined,
      description: html || undefined,
    })
    if (onClick) ent._onClick = onClick
    return { raw: ent, openPopup: () => { this.viewer.selectedEntity = ent } }
  }

  addRoute(coordinates, options = {}) {
    if (!this.viewer) return null
    const C = this.Cesium
    const flat = coordinates.flat()
    const ent = this.viewer.entities.add({
      polyline: {
        positions: C.Cartesian3.fromDegreesArray(flat),
        width: options.weight ?? 3,
        material: C.Color.fromCssColorString(options.color ?? '#ffd700'),
        clampToGround: true,
      },
    })
    return ent
  }

  showPopup(lngLat, html) {
    if (!this.viewer) return
    const C = this.Cesium
    const ent = this.viewer.entities.add({
      position: C.Cartesian3.fromDegrees(lngLat[0], lngLat[1]),
      point: { pixelSize: 1, color: C.Color.TRANSPARENT },
      description: html,
    })
    this.viewer.selectedEntity = ent
  }

  renderGeoJson(geojson, options = {}) {
    if (!this.viewer) return null
    const C = this.Cesium
    const feat = geojson.type === 'Feature' ? geojson : { geometry: geojson }
    const g = feat.geometry
    if (!g) return null
    const c = options.style?.fillColor || options.paint?.['fill-color'] || '#ffd700'
    const col = C.Color.fromCssColorString(c)
    if (g.type === 'Polygon') {
      const ring = g.coordinates[0]
      return this.viewer.entities.add({
        polygon: {
          hierarchy: C.Cartesian3.fromDegreesArray(ring.flat()),
          material: col.withAlpha(options.style?.fillOpacity ?? 0.32),
          outline: true, outlineColor: col, height: 0,
        },
      })
    }
    if (g.type === 'LineString') {
      return this.addRoute(g.coordinates, { color: c, weight: options.style?.weight ?? 2 })
    }
    return null
  }

  clear() {
    if (this.viewer) this.viewer.entities.removeAll()
  }

  destroy() {
    if (this._handler) { this._handler.destroy(); this._handler = null }
    if (this.viewer && !this.viewer.isDestroyed()) this.viewer.destroy()
    this.viewer = null
  }
}
