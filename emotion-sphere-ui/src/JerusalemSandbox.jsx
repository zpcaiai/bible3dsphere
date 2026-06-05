// JerusalemSandbox.jsx — 耶路撒冷数字孪生时空微缩沙盘
// Mapbox GL JS v3（有 VITE_MAPBOX_TOKEN 时）；否则 / 配额耗尽(401/403/429) 自动回退 MapLibre GL JS v1（免 token）。
// 核心：固定视角圣殿山 · 时间轴剥离各时期 · 3D fill-extrusion 平地起高楼 · 受难周 FPV 相机巡游。
// 库与瓦片均从 CDN 动态加载（需联网）。
import { useEffect, useRef, useState } from 'react'
import { JERU_ERAS, TEMPLE_CENTER, PASSION_WEEK, eraGeoJSON, locationsFor, JERU_LOCATIONS } from './data/jerusalemChronology'
import { TEMPLE_GEOJSON, TEMPLE_PARTS, TEMPLE_LABELS, TEMPLE_CAMERA } from './data/templeStructure'

const TOKEN = (import.meta.env && (import.meta.env.NEXT_PUBLIC_MAPBOX_TOKEN || import.meta.env.VITE_MAPBOX_TOKEN)) || ''
const MAPBOX_VER = '3.7.0'
const MAPLIBRE_VER = '1.15.2'
// 经 jsDelivr 加载（已在站点 CSP script-src 白名单内）；GL 库会创建 blob worker，需 CSP worker-src blob:
const CDN = {
  mapboxJs: `https://cdn.jsdelivr.net/npm/mapbox-gl@${MAPBOX_VER}/dist/mapbox-gl.js`,
  mapboxCss: `https://cdn.jsdelivr.net/npm/mapbox-gl@${MAPBOX_VER}/dist/mapbox-gl.css`,
  maplibreJs: `https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.js`,
  maplibreCss: `https://cdn.jsdelivr.net/npm/maplibre-gl@${MAPLIBRE_VER}/dist/maplibre-gl.css`,
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if ([...document.scripts].some(s => s.src === src)) return resolve()
    const el = document.createElement('script')
    el.src = src; el.async = true
    el.onload = () => resolve()
    el.onerror = () => reject(new Error('脚本加载失败：' + src))
    document.head.appendChild(el)
  })
}
// 用 fetch 取 CSS 文本并注入 <style>，避免依赖 CSP style-src 允许外部域
async function loadCss(href) {
  if (document.querySelector(`style[data-href="${href}"]`)) return
  try {
    const txt = await fetch(href).then(r => r.text())
    const st = document.createElement('style'); st.setAttribute('data-href', href); st.textContent = txt
    document.head.appendChild(st)
  } catch (_) {
    // 退而求其次：直接用 <link>（若 CSP 允许）
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l)
  }
}

// MapLibre 免 token 样式：暗色背景 + 可选 OSM 栅格（低饱和暗化）
const MAPLIBRE_STYLE = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png', 'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png', 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256, maxzoom: 19, attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#0e1726' } },
    { id: 'osm', type: 'raster', source: 'osm', layout: { visibility: 'none' }, paint: { 'raster-opacity': 0.5, 'raster-saturation': -0.7, 'raster-brightness-max': 0.7 } },
  ],
}

function bearing(a, b) {
  const r = Math.PI / 180
  const dLon = (b[0] - a[0]) * r
  const y = Math.sin(dLon) * Math.cos(b[1] * r)
  const x = Math.cos(a[1] * r) * Math.sin(b[1] * r) - Math.sin(a[1] * r) * Math.cos(b[1] * r) * Math.cos(dLon)
  return (Math.atan2(y, x) * 180) / Math.PI
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms))

export default function JerusalemSandbox({ onBack }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const glRef = useRef(null)
  const markersRef = useRef([])
  const passionMarkerRef = useRef(null)
  const triedFallbackRef = useRef(false)
  const passionRunRef = useRef(false)
  const eraIdxRef = useRef(0)

  const [engine, setEngine] = useState(TOKEN ? 'mapbox' : 'maplibre')
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [errMsg, setErrMsg] = useState('')
  const [eraIdx, setEraIdx] = useState(JERU_ERAS.findIndex(e => e.id === 'herod') >= 0 ? JERU_ERAS.findIndex(e => e.id === 'herod') : 0)
  const [selectedLoc, setSelectedLoc] = useState(null)
  const [passionStop, setPassionStop] = useState(-1)
  const [passionActive, setPassionActive] = useState(false)
  const [showOsm, setShowOsm] = useState(false)
  // —— 圣殿3D结构模式 ——
  const [templeMode, setTempleMode] = useState(false)
  const [cutaway, setCutaway] = useState(true)
  const [selectedPart, setSelectedPart] = useState(null)
  const templeMarkersRef = useRef([])
  const templeModeRef = useRef(false)

  const era = JERU_ERAS[eraIdx]
  eraIdxRef.current = eraIdx

  // —— 初始化地图（含回退）——
  useEffect(() => {
    let disposed = false

    async function boot(eng) {
      try {
        setStatus('loading')
        if (eng === 'mapbox') {
          loadCss(CDN.mapboxCss); await loadScript(CDN.mapboxJs)
          if (disposed) return
          const gl = window.mapboxgl
          gl.accessToken = TOKEN
          const map = new gl.Map({
            container: containerRef.current,
            style: 'mapbox://styles/mapbox/satellite-streets-v12',
            center: TEMPLE_CENTER, zoom: 15.4, pitch: 62, bearing: -22, antialias: true,
          })
          glRef.current = gl; mapRef.current = map
          map.on('error', (e) => {
            const st = e && e.error && e.error.status
            const msg = (e && e.error && e.error.message) || ''
            if (!triedFallbackRef.current && (st === 401 || st === 403 || st === 429 || /access token|unauthorized|quota|rate limit/i.test(msg))) {
              triedFallbackRef.current = true
              try { map.remove() } catch (_) {}
              setEngine('maplibre'); boot('maplibre')
            }
          })
          map.on('load', () => { if (!disposed) onMapReady(gl, map, 'mapbox') })
        } else {
          loadCss(CDN.maplibreCss); await loadScript(CDN.maplibreJs)
          if (disposed) return
          const gl = window.maplibregl
          const map = new gl.Map({
            container: containerRef.current,
            style: MAPLIBRE_STYLE,
            center: TEMPLE_CENTER, zoom: 15.4, pitch: 60, bearing: -22, antialias: true,
          })
          glRef.current = gl; mapRef.current = map
          map.on('load', () => { if (!disposed) onMapReady(gl, map, 'maplibre') })
        }
      } catch (e) {
        if (eng === 'mapbox' && !triedFallbackRef.current) {
          triedFallbackRef.current = true; setEngine('maplibre'); boot('maplibre')
        } else {
          setStatus('error'); setErrMsg(e.message || '地图加载失败（请检查网络）')
        }
      }
    }

    boot(TOKEN ? 'mapbox' : 'maplibre')
    return () => {
      disposed = true; passionRunRef.current = false
      clearMarkers()
      if (mapRef.current) { try { mapRef.current.remove() } catch (_) {} mapRef.current = null }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function clearMarkers() {
    markersRef.current.forEach(m => { try { m.remove() } catch (_) {} })
    markersRef.current = []
  }

  // —— 地图就绪：建立图层 + 首次渲染当前时期 ——
  function onMapReady(gl, map, eng) {
    try {
      map.addControl(new gl.NavigationControl({ visualizePitch: true }), 'top-left')
    } catch (_) {}
    // 可选地形（仅 Mapbox）
    if (eng === 'mapbox') {
      try {
        map.addSource('dem', { type: 'raster-dem', url: 'mapbox://mapbox.mapbox-terrain-dem-v1', tileSize: 512, maxzoom: 14 })
        map.setTerrain({ source: 'dem', exaggeration: 1.2 })
      } catch (_) {}
    }
    const g0 = eraGeoJSON(era.id)
    map.addSource('jeru-poly', { type: 'geojson', data: g0.polygons })
    map.addSource('jeru-wall', { type: 'geojson', data: g0.walls })

    map.addLayer({
      id: 'jeru-fill', type: 'fill-extrusion', source: 'jeru-poly',
      paint: {
        'fill-extrusion-color': ['coalesce', ['get', 'fill'], '#9a8b5a'],
        'fill-extrusion-height': ['coalesce', ['get', 'height'], 0],
        'fill-extrusion-base': 0,
        'fill-extrusion-opacity': 0.86,
      },
    })
    map.addLayer({
      id: 'jeru-wall-line', type: 'line', source: 'jeru-wall',
      paint: { 'line-color': '#e8b04b', 'line-width': 3, 'line-opacity': 0.9, 'line-dasharray': [2, 1.5] },
    })

    // 圣殿精细结构（默认隐藏，进入圣殿模式时显示）
    try {
      map.addSource('temple', { type: 'geojson', data: TEMPLE_GEOJSON })
      map.addLayer({
        id: 'temple-fill', type: 'fill-extrusion', source: 'temple',
        layout: { visibility: 'none' },
        paint: {
          'fill-extrusion-color': ['get', 'color'],
          'fill-extrusion-base': ['get', 'base'],
          'fill-extrusion-height': ['get', 'height'],
          'fill-extrusion-opacity': 0.95,
        },
      })
      map.on('click', 'temple-fill', (e) => {
        const f = e.features && e.features[0]
        if (f && f.properties && TEMPLE_PARTS[f.properties.id]) {
          setSelectedPart({ id: f.properties.id, ...TEMPLE_PARTS[f.properties.id] })
        }
      })
      map.on('mouseenter', 'temple-fill', () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', 'temple-fill', () => { map.getCanvas().style.cursor = '' })
    } catch (_) {}

    addMarkers(gl, map, era.id)
    setStatus('ready')
    riseTween()
  }

  // —— 关键地点 + 建筑名 DOM 标注（避免字形依赖，两引擎通用）——
  function addMarkers(gl, map, eraId) {
    clearMarkers()
    // 地点
    locationsFor(eraId).features.forEach(f => {
      const p = f.properties
      const el = document.createElement('div')
      el.className = 'jeru-marker'
      el.innerHTML = `<span class="jeru-pin"></span><span class="jeru-mlabel">${p.name_zh}</span>`
      el.onclick = (ev) => { ev.stopPropagation(); setSelectedLoc(JERU_LOCATIONS.find(l => l.id === p.id)) }
      const mk = new gl.Marker({ element: el, anchor: 'bottom' }).setLngLat(f.geometry.coordinates).addTo(map)
      markersRef.current.push(mk)
    })
    // 圣殿/建筑名（圣所类）
    eraGeoJSON(eraId).polygons.features.filter(f => f.properties.sacred || f.properties.kind === 'temple' || f.properties.kind === 'fortress').forEach(f => {
      const ring = f.geometry.coordinates[0].slice(0, -1)
      const c = ring.reduce((a, p) => [a[0] + p[0], a[1] + p[1]], [0, 0]).map(v => v / ring.length)
      const el = document.createElement('div'); el.className = 'jeru-structlabel'; el.textContent = f.properties.name
      const mk = new gl.Marker({ element: el, anchor: 'center' }).setLngLat(c).addTo(map)
      markersRef.current.push(mk)
    })
  }

  // —— 3D 平地起高楼：高度从 0 增长到目标 ——
  function riseTween() {
    const map = mapRef.current; if (!map || !map.getLayer || !map.getLayer('jeru-fill')) return
    const start = performance.now(); const dur = 900
    const heightExpr = ['coalesce', ['get', 'height'], 0]
    const step = (t) => {
      const k = Math.min(1, (t - start) / dur)
      const e = 1 - Math.pow(1 - k, 3) // easeOutCubic
      try { map.setPaintProperty('jeru-fill', 'fill-extrusion-height', ['*', heightExpr, e]) } catch (_) {}
      if (k < 1 && mapRef.current) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }

  // —— 切换时期 ——
  useEffect(() => {
    const map = mapRef.current; const gl = glRef.current
    if (!map || status !== 'ready' || !map.getSource) return
    if (!map.getSource('jeru-poly')) return
    // 切换时期时自动退出圣殿模式，恢复城市图层
    if (templeModeRef.current) {
      templeModeRef.current = false; setTempleMode(false); setSelectedPart(null)
      try {
        map.setLayoutProperty('temple-fill', 'visibility', 'none')
        map.setLayoutProperty('jeru-fill', 'visibility', 'visible')
        map.setLayoutProperty('jeru-wall-line', 'visibility', 'visible')
      } catch (_) {}
      clearTempleMarkers()
      map.easeTo({ zoom: 15.4, pitch: 60, bearing: -22, duration: 900 })
    }
    const g = eraGeoJSON(era.id)
    try {
      map.getSource('jeru-poly').setData(g.polygons)
      map.getSource('jeru-wall').setData(g.walls)
    } catch (_) {}
    addMarkers(gl, map, era.id)
    setSelectedLoc(null)
    riseTween()
    map.easeTo({ center: TEMPLE_CENTER, duration: 800 })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eraIdx, status])

  // —— OSM 底图开关（仅 MapLibre）——
  useEffect(() => {
    const map = mapRef.current
    if (!map || engine !== 'maplibre' || !map.getLayer || !map.getLayer('osm')) return
    try { map.setLayoutProperty('osm', 'visibility', showOsm ? 'visible' : 'none') } catch (_) {}
  }, [showOsm, engine, status])

  function resetView() {
    const map = mapRef.current; if (!map) return
    map.easeTo({ center: TEMPLE_CENTER, zoom: 15.4, pitch: 60, bearing: -22, duration: 900 })
  }

  // —— 圣殿3D结构模式 ——
  function clearTempleMarkers() {
    templeMarkersRef.current.forEach(m => { try { m.remove() } catch (_) {} })
    templeMarkersRef.current = []
  }
  function enterTemple() {
    const map = mapRef.current, gl = glRef.current
    if (!map || !map.getLayer || !map.getLayer('temple-fill')) return
    passionRunRef.current = false; setPassionActive(false)
    templeModeRef.current = true; setTempleMode(true); setSelectedLoc(null)
    try {
      map.setLayoutProperty('jeru-fill', 'visibility', 'none')
      map.setLayoutProperty('jeru-wall-line', 'visibility', 'none')
      map.setLayoutProperty('temple-fill', 'visibility', 'visible')
      map.setFilter('temple-fill', cutaway ? ['!=', ['get', 'cut'], 1] : null)
    } catch (_) {}
    clearMarkers()
    clearTempleMarkers()
    TEMPLE_LABELS.forEach(l => {
      const el = document.createElement('div'); el.className = 'jeru-structlabel'; el.textContent = l.name
      el.style.pointerEvents = 'auto'; el.style.cursor = 'pointer'
      el.onclick = (ev) => { ev.stopPropagation(); if (TEMPLE_PARTS[l.id]) setSelectedPart({ id: l.id, ...TEMPLE_PARTS[l.id] }) }
      const mk = new gl.Marker({ element: el, anchor: 'center' }).setLngLat(l.coord).addTo(map)
      templeMarkersRef.current.push(mk)
    })
    map.flyTo({ center: TEMPLE_CAMERA.center, zoom: TEMPLE_CAMERA.zoom, pitch: TEMPLE_CAMERA.pitch, bearing: TEMPLE_CAMERA.bearing, duration: 2200, essential: true })
  }
  function exitTemple() {
    const map = mapRef.current, gl = glRef.current
    templeModeRef.current = false; setTempleMode(false); setSelectedPart(null)
    if (!map) return
    try {
      map.setLayoutProperty('temple-fill', 'visibility', 'none')
      map.setLayoutProperty('jeru-fill', 'visibility', 'visible')
      map.setLayoutProperty('jeru-wall-line', 'visibility', 'visible')
    } catch (_) {}
    clearTempleMarkers()
    if (gl) addMarkers(gl, map, era.id)
    resetView()
  }
  // 剖视开关
  useEffect(() => {
    const map = mapRef.current
    if (!map || !templeMode || !map.getLayer || !map.getLayer('temple-fill')) return
    try { map.setFilter('temple-fill', cutaway ? ['!=', ['get', 'cut'], 1] : null) } catch (_) {}
  }, [cutaway, templeMode])

  // —— 受难周 FPV 巡游 ——
  async function playPassion() {
    const map = mapRef.current, gl = glRef.current
    if (!map || passionRunRef.current) return
    // 受难周属希律时期，先切过去
    const herodIdx = JERU_ERAS.findIndex(e => e.id === 'herod')
    if (eraIdxRef.current !== herodIdx) { setEraIdx(herodIdx); await sleep(900) }
    passionRunRef.current = true; setPassionActive(true)
    if (!passionMarkerRef.current) {
      const el = document.createElement('div'); el.className = 'jeru-pilgrim'; el.textContent = '🚶'
      passionMarkerRef.current = new gl.Marker({ element: el, anchor: 'bottom' })
    }
    passionMarkerRef.current.setLngLat(PASSION_WEEK[0].coord).addTo(map)
    for (let i = 0; i < PASSION_WEEK.length; i++) {
      if (!passionRunRef.current) break
      const stop = PASSION_WEEK[i]
      const next = PASSION_WEEK[Math.min(i + 1, PASSION_WEEK.length - 1)]
      const br = i < PASSION_WEEK.length - 1 ? bearing(stop.coord, next.coord) : map.getBearing()
      setPassionStop(i)
      passionMarkerRef.current.setLngLat(stop.coord)
      map.easeTo({ center: stop.coord, zoom: 17, pitch: 72, bearing: br, duration: 2600, essential: true })
      await sleep(3100)
    }
    passionRunRef.current = false; setPassionActive(false)
  }
  function stopPassion() {
    passionRunRef.current = false; setPassionActive(false); setPassionStop(-1)
    if (passionMarkerRef.current) { try { passionMarkerRef.current.remove() } catch (_) {} }
    resetView()
  }
  function jumpStop(i) {
    const map = mapRef.current, gl = glRef.current; if (!map) return
    const stop = PASSION_WEEK[i]
    if (!passionMarkerRef.current) {
      const el = document.createElement('div'); el.className = 'jeru-pilgrim'; el.textContent = '🚶'
      passionMarkerRef.current = new gl.Marker({ element: el, anchor: 'bottom' })
    }
    passionMarkerRef.current.setLngLat(stop.coord).addTo(map)
    setPassionStop(i)
    map.easeTo({ center: stop.coord, zoom: 17, pitch: 72, duration: 1600 })
  }

  return (
    <div className="jeru">
      <div className="biblemap-head">
        <button className="biblemap-back" onClick={onBack}>← 返回</button>
        <div className="biblemap-title">
          <h2>🏛 耶路撒冷数字孪生沙盘</h2>
          <p>圣城变迁与圣殿结构 · 时间轴剥离 · 受难周 FPV 步行 · {engine === 'mapbox' ? 'Mapbox GL v3' : 'MapLibre GL v1（免 token）'}</p>
        </div>
      </div>

      {/* 时间轴：六个时期 */}
      <div className="jeru-timeline">
        {JERU_ERAS.map((e, i) => (
          <button key={e.id} className={`jeru-era ${i === eraIdx ? 'on' : ''}`} onClick={() => setEraIdx(i)}>
            <span className="y">{e.year < 0 ? `前${Math.abs(e.year)}` : e.year}</span>
            <span className="l">{e.label}</span>
          </button>
        ))}
      </div>

      <div className="jeru-stage">
        <div ref={containerRef} className="jeru-map" />
        {status !== 'ready' && (
          <div className="jeru-overlay">
            {status === 'loading' && <div className="jeru-loading">🌍 正在加载{engine === 'mapbox' ? ' Mapbox' : ' MapLibre'} 三维沙盘…</div>}
            {status === 'error' && (
              <div className="jeru-err">
                <p>⚠ {errMsg}</p>
                <p className="dim">该功能需要联网加载地图库与瓦片。若 Mapbox 配额/令牌不可用，会自动回退到免费的 MapLibre。</p>
              </div>
            )}
          </div>
        )}

        {/* 控制条 */}
        <div className="jeru-controls">
          <button onClick={resetView} title="复位到圣殿山视角">🎯 复位视角</button>
          {!passionActive
            ? <button className="primary" onClick={playPassion}>✝ 受难周 FPV 巡游</button>
            : <button className="primary" onClick={stopPassion}>⏹ 停止巡游</button>}
          {engine === 'maplibre' && (
            <button className={showOsm ? 'on' : ''} onClick={() => setShowOsm(s => !s)}>🗺 现代底图</button>
          )}
          {status === 'ready' && (!templeMode
            ? <button className="primary" onClick={enterTemple}>🏛 圣殿3D结构</button>
            : <>
                <button className={cutaway ? 'on' : ''} onClick={() => setCutaway(c => !c)}>✂ 剖视{cutaway ? '·开' : '·关'}</button>
                <button onClick={exitTemple}>🚪 离开圣殿</button>
              </>)}
        </div>
      </div>

      {/* 时期说明 */}
      <div className="jeru-erainfo" style={{ borderColor: '#e8b04b55' }}>
        <div className="jeru-erainfo-h">
          <strong>{era.label}</strong>
          <span className="en">{era.en}</span>
          <span className="ref">{era.ref}</span>
        </div>
        <p>{era.desc}</p>
      </div>

      {/* 受难周分站 */}
      <div className="jeru-passion">
        <div className="jeru-passion-h">✝ 受难周步行轨迹（希律时期 · 点击任一站定位）</div>
        <div className="jeru-stops">
          {PASSION_WEEK.map((s, i) => (
            <button key={i} className={`jeru-stop ${passionStop === i ? 'on' : ''}`} onClick={() => jumpStop(i)}>
              <span className="d">{s.day}</span><span className="t">{s.title}</span>
            </button>
          ))}
        </div>
        {passionStop >= 0 && (
          <div className="jeru-stopdetail">
            <div className="h"><strong>{PASSION_WEEK[passionStop].title}</strong><span className="ref">{PASSION_WEEK[passionStop].ref}</span></div>
            <p>{PASSION_WEEK[passionStop].summary}</p>
          </div>
        )}
      </div>

      {/* 圣殿模式提示 */}
      {templeMode && (
        <div className="jeru-temple-hint">
          🏛 所罗门第一圣殿（王上6–7，按肘比例示意复原）· 点击任一部件看经文与尺寸 · ✂ 剖视揭开殿顶察看圣所与至圣所
        </div>
      )}

      {/* 圣殿部件详情 */}
      {selectedPart && (
        <div className="jeru-locdetail" style={{ borderColor: 'rgba(232,176,75,0.55)' }}>
          <button className="x" onClick={() => setSelectedPart(null)}>×</button>
          <div className="h"><strong>{selectedPart.name}</strong><span className="ref">{selectedPart.ref}</span></div>
          {selectedPart.dims && <p className="jeru-part-dims">📐 {selectedPart.dims}</p>}
          <p>{selectedPart.desc}</p>
        </div>
      )}

      {/* 地点详情 */}
      {selectedLoc && (
        <div className="jeru-locdetail">
          <button className="x" onClick={() => setSelectedLoc(null)}>×</button>
          <div className="h"><strong>{selectedLoc.name_zh}</strong><span className="en">{selectedLoc.name_en}</span><span className="ref">{selectedLoc.ref}</span></div>
          <p>{selectedLoc.note}</p>
        </div>
      )}

      <div className="jeru-foot">
        城墙与建筑轮廓为示意性复原（schematic），用于教学呈现各时期相对范围与圣殿"平地起高楼"，非精确考古测绘。
        {engine === 'maplibre' && !TOKEN && ' · 当前为免费 MapLibre 模式；配置 VITE_MAPBOX_TOKEN 可启用 Mapbox 卫星底图。'}
      </div>
    </div>
  )
}
