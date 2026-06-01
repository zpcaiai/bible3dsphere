// BibleMap.jsx — 可复用圣经地图引擎（自包含 SVG，离线可用，适配 PWA）
// 统一数据 schema 见 data/bibleMapsData.js。一个引擎驱动全部地图。
// 扩展：地点插图（MapScenes）、AI 讲解（fetchFaithQA）、人物卡片闭环（config.profile）。
import { useEffect, useMemo, useRef, useState } from 'react'
import MapScene, { resolveScene } from './MapScenes'
import { fetchFaithQA } from './api'

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

// —— AI 讲解（复用 /faith-qa，无需登录）——
function AIResult({ data }) {
  return (
    <div className="biblemap-ai-result">
      {data.question_summary && <div className="biblemap-ai-summary">{data.question_summary}</div>}
      {data.nature_analysis && <p>{data.nature_analysis}</p>}
      {data.contextual_analysis && <p>{data.contextual_analysis}</p>}
      {data.right_thinking && <p>{data.right_thinking}</p>}
      {Array.isArray(data.scriptures) && data.scriptures.length > 0 && (
        <div className="biblemap-ai-scriptures">
          {data.scriptures.map((s, i) => (
            <div key={i} className="biblemap-ai-verse">
              <span className="ref">{s.ref || s.reference || ''}</span>
              <span>{s.text || s.content || s.verse || ''}</span>
            </div>
          ))}
        </div>
      )}
      {Array.isArray(data.action_steps) && data.action_steps.length > 0 && (
        <ul className="biblemap-ai-steps">{data.action_steps.map((a, i) => <li key={i}>{a}</li>)}</ul>
      )}
      {data.prayer_direction && <div className="biblemap-ai-prayer">🙏 {data.prayer_direction}</div>}
    </div>
  )
}

function AIExplain({ question, label = '✦ AI 讲解', compact }) {
  const [state, setState] = useState({ loading: false, data: null, error: null })
  useEffect(() => { setState({ loading: false, data: null, error: null }) }, [question])
  if (state.data) return <AIResult data={state.data} />
  return (
    <div className={`biblemap-ai ${compact ? 'compact' : ''}`}>
      <button className="biblemap-ai-btn" disabled={state.loading}
        onClick={async () => {
          setState({ loading: true, data: null, error: null })
          try {
            const data = await fetchFaithQA(question)
            setState({ loading: false, data, error: null })
          } catch (e) {
            setState({ loading: false, data: null, error: e.message || 'AI 暂时不可用' })
          }
        }}>
        {state.loading ? '⏳ AI 思考中…' : label}
      </button>
      {state.error && <div className="biblemap-ai-error">{state.error}</div>}
    </div>
  )
}

export default function BibleMap({ config, onBack }) {
  const project = useMemo(() => makeProjector(config.bounds), [config.bounds])
  const grat = useMemo(() => graticule(config.bounds, project), [config.bounds, project])
  const isTimeline = config.mode === 'timeline'

  const singleSelect = config.layerSelect === 'single'
  const [activeLayerIds, setActiveLayerIds] = useState(
    singleSelect ? [config.layers[0].id] : config.layers.map(l => l.id)
  )
  const activeLayers = config.layers.filter(l => activeLayerIds.includes(l.id))

  const [year, setYear] = useState(config.years ? config.years.default : 0)

  const animLayer = activeLayers[0] || config.layers[0]
  const orderedPoints = useMemo(() => {
    return [...(animLayer?.points || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
  }, [animLayer])
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState(0)
  const rafRef = useRef(null)
  const lastTsRef = useRef(0)

  useEffect(() => { setProgress(0); setPlaying(false) }, [activeLayerIds.join(','), config.id])

  useEffect(() => {
    if (!playing) { cancelAnimationFrame(rafRef.current); return }
    const N = orderedPoints.length
    if (N < 2) { setPlaying(false); return }
    const speed = 0.7
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

  const revealCount = (playing || progress > 0) ? Math.floor(progress) + 1 : Infinity

  const travelDot = useMemo(() => {
    if (!(playing || progress > 0) || orderedPoints.length < 2) return null
    const i = Math.min(Math.floor(progress), orderedPoints.length - 2)
    const f = progress - i
    const a = orderedPoints[i], b = orderedPoints[i + 1]
    const [ax, ay] = project(a.lng, a.lat)
    const [bx, by] = project(b.lng, b.lat)
    return { x: ax + (bx - ax) * f, y: ay + (by - ay) * f }
  }, [playing, progress, orderedPoints, project])

  const [selected, setSelected] = useState(null)

  function visiblePoints(layer) {
    let pts = layer.points
    if (isTimeline && config.years) pts = pts.filter(p => (p.year ?? -99999) <= year)
    if ((playing || progress > 0) && layer.id === animLayer?.id && !isTimeline) {
      const sorted = [...pts].sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      pts = sorted.slice(0, revealCount)
    }
    return pts
  }

  function routePath(layer) {
    const pts = visiblePoints(layer).slice().sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    if (pts.length < 2) return ''
    return pts.map((p, i) => {
      const [x, y] = project(p.lng, p.lat)
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    }).join(' ')
  }

  // 每段中点放一个指向行进方向的箭头（手绘三角，渲染器无关，支持移动端 webview）
  function routeArrows(layer) {
    const pts = visiblePoints(layer).slice().sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
    const arr = []
    for (let i = 0; i < pts.length - 1; i++) {
      const [x1, y1] = project(pts[i].lng, pts[i].lat)
      const [x2, y2] = project(pts[i + 1].lng, pts[i + 1].lat)
      const dx = x2 - x1, dy = y2 - y1
      if (Math.hypot(dx, dy) < 24) continue // 太近的段不放，避免拥挤
      arr.push({ key: `ar-${layer.id}-${i}`, mx: (x1 + x2) / 2, my: (y1 + y2) / 2,
        ang: (Math.atan2(dy, dx) * 180) / Math.PI })
    }
    return arr
  }

  function toggleLayer(id) {
    if (singleSelect) { setActiveLayerIds([id]); setSelected(null); return }
    setActiveLayerIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const yearLabel = (y) => (y < 0 ? `公元前 ${Math.abs(y)}` : `公元 ${y}`)
  const profileLayer = config.profile ? (activeLayers[0] || config.layers[0]) : null

  return (
    <div className="biblemap">
      <div className="biblemap-head">
        <button className="biblemap-back" onClick={onBack}>← 返回</button>
        <div className="biblemap-title">
          <h2>{config.title}</h2>
          <p>{config.subtitle}{config.era ? ` · ${config.era}` : ''}</p>
        </div>
      </div>

      <div className="biblemap-controls">
        {config.layers.length > 1 && config.layers.map(l => {
          const on = activeLayerIds.includes(l.id)
          return (
            <button key={l.id} className={`biblemap-chip ${on ? 'on' : ''}`}
              onClick={() => toggleLayer(l.id)}
              style={on ? { background: l.color + '33', borderColor: l.color, color: l.color } : {}}>
              <span className="dot" style={{ background: l.color }} />{l.label}
            </button>
          )
        })}
        {!isTimeline && animLayer?.route !== false && orderedPoints.length > 1 && (
          <button className="biblemap-chip play"
            onClick={() => { if (progress >= orderedPoints.length - 1) setProgress(0); setPlaying(p => !p) }}>
            {playing ? '⏸ 暂停' : (progress > 0 && progress < orderedPoints.length - 1 ? '▶ 继续' : '▶ 路线动画')}
          </button>
        )}
        {!isTimeline && progress > 0 && (
          <button className="biblemap-chip" onClick={() => { setPlaying(false); setProgress(0) }}>↺ 重置</button>
        )}
      </div>

      {/* 人物卡片（闭环：人物 → 简介 → 书信 → 旅程地图 → AI 讲解）*/}
      {profileLayer && (
        <div className="biblemap-profile" style={{ borderColor: profileLayer.color + '66' }}>
          <div className="biblemap-profile-scene" style={{ background: profileLayer.color + '1a' }}>
            <MapScene scene={profileLayer.scene || 'journey'} color={profileLayer.color} />
          </div>
          <div className="biblemap-profile-body">
            <div className="biblemap-profile-name" style={{ color: profileLayer.color }}>
              {profileLayer.label}{profileLayer.era && <span className="era">{profileLayer.era}</span>}
            </div>
            {profileLayer.bio && <p className="biblemap-profile-bio">{profileLayer.bio}</p>}
            {Array.isArray(profileLayer.epistles) && profileLayer.epistles.length > 0 && (
              <div className="biblemap-profile-epistles">
                ✉ 相关书信：{profileLayer.epistles.map((e, i) => <span key={i} className="ep">{e}</span>)}
              </div>
            )}
            <AIExplain compact
              question={`请用简洁、温暖、适合查经班的话，介绍圣经人物「${profileLayer.label}」的生平、属灵意义与主要经历，并给出一句默想或祷告方向。`}
              label="✦ 请 AI 讲解这位人物" />
          </div>
        </div>
      )}

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
              <stop offset="0%" stopColor="#1a2f4a" /><stop offset="100%" stopColor="#0e1b2e" />
            </radialGradient>
            <linearGradient id="bm-land" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3a3526" /><stop offset="100%" stopColor="#2a2718" />
            </linearGradient>
            <filter id="bm-glow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          <rect x="0" y="0" width={VB_W} height={VB_H} fill="url(#bm-sea)" />
          <rect x={PAD - 14} y={PAD - 14} width={VB_W - 2 * (PAD - 14)} height={VB_H - 2 * (PAD - 14)}
            fill="url(#bm-land)" rx="10" opacity="0.55" />

          {grat.map((g, i) => (
            <g key={i}>
              <line x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} stroke="#ffffff" strokeOpacity="0.06" strokeWidth="1" />
              <text x={g.lx} y={g.ly} fill="#ffffff" fillOpacity="0.18" fontSize="11">{g.label}</text>
            </g>
          ))}

          <g transform={`translate(${VB_W - 46},${46})`} opacity="0.5">
            <circle r="18" fill="none" stroke="#ffffff" strokeOpacity="0.25" />
            <path d="M0,-15 L4,2 L0,-2 L-4,2 Z" fill="#e8b04b" />
            <text x="0" y="-22" textAnchor="middle" fill="#ffffff" fillOpacity="0.5" fontSize="11">N</text>
          </g>

          {activeLayers.map(layer => (
            <path key={'r-' + layer.id} d={routePath(layer)} fill="none"
              stroke={layer.color} strokeWidth="2.5" strokeOpacity="0.85"
              strokeDasharray={layer.route === false ? '2 8' : '7 6'} strokeLinecap="round" strokeLinejoin="round" />
          ))}

          {activeLayers.map(layer => layer.route === false ? null : (
            routeArrows(layer).map(a => (
              <path key={a.key} d="M-5,-4.5 L7,0 L-5,4.5 L-1.5,0 Z" fill={layer.color}
                stroke="#0e1b2e" strokeWidth="0.8"
                transform={`translate(${a.mx.toFixed(1)},${a.my.toFixed(1)}) rotate(${a.ang.toFixed(1)})`} />
            ))
          ))}

          {travelDot && (
            <g filter="url(#bm-glow)">
              <circle cx={travelDot.x} cy={travelDot.y} r="7" fill="#fff" />
              <circle cx={travelDot.x} cy={travelDot.y} r="13" fill="none" stroke="#fff" strokeOpacity="0.5">
                <animate attributeName="r" values="7;15;7" dur="1.4s" repeatCount="indefinite" />
                <animate attributeName="stroke-opacity" values="0.6;0;0.6" dur="1.4s" repeatCount="indefinite" />
              </circle>
            </g>
          )}

          {activeLayers.flatMap(layer => visiblePoints(layer).map(p => {
            const [x, y] = project(p.lng, p.lat)
            const isSel = selected && selected.id === p.id
            return (
              <g key={layer.id + '-' + p.id} transform={`translate(${x},${y})`}
                style={{ cursor: 'pointer' }} onClick={() => setSelected({ ...p, _color: layer.color })}>
                <circle r={isSel ? 9 : 6} fill={layer.color} stroke="#0e1b2e" strokeWidth="2"
                  filter={isSel ? 'url(#bm-glow)' : undefined} />
                {p.altar && <text x="0" y="-12" textAnchor="middle" fontSize="13">⛪</text>}
                <text x="10" y="4" fontSize="13" fill="#fff" stroke="#0e1b2e" strokeWidth="3"
                  paintOrder="stroke" style={{ pointerEvents: 'none' }}>{p.name_zh}</text>
              </g>
            )
          }))}
        </svg>

        {selected && (
          <div className="biblemap-detail">
            <button className="biblemap-detail-close" onClick={() => setSelected(null)}>×</button>
            <div className="biblemap-scene" style={{ background: selected._color + '1a' }}>
              <MapScene scene={resolveScene(selected, config.id)} color={selected._color} />
            </div>
            <div className="biblemap-detail-name" style={{ color: selected._color }}>
              {selected.name_zh}<span className="en">{selected.name_en}</span>
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
            {selected.altar && <div className="biblemap-altar">⛪ 在此筑坛：{selected.altar}</div>}
            {selected.promise && <div className="biblemap-promise">✝ 神的应许：{selected.promise}</div>}
            {selected.note && <p className="biblemap-note">{selected.note}</p>}
            <div className="biblemap-events">
              {(selected.events || []).map((ev, i) => (
                <div key={i} className="biblemap-event">
                  <div className="biblemap-event-h">
                    <strong>{ev.title}</strong>{ev.ref && <span className="ref">{ev.ref}</span>}
                  </div>
                  <p>{ev.summary}</p>
                </div>
              ))}
              {(!selected.events || selected.events.length === 0) && (
                <p className="biblemap-note dim">途经此地。</p>
              )}
            </div>
            <AIExplain
              question={`请用简洁、温暖、适合主日学的话，讲解圣经地点「${selected.name_zh}（${selected.name_en}）」的历史背景与属灵意义${selected.scriptureRef ? `（相关经文：${selected.scriptureRef}）` : ''}，并给出一句默想或祷告方向。`}
              label="✦ AI 讲解这个地点" />
          </div>
        )}
      </div>

      <div className="biblemap-legend">
        {Object.entries(CONFIDENCE).map(([k, v]) => (
          <span key={k}><i style={{ background: v.color }} />{v.label}</span>
        ))}
        <span className="hint">点击地标看经文与插图 · ✦ 可让 AI 现场讲解 · ⛪ 表示筑坛/圣所</span>
      </div>
    </div>
  )
}
