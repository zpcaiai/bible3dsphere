// BibleMapsPage.jsx — 圣经地图中心：12 张地图入口 + 渲染选中地图
import { useState } from 'react'
import BibleMap from './BibleMap'
import { BIBLE_MAPS } from '../data/bibleMapsData'

const ICONS = {
  abraham: '🏕', exodus: '🔥', joshua: '⚔️', tribes: '🧩', david: '👑', solomon: '🏛',
  divided: '⚖️', jesus: '✝️', paul: '⛵', 'seven-churches': '🕯', timeline: '🌍', characters: '👤',
}

const STAGES = [
  { label: '第一阶段 · 需求最大', ids: ['jesus', 'paul', 'exodus'] },
  { label: '第二阶段 · 互动产品', ids: ['characters', 'tribes', 'seven-churches'] },
  { label: '第三阶段 · 核心壁垒', ids: ['timeline', 'abraham', 'joshua', 'david', 'solomon', 'divided'] },
]

export default function BibleMapsPage({ onBack }) {
  const [activeId, setActiveId] = useState(null)
  const active = BIBLE_MAPS.find(m => m.id === activeId)

  if (active) {
    return <BibleMap config={active} onBack={() => setActiveId(null)} />
  }

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
      <div className="biblemap-head">
        <button className="biblemap-back" onClick={onBack}>← 返回</button>
        <div className="biblemap-title">
          <h2>🗺 圣经地图</h2>
          <p>从亚伯拉罕到启示录 · 点击地标看经文，播放路线动画，拖动时间轴看历史展开</p>
        </div>
      </div>
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
        共 {BIBLE_MAPS.length} 张地图 · 全部离线可用 · 数据采用传统圣经年代学，仅供主日学／查经教学示意
      </p>
    </div>
  )
}
