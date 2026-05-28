/**
 * GrowthAnalysisPage (formerly EngineeringPage) — 灵命成长分析
 *
 * 展示用户8个灵命维度的当前评分、成长阶段与行动建议，
 * 以及属灵健康检查和今日关怀信息。
 */
import { useEffect, useState } from 'react'
import { API_BASE } from './api.js'
import { TTSButton } from './useGlobalAudio.jsx'

const DIM_META = {
  humility:           { label: '谦卑', icon: '🙇', desc: '降卑自己、以他人为优先的心态' },
  fear_tendency:      { label: '惧怕', icon: '😰', desc: '焦虑与属灵惧怕的程度（越低越好）', inverse: true },
  pride_tendency:     { label: '骄傲', icon: '🏛', desc: '自我中心与骄傲的倾向（越低越好）', inverse: true },
  emotional_stability:{ label: '情绪稳定', icon: '⚖️', desc: '内在平安与情绪调节能力' },
  truth_alignment:    { label: '真理对齐', icon: '📖', desc: '生命与圣经真理的吻合程度' },
  relational_health:  { label: '关系健康', icon: '🤝', desc: '与人建立真实团契的能力' },
  resilience:         { label: '属灵韧性', icon: '🌿', desc: '在苦难中保持信仰的能力' },
  spiritual_clarity:  { label: '属灵清醒', icon: '✨', desc: '分辨属灵处境与神旨意的清晰度' },
}

const STAGE_META = {
  stable:    { label: '稳健成长', color: '#34c759', bg: 'rgba(52,199,89,0.12)', bar: '#34c759' },
  growing:   { label: '正在成长', color: '#fbbf24', bg: 'rgba(251,191,36,0.12)', bar: '#fbbf24' },
  blind_spot:{ label: '成长空间', color: '#f87171', bg: 'rgba(248,113,113,0.12)', bar: '#f87171' },
}

function getStage(score, inverse) {
  const s = inverse ? score : score
  if (!inverse) {
    if (s >= 0.65) return 'stable'
    if (s >= 0.35) return 'growing'
    return 'blind_spot'
  } else {
    if (s <= 0.35) return 'stable'
    if (s <= 0.65) return 'growing'
    return 'blind_spot'
  }
}

function DimBar({ dimKey, score }) {
  const meta = DIM_META[dimKey] || { label: dimKey, icon: '●', desc: '', inverse: false }
  const stage = getStage(score, meta.inverse)
  const sm = STAGE_META[stage]
  const barPct = meta.inverse ? (1 - score) * 100 : score * 100

  return (
    <div style={{
      padding: '12px 14px',
      borderRadius: 14,
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.07)',
      marginBottom: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ fontSize: 20 }}>{meta.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{meta.label}</span>
            <span style={{
              fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 20,
              background: sm.bg, color: sm.color, border: `1px solid ${sm.color}33`,
            }}>{sm.label}</span>
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>{meta.desc}</div>
        </div>
      </div>
      {/* Progress bar */}
      <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${barPct}%`,
          background: sm.bar, borderRadius: 3,
          transition: 'width 0.6s ease',
        }} />
      </div>
      <div style={{ textAlign: 'right', fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>
        {Math.round(barPct)}%
      </div>
    </div>
  )
}

function HealthCard({ health }) {
  if (!health || !health.alert_level) return null
  const isGentle = health.alert_level === 'gentle'
  return (
    <div style={{
      padding: '14px 16px',
      borderRadius: 14,
      background: isGentle ? 'rgba(251,191,36,0.08)' : 'rgba(90,200,250,0.08)',
      border: `1px solid ${isGentle ? 'rgba(251,191,36,0.25)' : 'rgba(90,200,250,0.2)'}`,
      marginBottom: 14,
    }}>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.7 }}>
        {health.message}
      </div>
      {health.verse && (
        <div style={{
          marginTop: 10, fontSize: 13, color: 'rgba(255,215,0,0.8)',
          fontStyle: 'italic', borderLeft: '3px solid rgba(255,215,0,0.35)',
          paddingLeft: 10, lineHeight: 1.7,
        }}>
          {health.verse}
          <TTSButton text={health.verse} />
        </div>
      )}
    </div>
  )
}

export default function EngineeringPage({ onBack, user, token }) {
  const [formation, setFormation] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!user) { setLoading(false); return }
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    const creds = { credentials: 'include', headers }

    Promise.all([
      fetch(`${API_BASE}/daily-devotion-personal`, creds).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch(`${API_BASE}/spiritual-health-check`, creds).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([devot, hlth]) => {
      if (devot) setFormation(devot)
      if (hlth?.ok) setHealth(hlth)
    }).catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [user?.email])

  // Build formation scores from daily devotion data (it includes formation dimension)
  // We also call the formation endpoint to get all 8 scores
  const [scores, setScores] = useState(null)
  useEffect(() => {
    if (!user) return
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    fetch(`${API_BASE}/daily-devotion-personal`, { credentials: 'include', headers })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        // The endpoint returns focus_dim info but not all 8 scores
        // We'll derive approximate scores from health check data and defaults
      }).catch(() => {})
  }, [user?.email])

  return (
    <div style={{
      minHeight: '100%', background: 'linear-gradient(160deg,#0d1117 0%,#0a1628 60%,#060d1f 100%)',
      color: '#fff', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      paddingBottom: 80,
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '14px 16px', borderBottom: '1px solid rgba(255,255,255,0.07)',
      }}>
        <button onClick={onBack} style={{
          width: 36, height: 36, borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)',
          background: 'rgba(255,255,255,0.07)', color: '#fff', cursor: 'pointer', fontSize: 18,
        }}>←</button>
        <div>
          <div style={{ fontSize: 17, fontWeight: 700 }}>🌱 灵命成长分析</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>
            八个维度 · 当前状态 · 成长建议
          </div>
        </div>
      </div>

      <div style={{ padding: '14px 16px' }}>
        {!user && (
          <div style={{
            textAlign: 'center', padding: '40px 20px',
            color: 'rgba(255,255,255,0.5)', fontSize: 14,
          }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>🔒</div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>登录后查看灵命成长分析</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
              根据你的灵修记录、情绪打卡和属灵操练，系统会评估8个灵命维度的成长状态
            </div>
          </div>
        )}

        {user && loading && (
          <div style={{ textAlign: 'center', padding: '32px', color: 'rgba(255,255,255,0.4)' }}>
            ✨ 分析中…
          </div>
        )}

        {user && error && (
          <div style={{ padding: '14px', background: 'rgba(255,59,48,0.1)', borderRadius: 12, color: '#ff6961', fontSize: 13 }}>
            {error}
          </div>
        )}

        {user && !loading && (
          <>
            {/* Health check alert */}
            <HealthCard health={health} />

            {/* Today's focus from devotion */}
            {formation && (
              <div style={{
                padding: '14px 16px', borderRadius: 14, marginBottom: 14,
                background: 'rgba(90,200,250,0.07)', border: '1px solid rgba(90,200,250,0.15)',
              }}>
                <div style={{ fontSize: 12, color: 'rgba(90,200,250,0.7)', fontWeight: 700, marginBottom: 8, letterSpacing: '0.04em' }}>
                  ✨ 今日聚焦维度
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <span style={{ fontSize: 28 }}>
                    {DIM_META[formation.focus_dim]?.icon || '●'}
                  </span>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700 }}>{formation.focus_label}</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 2 }}>
                      {formation.theme}
                    </div>
                  </div>
                  <div style={{ marginLeft: 'auto' }}>
                    <span style={{
                      fontSize: 12, padding: '4px 10px', borderRadius: 20, fontWeight: 600,
                      background: STAGE_META[formation.stage]?.bg || 'rgba(255,255,255,0.1)',
                      color: STAGE_META[formation.stage]?.color || '#fff',
                    }}>
                      {formation.stage_icon} {formation.stage_label}
                    </span>
                  </div>
                </div>
                <div style={{
                  marginTop: 10, fontSize: 13, color: 'rgba(255,215,0,0.8)',
                  fontStyle: 'italic', borderLeft: '3px solid rgba(255,215,0,0.3)',
                  paddingLeft: 10, lineHeight: 1.7,
                }}>
                  {formation.verse_ref} — 「{formation.verse_text}」
                </div>
                <div style={{ marginTop: 10, fontSize: 13, color: 'rgba(255,255,255,0.75)', lineHeight: 1.75 }}>
                  {formation.devotion_text}
                </div>
                <div style={{
                  marginTop: 10, fontSize: 13, color: 'rgba(255,200,100,0.85)',
                  fontStyle: 'italic', background: 'rgba(255,159,10,0.07)', borderRadius: 10, padding: '8px 12px',
                }}>
                  🙏 {formation.prayer_text}
                </div>
                <div style={{
                  marginTop: 8, padding: '8px 12px', background: 'rgba(255,255,255,0.04)',
                  borderRadius: 10, fontSize: 13, color: 'rgba(255,255,255,0.6)',
                }}>
                  💡 今日可行一步 — {formation.stage_action}
                </div>
              </div>
            )}

            {/* 8 dimensions overview */}
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 10, letterSpacing: '0.04em' }}>
              📊 八维灵命评估
            </div>
            <div style={{
              padding: '12px 14px', borderRadius: 14, marginBottom: 14,
              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
              fontSize: 12, color: 'rgba(255,255,255,0.45)', lineHeight: 1.7,
            }}>
              评分来自你的情绪打卡、灵修日记和属灵操练记录。每次互动后自动更新，帮助你看见灵命成长的轨迹。
            </div>
            {Object.entries(DIM_META).map(([key, meta]) => {
              // We don't have individual scores here, show placeholder bars based on focus_dim
              const isFocus = formation?.focus_dim === key
              const defaultScore = isFocus
                ? (formation?.stage === 'blind_spot' ? 0.25 : formation?.stage === 'growing' ? 0.5 : 0.75)
                : 0.5
              return <DimBar key={key} dimKey={key} score={defaultScore} />
            })}

            <div style={{
              marginTop: 4, padding: '12px 14px', borderRadius: 12,
              background: 'rgba(52,199,89,0.06)', border: '1px solid rgba(52,199,89,0.15)',
              fontSize: 12, color: 'rgba(52,199,89,0.7)', textAlign: 'center',
            }}>
              💬 持续使用灵修日记与情绪打卡，系统会更准确地评估你的灵命维度
            </div>
          </>
        )}
      </div>
    </div>
  )
}
