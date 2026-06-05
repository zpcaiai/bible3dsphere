// BibleMapsPage.jsx — 圣经地图中心：12 张交互地图 + 耶路撒冷数字孪生沙盘
import { lazy, Suspense, useState } from 'react'
import BibleMap from './BibleMap'
import { BIBLE_MAPS } from './data/bibleMapsData'

const JerusalemSandbox = lazy(() => import('./JerusalemSandbox'))

const ICONS = {
  abraham: '🏕', exodus: '🔥', joshua: '⚔️', tribes: '🧩', david: '👑', solomon: '🏛',
  divided: '⚖️', jesus: '✝️', paul: '⛵', 'seven-churches': '🕯', timeline: '🌍', characters: '👤',
}

const STAGES = [
  { label: '第一阶段 · 需求最大', ids: ['jesus', 'paul', 'exodus'] },
  { label: '第二阶段 · 互动产品', ids: ['characters', 'tribes', 'seven-churches'] },
  { label: '第三阶段 · 核心壁垒', ids: ['timeline', 'abraham', 'joshua', 'david', 'solomon', 'divided'] },
]

export default function BibleMapsPage({ onBack, embedded, onOpenAtlas }) {
  const [activeId, setActiveId] = useState(null)

  if (activeId === 'jerusalem') {
    return (
      <Suspense fallback={<div className="jeru-loading" style={{ padding: 40 }}>🌍 加载三维沙盘…</div>}>
        <JerusalemSandbox onBack={() => setActiveId(null)} />
      </Suspense>
    )
  }
  const active = BIBLE_MAPS.find(m => m.id === activeId)
  if (active) return <BibleMap key={active.id} config={active} onBack={() => setActiveId(null)} />

  const card = (m) => (
    <button key={m.id} className="biblemap-card" onClick={() => setActiveId(m.id)}>
      <div className="biblemap-card-icon">{ICONS[m.id] || '🗺'}</div>
      <div className="biblemap-card-body">
        <div className="biblemap-card-title">{m.title}<span className="badge">{m.badge}</span></div>
        <div className="biblemap-card-sub">{m.subtitle}</div>
        <div className="biblemap-card-era">{m.era}</div>
      </div>
      <span className="biblemap-card-arrow">›</span>
    </button>
  )

  return (
    <div className="biblemap-hub">
{!embedded && (
        <div className="biblemap-head">
          <button className="biblemap-back" onClick={onBack}>← 返回</button>
          <div className="biblemap-title">
            <h2>🗺 圣经地图</h2>
            <p>从亚伯拉罕到启示录 · 点击地标看经文，播放路线动画，拖动时间轴看历史展开</p>
          </div>
        </div>
      )}

      {/* 特别篇：耶路撒冷数字孪生沙盘 */}
      <section className="biblemap-stage-group">
        <h3 className="biblemap-stage-label">特别篇 · 数字孪生时空沙盘（3D）</h3>
        {onOpenAtlas && (
          <button className="biblemap-card jeru-feature" style={{ marginBottom: 10 }} onClick={onOpenAtlas}>
            <div className="biblemap-card-icon">🌍</div>
            <div className="biblemap-card-body">
              <div className="biblemap-card-title">圣经地图集<span className="badge">★★★★★★</span></div>
              <div className="biblemap-card-sub">Mapbox 时间轴地图集：支派分布 / 预言应验 / 战役 / 帝国疆域图层</div>
            </div>
            <span className="biblemap-card-arrow">›</span>
          </button>
        )}
        <button className="biblemap-card jeru-feature" onClick={() => setActiveId('jerusalem')}>
          <div className="biblemap-card-icon">🏛</div>
          <div className="biblemap-card-body">
            <div className="biblemap-card-title">耶路撒冷圣城变迁与圣殿结构<span className="badge">★★★★★★</span></div>
            <div className="biblemap-card-sub">固定视角圣殿山，拖时间轴看大卫城→所罗门→希西家→尼希米→希律→现代的"平地起高楼"；受难周 FPV 步行轨迹；🏛 圣殿3D精细结构(可剖视/逐部件经文)</div>
            <div className="biblemap-card-era">Mapbox GL v3 / MapLibre v1 · 3D WebGL · 需联网</div>
          </div>
          <span className="biblemap-card-arrow">›</span>
        </button>
      </section>

      {STAGES.map(stage => (
        <section key={stage.label} className="biblemap-stage-group">
          <h3 className="biblemap-stage-label">{stage.label}</h3>
          <div className="biblemap-card-grid">
            {stage.ids.map(id => {
              const m = BIBLE_MAPS.find(x => x.id === id)
              return m ? card(m) : null
            })}
          </div>
        </section>
      ))}
      <p className="biblemap-foot">
        共 {BIBLE_MAPS.length} 张交互地图 + 1 个 3D 沙盘 · SVG 地图离线可用 · 数据采用传统圣经年代学，仅供主日学／查经教学示意
      </p>
    </div>
  )
}
