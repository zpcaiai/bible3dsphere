import { useEffect, useRef, useState } from 'react'
import {
  fetchDiscipleMeta, fetchDiscipleProfile, assessDisciple, fetchDiscipleHistory,
  askDiscipleMentor, fetchDiscipleNetwork, addDiscipleRelationship, endDiscipleRelationship,
  fetchDiscipleReview, fetchDiscipleGraph, fetchDiscipleMilestones,
} from './api'

// 门徒塑造引擎 · Disciple Formation Engine (DFOS v1.0)
// 闭环：每日反思 → 识别信念/偶像/顺服/呼召 → Faith-Hope-Love 评分 → 更新数字孪生
//       → 今日顺服行动 → 历史聚合 → 状态迁移 → 门徒培养 / 倍增网络

const ACCENT = '#a78bfa'
const ACCENT_DIM = 'rgba(167,139,250,0.16)'

const RISK_COLOR = {
  LOW: '#34c759', MEDIUM: '#ffd60a', HIGH: '#ff9f0a', CRITICAL: '#ff453a',
}
const RISK_ZH = { LOW: '低', MEDIUM: '中', HIGH: '高', CRITICAL: '危急' }

function ciColor(v) {
  if (v >= 75) return '#34c759'
  if (v >= 55) return '#a78bfa'
  if (v >= 35) return '#ffd60a'
  return '#ff9f0a'
}

const card = {
  background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 14, padding: 16, marginBottom: 14,
}
const sectionTitle = {
  fontSize: 13, fontWeight: 700, color: ACCENT, marginBottom: 10,
  letterSpacing: 0.3,
}

// ── 维度条 ──────────────────────────────────────────────────────────────────
function DimBar({ label, value }) {
  const v = Math.round(value || 0)
  return (
    <div style={{ marginBottom: 9 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'rgba(255,255,255,0.75)', marginBottom: 3 }}>
        <span>{label}</span><span style={{ color: ciColor(v), fontWeight: 600 }}>{v}</span>
      </div>
      <div style={{ height: 7, borderRadius: 4, background: 'rgba(255,255,255,0.07)', overflow: 'hidden' }}>
        <div style={{ width: `${v}%`, height: '100%', borderRadius: 4, background: ciColor(v), transition: 'width 0.5s' }} />
      </div>
    </div>
  )
}

// ── 状态阶梯 ────────────────────────────────────────────────────────────────
function StateLadder({ states, current }) {
  const curOrder = (states.find(s => s.key === current) || {}).order ?? 0
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {[...states].reverse().map(s => {
        const reached = s.order <= curOrder
        const isCur = s.key === current
        return (
          <div key={s.key} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
            borderRadius: 9,
            background: isCur ? ACCENT_DIM : 'transparent',
            border: isCur ? `1px solid ${ACCENT}` : '1px solid transparent',
            opacity: reached ? 1 : 0.4,
          }}>
            <div style={{
              width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700,
              background: reached ? ACCENT : 'rgba(255,255,255,0.08)',
              color: reached ? '#1a1a2e' : 'rgba(255,255,255,0.5)',
            }}>{s.order + 1}</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: isCur ? 700 : 500, color: isCur ? '#fff' : 'rgba(255,255,255,0.85)' }}>
                {s.zh} {isCur && <span style={{ fontSize: 10, color: ACCENT, marginLeft: 4 }}>当前</span>}
              </div>
              {isCur && <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2, lineHeight: 1.5 }}>{s.desc}</div>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── 主组件 ──────────────────────────────────────────────────────────────────
export default function DiscipleFormationView({ user, token }) {
  const [meta, setMeta] = useState(null)
  const [profile, setProfile] = useState(null)
  const [view, setView] = useState('dash') // dash | reflect | engines | mentor | network | history
  const [report, setReport] = useState(null)   // 最近一次评估
  const [err, setErr] = useState('')

  useEffect(() => {
    fetchDiscipleMeta().then(d => setMeta(d)).catch(() => setErr('加载失败'))
    if (token) fetchDiscipleProfile(token).then(d => setProfile(d.profile)).catch(() => {})
  }, [token])

  const dimZh = k => (meta?.dimensions || []).find(d => d.key === k)?.zh || k
  const idolZh = k => (meta?.idols || []).find(i => i.key === k)?.zh || k
  const stateZh = k => (meta?.states || []).find(s => s.key === k)?.zh || k
  const engineList = meta?.engines || []

  if (!user) return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 10 }}>
      <div style={{ fontSize: 44 }}>🧬</div>
      <div style={{ fontSize: 15, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>门徒塑造引擎</div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)' }}>登录后开始你的门徒塑造旅程</div>
    </div>
  )

  if (!meta) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 14 }}>
      {err || '加载中…'}
    </div>
  )

  const NAV = [
    { key: 'dash', label: '概览', emoji: '📊' },
    { key: 'reflect', label: '反思', emoji: '✍️' },
    { key: 'engines', label: '引擎', emoji: '⚙️' },
    { key: 'mentor', label: '导师', emoji: '🧎' },
    { key: 'network', label: '门徒', emoji: '🌳' },
    { key: 'review', label: '复盘', emoji: '📈' },
    { key: 'history', label: '历史', emoji: '🕘' },
  ]

  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* 二级导航 */}
      <div style={{ display: 'flex', gap: 4, padding: '8px 12px 6px', overflowX: 'auto', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        {NAV.map(n => (
          <button key={n.key} onClick={() => setView(n.key)} style={{
            flexShrink: 0, padding: '6px 12px', borderRadius: 16, cursor: 'pointer',
            border: '1px solid ' + (view === n.key ? ACCENT : 'rgba(255,255,255,0.12)'),
            background: view === n.key ? ACCENT_DIM : 'transparent',
            color: view === n.key ? '#fff' : 'rgba(255,255,255,0.6)',
            fontSize: 12.5, fontWeight: view === n.key ? 700 : 400, fontFamily: 'inherit',
          }}>{n.emoji} {n.label}</button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 14px 24px' }}>
        {view === 'dash' && <Dashboard profile={profile} report={report} meta={meta} dimZh={dimZh} idolZh={idolZh} stateZh={stateZh} onReflect={() => setView('reflect')} />}
        {view === 'reflect' && <Reflect token={token} onDone={(r) => { setReport(r); if (token) fetchDiscipleProfile(token).then(d => setProfile(d.profile)).catch(() => {}) }} meta={meta} dimZh={dimZh} idolZh={idolZh} stateZh={stateZh} />}
        {view === 'engines' && <Engines report={report} engineList={engineList} idolZh={idolZh} dimZh={dimZh} onReflect={() => setView('reflect')} />}
        {view === 'mentor' && <Mentor token={token} />}
        {view === 'network' && <Network token={token} stateZh={stateZh} />}
        {view === 'review' && <Review token={token} dimZh={dimZh} stateZh={stateZh} />}
        {view === 'history' && <History token={token} stateZh={stateZh} dimZh={dimZh} idolZh={idolZh} />}
      </div>
    </div>
  )
}

// ── 概览 ────────────────────────────────────────────────────────────────────
function Dashboard({ profile, report, meta, dimZh, idolZh, stateZh, onReflect }) {
  const p = profile
  const dims = p?.dimensions || {}
  const ci = p?.christlikeness_index ?? 0
  const r = report
  if (!p) return <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, padding: 20, textAlign: 'center' }}>加载画像中…</div>

  const hasData = (p.assessment_count || 0) > 0
  return (
    <div>
      {!hasData && (
        <div style={{ ...card, background: ACCENT_DIM, borderColor: ACCENT, textAlign: 'center' }}>
          <div style={{ fontSize: 30, marginBottom: 6 }}>🧬</div>
          <div style={{ fontSize: 14, color: '#fff', fontWeight: 600, marginBottom: 4 }}>开始你的门徒塑造</div>
          <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, marginBottom: 12 }}>
            评估的不是你知道多少，而是你信靠什么、顺服了什么、能否培养下一代门徒。<br />写下今天的反思，引擎会为你画出属灵画像。
          </div>
          <button onClick={onReflect} style={primaryBtn}>✍️ 写今日反思</button>
        </div>
      )}

      {/* CI + 状态 */}
      <div style={{ ...card, display: 'flex', gap: 16, alignItems: 'center' }}>
        <div style={{ textAlign: 'center', flexShrink: 0 }}>
          <div style={{ fontSize: 38, fontWeight: 800, color: ciColor(ci), lineHeight: 1 }}>{Math.round(ci)}</div>
          <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.45)', marginTop: 3 }}>像基督指数</div>
        </div>
        <div style={{ flex: 1, borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>当前属灵状态</div>
          <div style={{ fontSize: 17, fontWeight: 700, color: '#fff', margin: '2px 0' }}>{stateZh(p.spiritual_state)}</div>
          {p.next_state && <div style={{ fontSize: 11.5, color: ACCENT }}>下一站 → {stateZh(p.next_state)}</div>}
        </div>
      </div>

      {/* 今日顺服 + 偶像 */}
      {(r?.next_step || p.growth_edge || p.top_idol) && (
        <div style={card}>
          {(r?.next_step) && (
            <div style={{ marginBottom: 12 }}>
              <div style={sectionTitle}>🚶 今日顺服行动</div>
              <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.9)', lineHeight: 1.6 }}>{r.next_step}</div>
            </div>
          )}
          <div style={{ display: 'flex', gap: 10 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>成长边界</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: ACCENT }}>{dimZh(p.growth_edge)}</div>
            </div>
            {p.top_idol && (
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>当前最大偶像</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#ff9f0a' }}>{idolZh(p.top_idol)}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 维度 */}
      <div style={card}>
        <div style={sectionTitle}>🌿 塑造维度</div>
        {(meta.dimensions || []).map(d => <DimBar key={d.key} label={d.zh} value={dims[d.key]} />)}
      </div>

      {/* 状态阶梯 */}
      <div style={card}>
        <div style={sectionTitle}>🪜 门徒成长之路</div>
        <StateLadder states={meta.states} current={p.spiritual_state} />
      </div>

      {/* DMI */}
      {p.dmi && (
        <div style={card}>
          <div style={sectionTitle}>🌳 门徒倍增指数 (DMI)</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', textAlign: 'center' }}>
            <Mini label="DMI" value={Math.round(p.dmi.dmi)} accent />
            <Mini label="深度" value={p.dmi.depth} />
            <Mini label="广度" value={p.dmi.breadth} />
            <Mini label="复制率" value={p.dmi.reproduction_rate} />
          </div>
        </div>
      )}

      {/* 画像数据来源（整合层：吸收了哪些子系统） */}
      {p.provenance?.length > 0 && (
        <div style={card}>
          <div style={sectionTitle}>🔗 画像数据来源</div>
          <div style={{ fontSize: 11.5, color: 'rgba(255,255,255,0.45)', marginBottom: 8 }}>
            本画像不只看你的反思，还融合了这些子系统的最新信号：
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {p.provenance.map((pr, i) => (
              <span key={i} style={{ fontSize: 11.5, padding: '4px 9px', borderRadius: 12, background: ACCENT_DIM, color: '#cbb8ff', border: '1px solid rgba(167,139,250,0.3)' }}>
                {pr.label}{pr.detail ? ` · ${pr.detail}` : ''}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Neo4j 图谱洞察 */}
      {p.graph?.enabled && p.graph.insights?.length > 0 && (
        <div style={card}>
          <div style={sectionTitle}>🕸 属灵图谱洞察</div>
          {p.graph.insights.map((g, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '5px 0', color: 'rgba(255,255,255,0.8)' }}>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>{g.label}</span>
              <span style={{ fontWeight: 600, color: ACCENT }}>{Array.isArray(g.value) ? g.value.join('、') : g.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── 复盘 ──
function Review({ token, dimZh, stateZh }) {
  const [kind, setKind] = useState('weekly')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [milestones, setMilestones] = useState([])
  useEffect(() => { if (token) fetchDiscipleMilestones(token).then(d => setMilestones(d.items || [])).catch(() => {}) }, [token])
  useEffect(() => {
    let live = true
    setLoading(true); setData(null)
    fetchDiscipleReview(kind, token).then(d => { if (live) setData(d) }).catch(() => { if (live) setData({ has_data: false, message: '加载失败' }) }).finally(() => live && setLoading(false))
    return () => { live = false }
  }, [kind, token])

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {[['weekly', '本周'], ['monthly', '本月']].map(([k, lbl]) => (
          <button key={k} onClick={() => setKind(k)} style={{
            flex: 1, padding: '8px', borderRadius: 9, cursor: 'pointer', fontFamily: 'inherit',
            border: '1px solid ' + (kind === k ? ACCENT : 'rgba(255,255,255,0.12)'),
            background: kind === k ? ACCENT_DIM : 'transparent',
            color: kind === k ? '#fff' : 'rgba(255,255,255,0.6)', fontSize: 13, fontWeight: kind === k ? 700 : 400,
          }}>{lbl}复盘</button>
        ))}
      </div>
      {loading && <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, padding: 20, textAlign: 'center' }}>生成中…</div>}
      {data && !data.has_data && <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 13, padding: 20, textAlign: 'center', lineHeight: 1.7 }}>{data.message}</div>}
      {data && data.has_data && (
        <div>
          <div style={{ ...card, display: 'flex', gap: 16, alignItems: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 30, fontWeight: 800, color: ciColor(data.ci_avg) }}>{Math.round(data.ci_avg)}</div>
              <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.45)' }}>CI 均值</div>
            </div>
            <div style={{ flex: 1, borderLeft: '1px solid rgba(255,255,255,0.1)', paddingLeft: 16 }}>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)' }}>近 {data.days} 天 · {data.count} 次反思</div>
              <div style={{ fontSize: 13, color: data.ci_trend >= 0 ? '#34c759' : '#ff9f0a', fontWeight: 600, marginTop: 2 }}>
                趋势 {data.ci_trend >= 0 ? '↑' : '↓'}{Math.abs(data.ci_trend)}
              </div>
            </div>
          </div>
          <div style={card}>
            <div style={sectionTitle}>📝 牧养复盘</div>
            <p style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.9)', lineHeight: 1.7, margin: '0 0 10px' }}>{data.summary}</p>
            {data.invitation && <p style={{ fontSize: 13, color: ACCENT, lineHeight: 1.6, margin: '0 0 10px' }}>👣 {data.invitation}</p>}
            {data.scripture?.text && (
              <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.65)', fontStyle: 'italic', borderLeft: `2px solid ${ACCENT}`, paddingLeft: 10 }}>
                {data.scripture.text}{data.scripture.ref ? ` — ${data.scripture.ref}` : ''}
              </div>
            )}
          </div>
          <div style={card}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
              <div><span style={{ color: 'rgba(255,255,255,0.45)' }}>最稳：</span><span style={{ color: '#34c759' }}>{dimZh(data.strongest)}</span></div>
              <div><span style={{ color: 'rgba(255,255,255,0.45)' }}>边界：</span><span style={{ color: ACCENT }}>{dimZh(data.weakest)}</span></div>
            </div>
            {data.next_state && <div style={{ fontSize: 12.5, marginTop: 8, color: 'rgba(255,255,255,0.6)' }}>🦄 状态迁移建议 → <span style={{ color: ACCENT, fontWeight: 600 }}>{stateZh(data.next_state)}</span></div>}
          </div>
        </div>
      )}
      {milestones.length > 0 && (
        <div style={card}>
          <div style={sectionTitle}>🏛 属灵里程碑</div>
          {milestones.map((m, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', padding: '7px 0', borderBottom: i < milestones.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
              <span style={{ fontSize: 15 }}>{m.kind === 'milestone' ? (m.up ? '🎉' : '🔄') : '🔔'}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12.5, fontWeight: 600, color: m.kind === 'milestone' ? '#34c759' : '#ff9f0a' }}>{m.title}</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.65)', lineHeight: 1.5 }}>{m.body}</div>
                <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.3)', marginTop: 2 }}>{(m.created_at || '').slice(0, 10)}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Mini({ label, value, accent }) {
  return (
    <div>
      <div style={{ fontSize: 20, fontWeight: 700, color: accent ? ACCENT : '#fff' }}>{value}</div>
      <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>{label}</div>
    </div>
  )
}

// ── 反思评估 ────────────────────────────────────────────────────────────────
function Reflect({ token, onDone, meta, dimZh, idolZh, stateZh }) {
  const [journal, setJournal] = useState('')
  const [scripture, setScripture] = useState('')
  const [prayer, setPrayer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [err, setErr] = useState('')

  async function submit() {
    if (!journal.trim()) { setErr('请至少写下今天的反思'); return }
    setSubmitting(true); setErr('')
    try {
      const r = await assessDisciple({ journal, scripture, prayer }, token)
      setResult(r); onDone(r)
    } catch (e) { setErr(e.message || '评估失败') }
    finally { setSubmitting(false) }
  }

  if (result) {
    const m = result.mentor || {}
    return (
      <div>
        <div style={{ ...card, borderColor: ACCENT }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff' }}>{stateZh(result.spiritual_state)}</div>
            <div style={{ fontSize: 12, color: ciColor(result.christlikeness_index) }}>CI {Math.round(result.christlikeness_index)}</div>
          </div>
          {result.source === 'heuristic' && <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)' }}>（确定性分析，AI 暂不可用）</div>}
        </div>
        {result.reactions?.length > 0 && (
          <div style={{ ...card, borderColor: 'rgba(255,159,10,0.4)' }}>
            {result.reactions.map((rx, i) => (
              <div key={i} style={{ display: 'flex', gap: 9, alignItems: 'flex-start', marginBottom: i < result.reactions.length - 1 ? 8 : 0 }}>
                <span style={{ fontSize: 16 }}>{rx.kind === 'milestone' ? (rx.up ? '🎉' : '🔄') : '🔔'}</span>
                <div>
                  <div style={{ fontSize: 12.5, fontWeight: 600, color: rx.kind === 'milestone' ? '#34c759' : '#ff9f0a' }}>{rx.title}</div>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>{rx.body}</div>
                </div>
              </div>
            ))}
          </div>
        )}
        <MentorReport m={m} stateZh={stateZh} />
        <button onClick={() => { setResult(null); setJournal(''); setScripture(''); setPrayer('') }} style={{ ...primaryBtn, width: '100%', marginTop: 4 }}>再写一篇</button>
      </div>
    )
  }

  return (
    <div>
      <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6, marginBottom: 14 }}>
        诚实地写下今天的处境、情绪与挣扎。引擎会从中辨识你的信念、偶像、顺服与呼召，给出今日的一步顺服。
      </div>
      <label style={lbl}>今日反思 / 处境 *</label>
      <textarea value={journal} onChange={e => setJournal(e.target.value)} placeholder="今天发生了什么？我有什么感受、渴望或害怕？我在挣扎什么？" style={{ ...ta, minHeight: 130 }} />
      <label style={lbl}>今日经文（可选）</label>
      <input value={scripture} onChange={e => setScripture(e.target.value)} placeholder="例：马太福音 6:33" style={inp} />
      <label style={lbl}>今日祷告（可选）</label>
      <textarea value={prayer} onChange={e => setPrayer(e.target.value)} placeholder="主啊……" style={{ ...ta, minHeight: 70 }} />
      {err && <div style={{ color: '#ff6b6b', fontSize: 12, marginBottom: 8 }}>{err}</div>}
      <button onClick={submit} disabled={submitting} style={{ ...primaryBtn, width: '100%', opacity: submitting ? 0.6 : 1 }}>
        {submitting ? '引擎分析中…' : '🧬 提交并评估'}
      </button>
    </div>
  )
}

function MentorReport({ m, stateZh }) {
  const rows = [
    ['🔍 根因分析', m.root_cause],
    ['📖 圣经真理', m.biblical_truth],
    ['🚶 顺服行动', m.obedience_step],
    ['🙏 回应祷告', m.prayer],
    ['🌱 成长机会', m.growth_opportunity],
  ]
  return (
    <div style={card}>
      <div style={sectionTitle}>🧎 导师之言</div>
      {rows.filter(r => r[1]).map(([h, t]) => (
        <div key={h} style={{ marginBottom: 11 }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: ACCENT, marginBottom: 3 }}>{h}</div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.88)', lineHeight: 1.6 }}>{t}</div>
        </div>
      ))}
      {m.next_transition && (
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', marginTop: 4, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          🪜 下一个状态建议：<span style={{ color: ACCENT, fontWeight: 600 }}>{stateZh(m.next_transition)}</span>
        </div>
      )}
    </div>
  )
}

// ── 11 引擎卡片 ─────────────────────────────────────────────────────────────
function Engines({ report, engineList, idolZh, dimZh, onReflect }) {
  const [open, setOpen] = useState(null)
  if (!report) return (
    <div style={{ textAlign: 'center', padding: 24 }}>
      <div style={{ fontSize: 36, marginBottom: 10 }}>⚙️</div>
      <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.6)', marginBottom: 14, lineHeight: 1.6 }}>
        完成一次反思评估后，<br />11 个引擎的分析会显示在这里。
      </div>
      <button onClick={onReflect} style={primaryBtn}>✍️ 去写反思</button>
    </div>
  )
  const eng = report.engines || {}
  return (
    <div>
      {engineList.map(e => {
        const data = eng[e.key] || {}
        const isOpen = open === e.key
        return (
          <div key={e.key} style={{ ...card, marginBottom: 10, padding: 0, overflow: 'hidden' }}>
            <div onClick={() => setOpen(isOpen ? null : e.key)} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '13px 15px', cursor: 'pointer' }}>
              <div style={{ fontSize: 22 }}>{e.emoji}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{e.zh}</div>
                <div style={{ fontSize: 11.5, color: 'rgba(255,255,255,0.45)' }}>{e.desc}</div>
              </div>
              <EngineBadge ek={e.key} data={data} />
              <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12 }}>{isOpen ? '▲' : '▼'}</div>
            </div>
            {isOpen && (
              <div style={{ padding: '0 15px 14px', fontSize: 13, color: 'rgba(255,255,255,0.85)', lineHeight: 1.65 }}>
                <EngineDetail ek={e.key} data={data} idolZh={idolZh} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function EngineBadge({ ek, data }) {
  let v = null
  if (typeof data.score === 'number') v = Math.round(data.score)
  else if (ek === 'idol' && data.risk_level) return <span style={{ fontSize: 11, fontWeight: 700, color: RISK_COLOR[data.risk_level] || '#fff' }}>{RISK_ZH[data.risk_level] || data.risk_level}</span>
  else if (ek === 'multiplication' && typeof data.dmi === 'number') v = Math.round(data.dmi)
  else if (ek === 'calling' && typeof data.confidence === 'number') v = Math.round(data.confidence)
  else if (ek === 'parenting' && typeof data.readiness === 'number') v = Math.round(data.readiness)
  if (v == null) return null
  return <span style={{ fontSize: 13, fontWeight: 700, color: ciColor(v) }}>{v}</span>
}

function EngineDetail({ ek, data, idolZh }) {
  return (
    <div>
      {data.summary && <p style={{ margin: '0 0 8px' }}>{data.summary}</p>}
      {ek === 'idol' && data.scores && (
        <div style={{ margin: '6px 0' }}>
          {Object.entries(data.scores).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => (
            <DimBar key={k} label={idolZh(k)} value={v} />
          ))}
          {data.gospel_remedy && <p style={{ margin: '8px 0 4px', color: '#7ee0a0' }}>💊 福音解药：{data.gospel_remedy}</p>}
          {data.demolition_plan && <p style={{ margin: 0, color: 'rgba(255,255,255,0.7)' }}>🔨 拆除计划：{data.demolition_plan}</p>}
        </div>
      )}
      {ek === 'character' && data.scores && (
        <div style={{ margin: '6px 0' }}>
          {Object.entries(data.scores).map(([k, v]) => <DimBar key={k} label={CHAR_ZH[k] || k} value={v} />)}
        </div>
      )}
      {ek === 'faith' && (data.false_beliefs?.length > 0 || data.true_beliefs?.length > 0) && (
        <div>
          {data.false_beliefs?.length > 0 && <p style={{ margin: '4px 0', color: '#ff9f9f' }}>✗ {data.false_beliefs.join('；')}</p>}
          {data.true_beliefs?.length > 0 && <p style={{ margin: '4px 0', color: '#7ee0a0' }}>✓ {data.true_beliefs.join('；')}</p>}
        </div>
      )}
      {ek === 'multiplication' && (
        <p style={{ margin: '4px 0', color: 'rgba(255,255,255,0.6)' }}>深度 {data.depth} · 广度 {data.breadth} · 复制率 {data.reproduction_rate} · 时长 {data.duration_months} 月</p>
      )}
    </div>
  )
}

const CHAR_ZH = {
  humility: '谦卑', patience: '忍耐', gentleness: '温柔', courage: '勇气',
  faithfulness: '忠心', self_control: '节制', holiness: '圣洁', love: '爱',
}

// ── AI 导师对话 ─────────────────────────────────────────────────────────────
function Mentor({ token }) {
  const [msgs, setMsgs] = useState([])
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function send() {
    const question = q.trim()
    if (!question || loading) return
    setMsgs(m => [...m, { role: 'user', text: question }]); setQ(''); setLoading(true)
    try {
      const r = await askDiscipleMentor(question, token)
      setMsgs(m => [...m, { role: 'mentor', text: r.answer || '…' }])
    } catch (e) {
      setMsgs(m => [...m, { role: 'mentor', text: e.message || '导师暂时无法回应' }])
    } finally { setLoading(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 320 }}>
      <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6, marginBottom: 12 }}>
        门徒塑造导师不为提供信息，而要把你带到基督面前。问祂关于你生命、关系、决定与顺服的问题。
      </div>
      <div style={{ flex: 1 }}>
        {msgs.length === 0 && (
          <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13, textAlign: 'center', padding: 20 }}>
            例如：「我在做一个重大决定，怎么分辨是出于信心还是惧怕？」
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 9 }}>
            <div style={{
              maxWidth: '82%', padding: '9px 13px', borderRadius: 13, fontSize: 13.5, lineHeight: 1.6,
              background: m.role === 'user' ? ACCENT_DIM : 'rgba(255,255,255,0.05)',
              border: '1px solid ' + (m.role === 'user' ? ACCENT : 'rgba(255,255,255,0.08)'),
              color: m.role === 'user' ? '#fff' : 'rgba(255,255,255,0.9)',
            }}>{m.text}</div>
          </div>
        ))}
        {loading && <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12, padding: 6 }}>导师默想中…</div>}
        <div ref={endRef} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <input value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="向导师提问…" style={{ ...inp, marginBottom: 0, flex: 1 }} />
        <button onClick={send} disabled={loading} style={{ ...primaryBtn, padding: '0 16px' }}>发送</button>
      </div>
    </div>
  )
}

// ── 门徒网络 ────────────────────────────────────────────────────────────────
const REL_ZH = { MENTOR: '属灵导师', DISCIPLER: '门徒', SPIRITUAL_PARENT: '属灵儿女', PEER: '属灵同伴' }

function Network({ token }) {
  const [net, setNet] = useState(null)
  const [dmi, setDmi] = useState(null)
  const [graph, setGraph] = useState(null)
  const [name, setName] = useState('')
  const [type, setType] = useState('DISCIPLER')
  const [adding, setAdding] = useState(false)
  const [err, setErr] = useState('')

  const load = () => fetchDiscipleNetwork(token).then(d => { setNet(d.network); setDmi(d.dmi) }).catch(() => setErr('加载失败'))
  useEffect(() => { if (token) { load(); fetchDiscipleGraph(token).then(setGraph).catch(() => {}) } }, [token])

  async function add() {
    if (!name.trim()) return
    setAdding(true); setErr('')
    try {
      const d = await addDiscipleRelationship({ disciple_name: name.trim(), relationship_type: type }, token)
      setNet(d.network); setDmi(d.dmi); setName('')
    } catch (e) { setErr(e.message) } finally { setAdding(false) }
  }
  async function end(id) {
    try { await endDiscipleRelationship(id, token); load() } catch { /* ignore */ }
  }

  if (!net) return <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, padding: 20, textAlign: 'center' }}>{err || '加载中…'}</div>

  return (
    <div>
      <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.5)', lineHeight: 1.6, marginBottom: 12 }}>
        提后 2:2 —— 你从谁领受，又把所领受的交托给谁。成熟的标志是复制：培养能再带门徒的门徒。
      </div>
      {dmi && (
        <div style={card}>
          <div style={sectionTitle}>🌳 倍增健康度</div>
          <div style={{ display: 'flex', justifyContent: 'space-between', textAlign: 'center' }}>
            <Mini label="DMI" value={Math.round(dmi.dmi)} accent />
            <Mini label="深度" value={net.depth} />
            <Mini label="直接门徒" value={net.breadth} />
            <Mini label="第二代" value={net.second_generation} />
          </div>
        </div>
      )}

      <div style={card}>
        <div style={sectionTitle}>➕ 添加我正在陪伴的人</div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input value={name} onChange={e => setName(e.target.value)} placeholder="门徒姓名" style={{ ...inp, marginBottom: 0, flex: 1 }} />
          <select value={type} onChange={e => setType(e.target.value)} style={{ ...inp, marginBottom: 0, width: 110 }}>
            <option value="DISCIPLER">我带的门徒</option>
            <option value="MENTOR">我的导师</option>
            <option value="PEER">属灵同伴</option>
            <option value="SPIRITUAL_PARENT">属灵儿女</option>
          </select>
        </div>
        <button onClick={add} disabled={adding} style={{ ...primaryBtn, width: '100%' }}>{adding ? '添加中…' : '添加'}</button>
        {err && <div style={{ color: '#ff6b6b', fontSize: 12, marginTop: 6 }}>{err}</div>}
      </div>

      {graph?.enabled && graph.insights?.length > 0 && (
        <div style={card}>
          <div style={sectionTitle}>🕸 属灵图谱洞察</div>
          {graph.insights.map((g, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, padding: '5px 0', color: 'rgba(255,255,255,0.8)' }}>
              <span style={{ color: 'rgba(255,255,255,0.5)' }}>{g.label}</span>
              <span style={{ fontWeight: 600, color: ACCENT }}>{Array.isArray(g.value) ? g.value.join('、') : g.value}</span>
            </div>
          ))}
        </div>
      )}

      <div style={card}>
        <div style={sectionTitle}>🤝 我的门徒关系</div>
        {net.relationships.length === 0 && <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.4)' }}>还没有添加门徒关系。</div>}
        {net.relationships.map((r, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderBottom: i < net.relationships.length - 1 ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
            <div style={{ width: 34, height: 34, borderRadius: '50%', background: ACCENT_DIM, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🧑</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13.5, color: '#fff' }}>{r.disciple_name || r.disciple_email}</div>
              <div style={{ fontSize: 11, color: ACCENT }}>{REL_ZH[r.relationship_type] || r.relationship_type}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── 历史 ────────────────────────────────────────────────────────────────────
function History({ token, stateZh, dimZh, idolZh }) {
  const [items, setItems] = useState(null)
  useEffect(() => { if (token) fetchDiscipleHistory(token, 30).then(d => setItems(d.items || [])).catch(() => setItems([])) }, [token])
  if (!items) return <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, padding: 20, textAlign: 'center' }}>加载中…</div>
  if (items.length === 0) return <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 13, padding: 20, textAlign: 'center' }}>还没有评估记录。</div>
  return (
    <div>
      {items.map((it, i) => (
        <div key={i} style={{ ...card, marginBottom: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: ACCENT }}>{stateZh(it.spiritual_state)}</span>
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{(it.created_at || '').slice(0, 16).replace('T', ' ')}</span>
          </div>
          {it.journal && <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.7)', lineHeight: 1.5, marginBottom: 6, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>{it.journal}</div>}
          <div style={{ display: 'flex', gap: 12, fontSize: 11.5, color: 'rgba(255,255,255,0.55)' }}>
            <span>CI {Math.round(it.christlikeness_index || 0)}</span>
            {it.growth_edge && <span>边界·{dimZh(it.growth_edge)}</span>}
            {it.top_idol && <span style={{ color: '#ff9f0a' }}>偶像·{idolZh(it.top_idol)}</span>}
          </div>
          {it.next_step && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', marginTop: 6 }}>🚶 {it.next_step}</div>}
        </div>
      ))}
    </div>
  )
}

// ── shared styles ───────────────────────────────────────────────────────────
const primaryBtn = {
  background: ACCENT, border: 'none', borderRadius: 9, color: '#1a1a2e',
  fontSize: 13.5, fontWeight: 700, padding: '10px 16px', cursor: 'pointer', fontFamily: 'inherit',
}
const lbl = { display: 'block', fontSize: 12, color: 'rgba(255,255,255,0.55)', margin: '10px 0 5px' }
const inp = {
  width: '100%', boxSizing: 'border-box', padding: '9px 11px', marginBottom: 4,
  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 8, color: '#fff', fontSize: 13, fontFamily: 'inherit', outline: 'none',
}
const ta = { ...inp, resize: 'vertical', lineHeight: 1.6 }
