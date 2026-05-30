// BibleMap.jsx — 可复用圣经地图引擎（自包含 SVG，离线可用，适配 PWA）
// 统一数据 schema 见 data/*.js。一个引擎驱动全部地图。
import { useEffect, useMemo, useRef, useState } from 'react'

const VB_W = 1000
const VB_H = 720
const PAD = 56

const CONFIDENCE = {
  identified:  { label: '考古较确定', color: '#4ade80' },
  approximate: { label: '传统推定',   color: '#fbbf24' },
  unknown:     { label: '地点失考',   color: '#94a3b8' },
}

// 经纬度 → SVG 坐标（保持长宽比，按中纬度余弦校正经度）
function makeProjector(bounds) {
  const { minLng, maxLng, minLat, maxLat } = bounds
  const midLat = (minLat + maxLat) / 2
  const lngScale = Math.cos((midLat * Math.PI) / 180)
  const geoW = (maxLng - minLng) * lngScale
  const geoH = (maxLat - minLat)
  const innerW = VB_W - 2 * PAD
  const innerH = VB_H - 2 * PAD
  const s = Math.min(innerW / geoW, innerH / geoH)
  const drawW = geoW * s
  const drawH = geoH * s
  const offX = PAD + (innerW - drawW) / 2
  const offY = PAD + (innerH - drawH) / 2
  return (lng, lat) => [
    offX + (lng - minLng) * lngScale * s,
    offY + (maxLat - lat) * s,
  ]
}

// 经纬网格线
function graticule(bounds, project) {
  const lines = []
  const lngStep = (bounds.maxLng - bounds.minLng) > 12 ? 5 : (bounds.maxLng - bounds.minLng) > 5 ? 2 : 1
  const latStep = (bounds.maxLat - bounds.minLat) > 12 ? 5 : (bounds.maxLat - bounds.minLat) > 5 ? 2 : 1
  for (let lng = Math.ceil(bounds.minLng / lngStep) * lngStep; lng <= bounds.maxLng; lng += lngStep) {
    const [x1, y1] = project(lng, bounds.minLat)
    const [x2, y2] = project(lng, bounds.maxLat)
    lines.push({ x1, y1, x2, y2, label: `${lng}°E`, lx: x1, ly: y2 - 6 })
  }
  for (let lat = Math.ceil(bounds.minLat / latStep) * latStep; lat <= bounds.maxLat; lat += latStep) {
    const [x1, y1] = project(bounds.minLng, lat)
    const [x2, y2] = project(bounds.maxLng, lat)
    lines.push({ x1, y1, x2, y2, label: `${lat}°N`, lx: x1 + 4, ly: y1 - 4, horiz: true })
  }
  return lines
}

export default function BibleMap({ config, onBack }) {
  const project = useMemo(() => makeProjector(config.bounds), [config.bounds])
  const grat = useMemo(() => graticule(config.bounds, project), [config.bounds, project])
  const isTimeline = config.mode === 'timeline'

  // —— 图层选择 ——
  const singleSelect = config.layerSelect === 'single'
  const [activeLayerIds, setActiveLayerIds] = useState(
    singleSelect ? [config.layers[0].id] : config.layers.map(l => l.id)
  )
  const activeLayers = config.layers.filter(l => activeLayerIds.includes(l.id))

  // —— 时间轴（timeline 模式）——
  const [year, setYear] = useState(config.years ? config.years.default : 0)

  // —— 路线动画（journey 模式）——
  const animLayer = activeLayers[0] || config.layers[0]
  const orderedPoints = useMemo(() => {
    return [...(animLayer?.points || [])].sort(
      (a, b) => (a.order ?? 0) - (b.order ?? 0)
    )
  }, [animLayer])
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0) // 0 .. N-1
  const rafRef = useRef(null)
  const lastTsRef = useRef(0)

  useEffect(() => { setProgress(0); setPlaying(false) }, [activeLayerIds.join(','), config.id])

  useEffect(() => {
    if (!playing) { cancelAnimationFrame(rafRef.current); return }
    const N = orderedPoints.length
    if (N < 2) { setPlaying(false); return }
    const speed = 0.7 // 站/秒
    const tick = (ts) => {
      if (!lastTsRef.current) lastTsRef.current = ts
      const dt = (ts - lastTsRef.current) / 1000
      lastTsRef.current = ts
      setProgress(p => {
        const np = p + dt * speed
        if (np >= N - 1) { setPlaying(false); return N - 1 }
        return np
      })
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(rafRef.current); lastTsRef.current = 0 }
  }, [playing, orderedPoints.length])

  const revealCount = playing || progress > 0
    ? Math.floor(progress) + 1
    : (isTimeline ? Infinity : Infinity)

  // 动画行进点坐标
  const travelDot = useMemo(() => {
    if (!(playing || progress > 0) || orderedPoints.length < 2) return null
    const i = Math.min(Math.floor(progress), orderedPoints.length - 2)
    const f = progress - i
    const a = orderedPoints[i], b = orderedPoints[i + 1]
    const [ax, ay] = project(a.lng, a.lat)
    const [bx, by] = project(b.lng, b.lat)
    return { x: ax + (bx - ax) * f, y: ay + (by - ay) * f, name: orderedPoints[Math.round(progress)]?.name_zh }
  }, [playing, progress, orderedPoints, project])

  // —— 选中地标 ——
  const [selected, setSelected] = useState(null)

  // 当前可见点（按图层 + 时间轴 + 动画揭示过滤）
  function visiblePoints(layer) {
    let pts = layer.points
    if (isTimeline && config.years) {
      pts = pts.filter(p => (p.year ?? -99999) <= year)
    }
    if ((playing || progress > 0) && layer.id === animLayer?.id && !isTimeline) {
      const sorted = [...pts].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      pts = sorted.slice(0, revealCount)
    }
    return pts
  }

  function routePath(layer) {
    const pts = visiblePoints(layer)
      .slice()
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    if (pts.length < 2) return ''
    return pts.map((p, i) => {
      const [x, y] = project(p.lng, p.lat)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  }

  function toggleLayer(id) {
    if (singleSelect) { setActiveLayerIds([id]); setSelected(null); return }
    setActiveLayerIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const yearLabel = (y) => (y < 0 ? `公元前 ${Math.abs(y)}` : `公元 ${y}`)

  return (
    <div className="biblemap">
      <div className="biblemap-head">
        <button className="biblemap-back" onClick={onBack}>← 返回</button>
        <div className="biblemap-title">
          <h2>{config.title}</h2>
          <p>{config.subtitle}{config.era ? ` · ${config.era}` : ''}</p>
        </div>
      </div>

      {/* 控制栏 */}
      <div className="biblemap-controls">
        {config.layers.length > 1 && config.layers.map(l => {
          const on = activeLayerIds.includes(l.id)
          return (
            <button key={l.id}
              className={`biblemap-chip ${on ? 'on' : ''}`}
              onClick={() => toggleLayer(l.id)}
              style={on ? { background: l.color + '33', borderColor: l.color, color: l.color } : {}}
            >
              <span className="dot" style={{ background: l.color }} />{l.label}
            </button>
          )
        })}
        {!isTimeline && orderedPoints.length > 1 && (
          <button className="biblemap-chip play"
            onClick={() => { if (progress >= orderedPoints.length - 1) setProgress(0); setPlaying(p => !p) }}>
            {playing ? '⏸ 暂停' : (progress > 0 && progress < orderedPoints.length - 1 ? '▶ 继续' : '▶ 路线动画')}
          </button>
        )}
        {!isTimeline && progress > 0 && (
          <button className="biblemap-chip" onClick={() => { setPlaying(false); setProgress(0) }}>↺ 重置</button>
        )}
      </div>

      {/* 时间轴滑块 */}
      {isTimeline && config.years && (
        <div className="biblemap-timeline">
          <span className="ty">{yearLabel(year)}</span>
          <input type="range" min={config.years.min} max={config.years.max} step={config.years.step || 1}
            value={year} onChange={e => setYear(Number(e.target.value))} />
          <div className="biblemap-eras">
            {(config.eras || []).map(er => (
              <button key={er.label} className={`era ${year >= er.from && year <= er.to ? 'on' : ''}`}
                onClick={() => setYear(Math.round((er.from + er.to) / 2))}>{er.label}</button>
            ))}
          </div>
        </div>
      )}

      <div className="biblemap-stage">
        <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="biblemap-svg" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id="bm-sea" cx="50%" cy="40%" r="80%">
              <stop offset="0%" stopColor="#1a2f4a" />
              <stop offset="100%" stopColor="#0e1b2e" />
            </radialGradient>
            <linearGradient id="bm-land" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3a3526" />
              <stop offset="100%" stopColor="#2a2718" />
            </linearGradient>
            <filter id="bm-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          <rect x="0" y="0" width={VB_W} height={VB_H} fill="url(#bm-sea)" />
          <rect x={PAD - 14} y={PAD - 14} width={VB_W - 2 * (PAD - 14)} height={VB_H - 2 * (PAD - 14)}
            fill="url(#bm-land)" rx="10" opacity="0.55" />

          {/* 经纬网 */}
          {grat.map((g, i) => (
            <g key={i}>
              <line x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} stroke="#ffffff" strokeOpacity="0.06" strokeWidth="1" />
              <text x={g.lx} y={g.ly} fill="#ffffff" fillOpacity="0.18" fontSize="11">{g.label}</text>
            </g>
          ))}

          {/* 指南针 */}
          <g transform={`translate(${VB_W - 46},${46})`} opacity="0.5">
            <circle r="18" fill="none" stroke="#ffffff" strokeOpacity="0.25" />
            <path d="M0,-15 L4,2 L0,-2 L-4,2 Z" fill="#e8b04b" />
            <text x="0" y="-22" textAnchor="middle" fill="#ffffff" fillOpacity="0.5" fontSize="11">N</text>
          </g>

          {/* 路线 */}
          {activeLayers.map(layer => (
            <path key={'r-' + layer.id} d={routePath(layer)} fill="none"
              stroke={layer.color} strokeWidth="2.5" strokeOpacity="0.85"
              strokeDasharray={layer.route === false ? '2 8' : '7 6'} strokeLinecap="round" strokeLinejoin="round" />
          ))}

          {/* 行进点 */}
          {travelDot && (
            <g filter="url(#bm-glow)">
              <circle cx={travelDot.x} cy={travelDot.y} r="7" fill="#fff" />
              <circle cx={travelDot.x} cy={travelDot.y} r="13" fill="none" stroke="#fff" strokeOpacity="0.5">
                <animate attributeName="r" values="7;15;7" dur="1.4s" repeatCount="indefinite" />
                <animate attributeName="stroke-opacity" values="0.6;0;0.6" dur="1.4s" repeatCount="indefinite" />
              </circle>
            </g>
          )}

          {/* 地标点 */}
          {activeLayers.flatMap(layer => visiblePoints(layer).map(p => {
            const [x, y] = project(p.lng, p.lat)
            const conf = CONFIDENCE[p.confidence] || CONFIDENCE.approximate
            const isSel = selected && selected.id === p.id
            return (
              <g key={layer.id + '-' + p.id} transform={`translate(${x},${y})`}
                style={{ cursor: 'pointer' }}
                onClick={() => setSelected({ ...p, _color: layer.color })}>
                <circle r={isSel ? 9 : 6} fill={layer.color} stroke="#0e1b2e" strokeWidth="2"
                  filter={isSel ? 'url(#bm-glow)' : undefined} />
                {p.altar && <text x="0" y="-12" textAnchor="middle" fontSize="13">⛪</text>}
                <text x="10" y="4" fontSize="13" fill="#fff" stroke="#0e1b2e" strokeWidth="3"
                  paintOrder="stroke" style={{ pointerEvents: 'none' }}>{p.name_zh}</text>
              </g>
            )
          }))}
        </svg>

        {/* 详情面板 */}
        {selected && (
          <div className="biblemap-detail">
            <button className="biblemap-detail-close" onClick={() => setSelected(null)}>×</button>
            <div className="biblemap-detail-name" style={{ color: selected._color }}>
              {selected.name_zh}
              <span className="en">{selected.name_en}</span>
            </div>
            <div className="biblemap-detail-meta">
              {selected.year != null && <span>🗓 {yearLabel(selected.year)}</span>}
              {selected.age != null && <span>👤 亚伯拉罕 {selected.age} 岁</span>}
              {selected.scriptureRef && <span>📖 {selected.scriptureRef}</span>}
              {selected.confidence && (
                <span style={{ color: (CONFIDENCE[selected.confidence] || {}).color }}>
                  ◎ {(CONFIDENCE[selected.confidence] || {}).label}
                </span>
              )}
            </div>
            {selected.altar && (
              <div className="biblemap-altar">⛪ 在此筑坛：{selected.altar}</div>
            )}
            {selected.promise && (
              <div className="biblemap-promise">✝ 神的应许：{selected.promise}</div>
            )}
            {selected.note && <p className="biblemap-note">{selected.note}</p>}
            <div className="biblemap-events">
              {(selected.events || []).map((ev, i) => (
                <div key={i} className="biblemap-event">
                  <div className="biblemap-event-h">
                    <strong>{ev.title}</strong>
                    {ev.ref && <span className="ref">{ev.ref}</span>}
                  </div>
                  <p>{ev.summary}</p>
                </div>
              ))}
              {(!selected.events || selected.events.length === 0) && (
                <p className="biblemap-note dim">途经此地（民数记安营站点）。</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 图例 */}
      <div className="biblemap-legend">
        {Object.entries(CONFIDENCE).map(([k, v]) => (
          <span key={k}><i style={{ background: v.color }} />{v.label}</span>
        ))}
        <span className="hint">点击地标查看经文与事件 · ⛪ 表示筑坛/圣所</span>
      </div>
    </div>
  )
}
