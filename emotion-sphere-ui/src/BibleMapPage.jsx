import { useEffect, useRef, useState, useCallback } from 'react'
import { createMapAdapter } from './map/createMapAdapter'
import { loadBibleMap, BIBLE_MAPS, confidenceMeta, fetchTimeSlice, fetchRegions, fetchRelations, fetchLandmarks, landmarkNoteBySlug } from './data/bibleGeoSource'

function popupHtml(p, cm, order) {
  return `<div class="biblemap-pop">
    <div class="biblemap-pop-no">第 ${order} 站 · ${p.scriptureRef || ''}</div>
    <div class="biblemap-pop-name">${p.name_zh}</div>
    <div class="biblemap-pop-en">${p.name_en || ''}</div>
    <div class="biblemap-pop-conf" style="color:${cm.color}">● ${cm.label}</div>
  </div>`
}

function coordsFor(feature, variant) {
  const ov = variant?.overrides?.[feature.properties.id]
  return ov || feature.geometry?.coordinates
}

// 语音朗读（SpeechSynthesis，免素材、离线可用）
function speak(text) {
  try {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'zh-CN'
    window.speechSynthesis.speak(u)
  } catch (e) { /* ignore */ }
}

function orderedStations(dataset, variant) {
  if (!dataset || dataset.temporal || !dataset.stations) return []
  if (variant?.stationIds) {
    const byId = new Map(dataset.stations.map((f) => [f.properties.id, f]))
    return variant.stationIds.map((id) => byId.get(id)).filter(Boolean)
  }
  return dataset.stations.slice().sort((a, b) => (a.properties.order || 0) - (b.properties.order || 0))
}

function eraOf(eras, year) {
  return eras.find((e) => year >= e.start && year < e.end) || eras[eras.length - 1]
}
const REL_LABEL = { within: '隶属于', contains: '包含', adjacent: '相邻', capital_of: '首都：', borders: '接壤' }

export default function BibleMapPage() {
  const mapRef = useRef(null)
  const adapterRef = useRef(null)
  const markersRef = useRef({})
  const playRef = useRef(null)
  const selectedRef = useRef(null)

  const [datasetId, setDatasetId] = useState('exodus')
  const [dataset, setDataset] = useState(null)
  const [variantId, setVariantId] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [year, setYear] = useState(-1000)       // 时间轴（温度场数据集用）
  const [slice, setSlice] = useState(null)       // 当前年份切片
  const [mapError, setMapError] = useState('')
  const [ready, setReady] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [regionRel, setRegionRel] = useState(null)

  // 加载数据集
  useEffect(() => {
    let cancelled = false
    setDataset(null)
    loadBibleMap(datasetId).then((ds) => {
      if (cancelled) return
      setDataset(ds)
      if (ds.temporal) {
        setYear(Math.round((ds.eras[0].start + ds.eras[Math.min(2, ds.eras.length - 1)].end) / 2))
      } else {
        setVariantId(ds.defaultVariantId)
        const stn = orderedStations(ds, ds.variants.find((v) => v.id === ds.defaultVariantId))
        setSelectedId(stn[0]?.properties.id || null)
        selectedRef.current = stn[0] || null
      }
    })
    return () => { cancelled = true }
  }, [datasetId])

  // 初始化地图（一次）
  useEffect(() => {
    let cancelled = false
    const adapter = createMapAdapter()
    adapterRef.current = adapter
    adapter
      .init(mapRef.current, { center: [34, 31], zoom: 5, scrollWheelZoom: false })
      .then(() => { if (cancelled) { adapter.destroy() } else setReady(true) })
      .catch((e) => { if (!cancelled) setMapError(e.message || '地图加载失败') })
    return () => {
      cancelled = true
      if (playRef.current) clearInterval(playRef.current)
      adapter.destroy()
    }
  }, [])

  const variant = dataset && !dataset.temporal ? (dataset.variants.find((v) => v.id === variantId) || dataset.variants[0]) : null
  const STN = orderedStations(dataset, variant)
  const selected = STN.find((s) => s.properties.id === selectedId) || STN[0] || null
  useEffect(() => { selectedRef.current = selected }, [selected])

  const selectStation = useCallback((f, fromMarker = false) => {
    setSelectedId(f.properties.id)
    selectedRef.current = f
    const ad = adapterRef.current
    if (ad?.ready) {
      ad.setView(coordsFor(f, variant), variant?.stationIds ? 6 : 8)
      const m = markersRef.current[f.properties.id]
      if (m && m.openPopup) setTimeout(() => m.openPopup(), fromMarker ? 0 : 250)
    }
  }, [variant])

  // 渲染图层（旅程/路线模式）
  useEffect(() => {
    const ad = adapterRef.current
    if (!ad?.ready || !dataset || dataset.temporal || !variant || !STN.length) return
    ad.clear()
    markersRef.current = {}
    if (variant.route?.length) ad.addRoute(variant.route, { color: variant.color, weight: 3 })
    STN.forEach((f, i) => {
      const cm = confidenceMeta[f.properties.confidence] || confidenceMeta.unknown
      const m = ad.addMarker(coordsFor(f, variant), {
        label: i + 1, color: cm.color,
        active: selectedRef.current && selectedRef.current.properties.id === f.properties.id,
        html: popupHtml(f.properties, cm, i + 1),
        onClick: () => selectStation(f, true),
      })
      markersRef.current[f.properties.id] = m
    })
    const coords = STN.map((f) => coordsFor(f, variant)).filter(Boolean)
    const lngs = coords.map((c) => c[0]); const lats = coords.map((c) => c[1])
    ad.fitBounds([[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, dataset, variantId])

  // 渲染图层（时间轴/疆域模式）
  useEffect(() => {
    const ad = adapterRef.current
    if (!ad?.ready || !dataset?.temporal) return
    let cancelled = false
    const era = eraOf(dataset.eras, year)
    ;(async () => {
      if (dataset.kind === 'regions') {
        const { fc, source } = await fetchRegions(year)
        if (cancelled) return
        ad.clear()
        const colors = dataset.colorBySlug || {}
        const allLng = [], allLat = []
        fc.features.forEach((f) => {
          const c = colors[f.properties.slug] || '#ffd700'
          ad.renderGeoJson(f, {
            style: { color: c, weight: 1.5, fillColor: c, fillOpacity: 0.32 },
            type: 'fill',
            paint: { 'fill-color': c, 'fill-opacity': 0.32, 'fill-outline-color': c },
          })
          const ring = f.geometry?.coordinates?.[0] || []
          ring.forEach(([lng, lat]) => { allLng.push(lng); allLat.push(lat) })
        })
        if (allLng.length) ad.fitBounds([[Math.min(...allLng), Math.min(...allLat)], [Math.max(...allLng), Math.max(...allLat)]], { maxZoom: 9 })
        setSlice({ era, source, regions: fc.features.map((f) => ({ slug: f.properties.slug, name_zh: f.properties.name_zh })) })
        setRegionRel(null)
        return
      }
      const api = await fetchTimeSlice(dataset.slug, year)
      if (cancelled) return
      const geometry = api?.geometry || { type: 'Polygon', coordinates: [era.polygon] }
      ad.clear()
      ad.renderGeoJson(
        { type: 'Feature', geometry, properties: {} },
        {
          style: { color: '#ffd700', weight: 2, fillColor: '#ffd700', fillOpacity: 0.25 },
          type: 'fill',
          paint: { 'fill-color': '#ffd700', 'fill-opacity': 0.25, 'fill-outline-color': '#ffd700' },
        },
      )
      ad.addMarker(dataset.point, { label: '', color: '#ffd700', active: true })
      const { fc: lmFc } = await fetchLandmarks(year)
      if (cancelled) return
      lmFc.features.forEach((f) => {
        const note = landmarkNoteBySlug[f.properties.slug] || ''
        ad.addMarker(f.geometry.coordinates, {
          label: '', color: '#22d3ee',
          html: `<div class="biblemap-pop"><div class="biblemap-pop-name">${f.properties.name_zh}</div><div class="biblemap-pop-en">${f.properties.name_en || ''}</div><div class="biblemap-pop-conf" style="color:#22d3ee">${note}</div></div>`,
        })
      })
      try {
        const ring = geometry.type === 'Polygon' ? geometry.coordinates[0] : [dataset.point]
        const lngs = ring.map((c) => c[0]); const lats = ring.map((c) => c[1])
        ad.fitBounds([[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]], { maxZoom: 14 })
      } catch (e) { /* ignore */ }
      setSlice({ name_zh: api?.name_zh || era.name_zh, name_en: api?.name_en || era.name_en, era, source: api ? 'api' : 'local', landmarks: lmFc.features.map((f) => ({ slug: f.properties.slug, name_zh: f.properties.name_zh })) })
    })()
    return () => { cancelled = true }
  }, [ready, dataset, year])

  function step(dir) {
    if (!selected) return
    const idx = STN.findIndex((s) => s.properties.id === selected.properties.id)
    let next = idx + dir
    if (next < 0) next = STN.length - 1
    if (next >= STN.length) next = 0
    selectStation(STN[next])
  }

  function togglePlay() {
    if (playing) { clearInterval(playRef.current); playRef.current = null; setPlaying(false); return }
    setPlaying(true)
    playRef.current = setInterval(() => {
      setSelectedId((curId) => {
        if (!STN.length) return curId
        const idx = STN.findIndex((s) => s.properties.id === curId)
        const nx = STN[(idx + 1) % STN.length]
        selectedRef.current = nx
        const ad = adapterRef.current
        if (ad?.ready) ad.setView(coordsFor(nx, variant), variant?.stationIds ? 6 : 8)
        return nx.properties.id
      })
    }, 2600)
  }

  function switchDataset(id) {
    if (id === datasetId) return
    setPlaying(false)
    if (playRef.current) { clearInterval(playRef.current); playRef.current = null }
    setSlice(null)
    setDatasetId(id)
  }

  if (!dataset) {
    return (
      <div className="biblemap-page">
        {/* Keep map container in DOM so mapRef is always available for Leaflet init */}
        <div style={{ visibility: 'hidden', pointerEvents: 'none' }}>
          <div className="biblemap-map-wrap"><div ref={mapRef} className="biblemap-map" /></div>
        </div>
        <div className="biblemap-loading">地图数据加载中…</div>
      </div>
    )
  }

  const DatasetSelector = (
    <div className="biblemap-dataset">
      {BIBLE_MAPS.map((m) => (
        <button key={m.id} className={`biblemap-dataset-btn ${m.id === datasetId ? 'active' : ''}`} onClick={() => switchDataset(m.id)}>
          <span className="biblemap-dataset-icon">{m.icon}</span>{m.title}
        </button>
      ))}
    </div>
  )

  const MapBox = (
    <div className="biblemap-map-wrap">
      <div ref={mapRef} className="biblemap-map" />
      {mapError && (
        <div className="biblemap-map-fallback">
          🗺️ 地图瓦片加载失败{mapError ? `（${mapError}）` : ''}<br />
          <span>可能处于离线状态，下方仍可浏览经文与时代信息</span>
        </div>
      )}
    </div>
  )

  // ── 时间轴 / 疆域模式 ──────────────────────────────────────────────
  if (dataset.temporal) {
    const era = eraOf(dataset.eras, year)
    const minY = dataset.eras[0].start
    const maxY = dataset.eras[dataset.eras.length - 1].end
    const yLabel = (y) => (y < 0 ? `公元前 ${-y}` : `公元 ${y}`)
    const eraEndLabel = era.end <= 0 ? yLabel(era.end) : `公元 ${era.end}`
    const colorBySlug = dataset.colorBySlug || {}
    return (
      <div className="biblemap-page">
        {DatasetSelector}
        <div className="biblemap-hypo-desc">{dataset.subtitle}
          <span className="biblemap-src">{slice?.source === 'api' ? '· 数据源：后端' : '· 数据源：本地'}</span>
        </div>
        {MapBox}
        <div className="biblemap-timeline">
          <div className="biblemap-year">{yLabel(year)}</div>
          <input
            type="range" className="biblemap-slider"
            min={minY} max={maxY - 1} step={10} value={year}
            onChange={(e) => setYear(parseInt(e.target.value, 10))}
          />
          <div className="biblemap-era-chips">
            {dataset.eras.map((e) => (
              <button key={e.id}
                className={`biblemap-era-chip ${e.id === era.id ? 'active' : ''}`}
                onClick={() => setYear(Math.round((e.start + e.end) / 2))}>
                {e.name_zh || e.label}
              </button>
            ))}
          </div>
        </div>
        <div className="biblemap-detail">
          <div className="biblemap-detail-head">
            <div className="biblemap-detail-no">{era.label} · {era.ref}</div>
            <div className="biblemap-detail-title">{dataset.kind === 'regions' ? era.label : (slice?.name_zh || era.name_zh)}</div>
            <div className="biblemap-detail-sub">{dataset.kind === 'regions'
              ? `${yLabel(era.start)} – ${eraEndLabel} · ${slice?.regions?.length || 0} 个疆域`
              : `${slice?.name_en || era.name_en} · ${yLabel(era.start)} – ${eraEndLabel}`}</div>
            <span className="biblemap-conf-badge" style={{ color: confidenceMeta.approximate.color, borderColor: confidenceMeta.approximate.color }}>● 疆域范围为示意</span>
          </div>
          <div className="biblemap-events">
            <div className="biblemap-event">
              <div className="biblemap-event-summary">{era.note}</div>
            </div>
          </div>

          {dataset.kind !== 'regions' && slice?.landmarks?.length > 0 && (
            <div className="biblemap-region-grid">
              {slice.landmarks.map((l) => (
                <span key={l.slug} className="biblemap-region-chip biblemap-region-chip-static">
                  <i style={{ background: '#22d3ee' }} />{l.name_zh}
                </span>
              ))}
            </div>
          )}

          {dataset.kind === 'regions' && slice?.regions && (
            <>
              <div className="biblemap-region-grid">
                {slice.regions.map((r) => (
                  <button key={r.slug}
                    className={`biblemap-region-chip ${regionRel?.slug === r.slug ? 'active' : ''}`}
                    onClick={async () => {
                      const rels = await fetchRelations(r.slug, year)
                      setRegionRel({ slug: r.slug, name: r.name_zh, rels })
                    }}>
                    <i style={{ background: colorBySlug[r.slug] || '#ffd700' }} />{r.name_zh}
                  </button>
                ))}
              </div>
              {regionRel && (
                <div className="biblemap-relations">
                  <div className="biblemap-relations-title">{regionRel.name} · 拓扑关系</div>
                  {regionRel.rels.length ? regionRel.rels.map((rl, i) => (
                    <div key={i} className="biblemap-relation">
                      {REL_LABEL[rl.relation_type] || rl.relation_type} <b>{rl.other_name || rl.other_slug}</b>
                    </div>
                  )) : <div className="biblemap-relation biblemap-relation-empty">（暂无关系记录，或后端未启用）</div>}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    )
  }

  // ── 旅程 / 路线模式 ──────────────────────────────────────────────
  if (!selected) {
    return (
      <div className="biblemap-page">
        {DatasetSelector}
        {/* Keep map container in DOM so mapRef is always available for Leaflet init */}
        <div style={{ visibility: 'hidden', pointerEvents: 'none' }}>{MapBox}</div>
        <div className="biblemap-loading">加载中…</div>
      </div>
    )
  }
  const p = selected.properties
  const cm = confidenceMeta[p.confidence] || confidenceMeta.unknown
  const idx = STN.findIndex((s) => s.properties.id === selected.properties.id)
  const hasYears = variant?.startYear != null && variant?.endYear != null && STN.length > 1
  const stationYears = hasYears ? STN.map((_, i) => Math.round(variant.startYear + (variant.endYear - variant.startYear) * i / (STN.length - 1))) : null
  const jYLabel = (y) => (y < 0 ? `约公元前 ${-y}` : `约公元 ${y}`)
  const curYear = hasYears ? stationYears[idx < 0 ? 0 : idx] : null
  const selectByYear = (y) => { if (!stationYears) return; let i = 0; for (let k = 0; k < stationYears.length; k++) { if (stationYears[k] <= y) i = k }; selectStation(STN[i]) }

  return (
    <div className="biblemap-page">
      {DatasetSelector}
      <div className="biblemap-hypo">
        {dataset.variants.map((h) => (
          <button key={h.id} className={`biblemap-hypo-btn ${h.id === variantId ? 'active' : ''}`}
            style={{ '--hc': h.color }} onClick={() => setVariantId(h.id)} title={h.description}>
            <i style={{ background: h.color }} />{h.label}
          </button>
        ))}
      </div>
      <div className="biblemap-hypo-desc">{variant.description}
        <span className="biblemap-src">{dataset.source === 'api' ? '· 数据源：后端' : '· 数据源：本地'}</span>
      </div>
      {MapBox}
      <div className="biblemap-controls">
        <button onClick={() => step(-1)} aria-label="上一站">‹</button>
        <button className={`biblemap-play ${playing ? 'on' : ''}`} onClick={togglePlay}>{playing ? '⏸ 暂停' : '▶ 播放行程'}</button>
        <button onClick={() => step(1)} aria-label="下一站">›</button>
        <span className="biblemap-counter">第 {idx + 1} 站 / {STN.length}</span>
      </div>
      <div className="biblemap-journey-axis">
        {hasYears && <div className="biblemap-year biblemap-year-sm">{jYLabel(curYear)}</div>}
        <input
          type="range" className="biblemap-slider"
          min={hasYears ? variant.startYear : 0}
          max={hasYears ? variant.endYear : Math.max(0, STN.length - 1)}
          step={1}
          value={hasYears ? curYear : (idx < 0 ? 0 : idx)}
          onChange={(e) => hasYears ? selectByYear(parseInt(e.target.value, 10)) : selectStation(STN[parseInt(e.target.value, 10)])}
          aria-label="行程进度"
        />
        <div className="biblemap-axis-ends">
          <span>{STN[0]?.properties.name_zh}{hasYears ? ` · ${jYLabel(stationYears[0])}` : ''}</span>
          <span>{STN[STN.length - 1]?.properties.name_zh}{hasYears ? ` · ${jYLabel(stationYears[STN.length - 1])}` : ''}</span>
        </div>
      </div>
      <div className="biblemap-detail">
        <div className="biblemap-detail-head">
          <div className="biblemap-detail-no">第 {idx + 1} 站{p.scriptureRef ? ` · ${p.scriptureRef}` : ''}</div>
          <div className="biblemap-detail-title">{p.name_zh}</div>
          <div className="biblemap-detail-sub">{p.name_en}{p.name_he ? ` · ${p.name_he}` : ''}</div>
          <span className="biblemap-conf-badge" style={{ color: cm.color, borderColor: cm.color }}>● {cm.label}</span>
        </div>
        {p.events && p.events.length > 0 ? (
          <div className="biblemap-events">
            {p.events.map((ev, i) => (
              <div key={i} className="biblemap-event">
                <div className="biblemap-event-title">
                  {ev.title}<span className="biblemap-event-ref">{ev.ref}</span>
                  <button className="biblemap-tts" onClick={() => speak(`${ev.title}。${ev.summary}`)} title="朗读" aria-label="朗读">🔊</button>
                </div>
                <div className="biblemap-event-summary">{ev.summary}</div>
                {ev.image && (
                  <img className="biblemap-event-img" src={ev.image} alt={ev.title} loading="lazy"
                    onError={(e) => { e.currentTarget.style.display = 'none' }} />
                )}
                {ev.audio && <audio className="biblemap-event-audio" controls src={ev.audio} />}
              </div>
            ))}
          </div>
        ) : (
          <div className="biblemap-noevent">此站为途经地，圣经未记载具体事件。</div>
        )}
      </div>
      <div className="biblemap-strip">
        {STN.map((f, i) => (
          <button key={f.properties.id} className={`biblemap-chip ${i === idx ? 'active' : ''}`}
            style={{ '--c': (confidenceMeta[f.properties.confidence] || confidenceMeta.unknown).color }}
            onClick={() => selectStation(f)}>
            <span className="biblemap-chip-no">{i + 1}</span>
            <span className="biblemap-chip-name">{f.properties.name_zh}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
