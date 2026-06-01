/**
 * WaitingPathPage — 等候之路 / Waiting Transformation Module
 *
 * 把「等待戈多」(被动、虚无、焦虑、幻想式等待) 温柔地分辨与转化为
 * 「等候上帝」(在不确定中仍信靠、忠心行动、不把结果当偶像)。
 * 不定罪、不贴标签，是反思 / 分辨 / 陪伴式功能。
 * 入口：今日心镜 (SoulDashboard) 卡片。
 */
import { useEffect, useState } from 'react'
import {
  fetchWaitingCases, createWaitingCase, analyzeWaitingCase,
  generateWaitingPractices, fetchWaitingCase, completeWaitingPractice,
  submitWaitingReflection,
} from './api'
import { getToken } from './auth'

const SLIDERS = [
  { key: 'anxiety_level',       name: '焦虑程度',   hint: '想到这件事，我有多焦躁不安？' },
  { key: 'hope_level',          name: '盼望程度',   hint: '我对它仍存着多少有根的盼望？' },
  { key: 'passivity_level',     name: '被动程度',   hint: '我是否在「耗着」、什么也不做地等？' },
  { key: 'fantasy_level',       name: '幻想程度',   hint: '我多常用想象的剧情来填补等待？' },
  { key: 'trust_level',         name: '信靠程度',   hint: '在不确定中，我有多信靠神？' },
  { key: 'obedience_readiness', name: '顺服预备',   hint: '无论结果如何，我多愿意继续顺服？' },
  { key: 'action_clarity',      name: '行动清晰度', hint: '我多清楚此刻能忠心做的小事？' },
]

const TYPE = {
  godot_waiting: { label: '等待戈多', color: '#ff8787', desc: '更接近被动、虚无、焦虑、幻想式的等待。' },
  god_waiting:   { label: '等候上帝', color: '#34c759', desc: '更接近信靠、盼望、忠心行动的等候。' },
  mixed:         { label: '二者交织', color: '#ffd43b', desc: '两种等待同时存在——这很真实，也正是被塑造的地方。' },
  unknown:       { label: '尚不清晰', color: '#868e96', desc: '信息还不够，先从命名你的等待开始。' },
}

const SCORE_BARS = [
  { key: 'godot_waiting_score', name: '等待戈多倾向', color: '#ff8787' },
  { key: 'god_waiting_score',   name: '等候上帝倾向', color: '#34c759' },
  { key: 'idolatry_risk',       name: '偶像化风险',   color: '#ffa94d' },
  { key: 'passivity_risk',      name: '被动风险',     color: '#da77f2' },
  { key: 'hope_stability',      name: '盼望稳定度',   color: '#5ac8fa' },
]
const ANALYSIS_FIELDS = [
  { key: 'waiting_object',             label: '等待对象' },
  { key: 'emotional_pattern',          label: '情绪模式' },
  { key: 'possible_idolatry_pattern',  label: '偶像风险' },
  { key: 'passivity_pattern',          label: '被动风险' },
  { key: 'faith_hope_love_direction',  label: '信 · 望 · 爱 方向' },
]

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 14, marginBottom: 12 }

export default function WaitingPathPage({ user, onBack, onNeedLogin }) {
  const [view, setView] = useState('home')   // home | create | detail
  const [cases, setCases] = useState([])
  const [active, setActive] = useState(null)  // detail bundle {case, practices, reflections, analysis}
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { loadHome() }, [])

  async function loadHome() {
    const token = getToken(); if (!token) return
    setLoading(true)
    try { const r = await fetchWaitingCases(token); setCases(r.cases || []) }
    catch (e) { setError(e.message || '加载失败') }
    finally { setLoading(false) }
  }

  async function openCase(id) {
    const token = getToken(); if (!token) { onNeedLogin && onNeedLogin(); return }
    setLoading(true); setError('')
    try { const r = await fetchWaitingCase(id, token); setActive(r); setView('detail'); window.scrollTo({ top: 0 }) }
    catch (e) { setError(e.message || '加载失败') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={view === 'home' ? onBack : () => { setView('home'); loadHome() }} style={backBtn}>‹</button>
          <div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>等候之路</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>从等待戈多，到等候上帝</div>
          </div>
        </div>
        {view === 'home' && <button onClick={() => setView('create')} style={primaryPill}>＋ 新建</button>}
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 720, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {view === 'home' && <HomeView cases={cases} loading={loading} onOpen={openCase} onNew={() => setView('create')} />}
        {view === 'create' && <CreateView onCancel={() => setView('home')} onCreated={(bundle) => { setActive(bundle); setView('detail'); loadHome() }} onNeedLogin={onNeedLogin} setError={setError} />}
        {view === 'detail' && active && <DetailView bundle={active} reload={openCase} setError={setError} onNeedLogin={onNeedLogin} />}
      </div>
    </div>
  )
}

function HomeView({ cases, loading, onOpen, onNew }) {
  return (
    <>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(52,199,89,0.10), rgba(90,200,250,0.08))' }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>🕯️ 等候，不是枯等</div>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: 'rgba(255,255,255,0.78)' }}>
          等待可以是焦虑、被动、幻想式的「等戈多」；也可以是有信、有望、有爱、有行动、
          有顺服的「等候上帝」。这里陪你温柔地分辨，并在等待中被塑造——而非被消耗。
        </div>
      </div>
      {loading && <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>加载中…</div>}
      {!loading && cases.length === 0 && (
        <div style={{ ...card, textAlign: 'center', padding: '28px 14px' }}>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 14 }}>还没有等待案例。你此刻在等什么？</div>
          <button onClick={onNew} style={primaryBtn}>＋ 命名我的等待</button>
        </div>
      )}
      {cases.map(c => {
        const t = TYPE[c.waiting_type] || TYPE.unknown
        return (
          <div key={c.id} onClick={() => onOpen(c.id)} style={{ ...card, cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
              <div style={{ fontSize: 14, fontWeight: 600, flex: 1 }}>{c.waiting_for}</div>
              <span style={{ fontSize: 11, fontWeight: 700, color: t.color, padding: '2px 8px', borderRadius: 10, background: `${t.color}22`, flexShrink: 0 }}>{t.label}</span>
            </div>
            <div style={{ display: 'flex', gap: 14, marginTop: 10, fontSize: 11, color: 'rgba(255,255,255,0.45)' }}>
              <span>焦虑 {Math.round((c.anxiety_level || 0))}</span>
              <span>盼望 {Math.round((c.hope_level || 0))}</span>
              <span>{(c.created_at || '').slice(0, 10)}</span>
            </div>
          </div>
        )
      })}
    </>
  )
}

function CreateView({ onCancel, onCreated, onNeedLogin, setError }) {
  const [waitingFor, setWaitingFor] = useState('')
  const [desc, setDesc] = useState('')
  const [vals, setVals] = useState(Object.fromEntries(SLIDERS.map(s => [s.key, 5])))
  const [busy, setBusy] = useState(false)

  async function submit() {
    const token = getToken(); if (!token) { onNeedLogin && onNeedLogin(); return }
    if (!waitingFor.trim()) { setError('请先写下你在等什么'); return }
    setBusy(true); setError('')
    try {
      const created = await createWaitingCase({ waiting_for: waitingFor.trim(), waiting_description: desc.trim(), ...vals }, token)
      const id = created.case.id
      await analyzeWaitingCase(id, token, true)
      const bundle = await fetchWaitingCase(id, token)
      onCreated(bundle)
    } catch (e) { setError(e.message || '提交失败') }
    finally { setBusy(false) }
  }

  return (
    <>
      <div style={card}>
        <label style={lbl}>我正在等什么？</label>
        <input value={waitingFor} onChange={e => setWaitingFor(e.target.value)} placeholder="如：一个 offer、一段关系的回应、一个突破…" style={input} />
        <label style={{ ...lbl, marginTop: 14 }}>具体描述（可选）</label>
        <textarea value={desc} onChange={e => setDesc(e.target.value)} rows={3} placeholder="发生了什么？你最害怕它不来的原因是什么？" style={{ ...input, resize: 'vertical' }} />
      </div>
      <div style={card}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 6 }}>诚实地为此刻打分（0–10）</div>
        {SLIDERS.map(s => (
          <div key={s.key} style={{ marginTop: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
              <span style={{ color: 'rgba(255,255,255,0.78)' }}>{s.name}</span>
              <span style={{ color: '#5ac8fa', fontWeight: 700 }}>{vals[s.key]}</span>
            </div>
            <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)', marginBottom: 4 }}>{s.hint}</div>
            <input type="range" min="0" max="10" step="1" value={vals[s.key]} onChange={e => setVals(v => ({ ...v, [s.key]: parseInt(e.target.value) }))} style={{ width: '100%', accentColor: '#5ac8fa' }} />
          </div>
        ))}
      </div>
      <button onClick={submit} disabled={busy} style={primaryBtn}>{busy ? '正在分辨…' : '提交并分辨'}</button>
      <button onClick={onCancel} style={{ ...primaryBtn, background: 'rgba(255,255,255,0.06)', marginTop: 8 }}>取消</button>
      <div style={footNote}>本工具是反思与陪伴，不替代专业心理帮助。若你正经历极端的痛苦或绝望，请联系信任的人或寻求专业支持。</div>
    </>
  )
}

function DetailView({ bundle, reload, setError, onNeedLogin }) {
  const c = bundle.case
  const a = bundle.analysis || {}
  const [practices, setPractices] = useState(bundle.practices || [])
  const [busy, setBusy] = useState(false)
  // 同步：reload 后 bundle 变化时刷新本地操练状态（useState 初值不会在 re-render 时重跑）
  useEffect(() => { setPractices(bundle.practices || []) }, [bundle])
  const t = TYPE[a.waiting_type || c.waiting_type] || TYPE.unknown
  const crisis = a.crisis_flag

  async function genPractices() {
    const token = getToken(); if (!token) { onNeedLogin && onNeedLogin(); return }
    setBusy(true); setError('')
    try { const r = await generateWaitingPractices(c.id, token); setPractices(r.practices || []) }
    catch (e) { setError(e.message || '生成失败') }
    finally { setBusy(false) }
  }

  return (
    <>
      {crisis && (
        <div style={{ ...card, borderColor: 'rgba(255,135,135,0.5)', background: 'rgba(255,135,135,0.08)' }}>
          <div style={{ fontSize: 13, lineHeight: 1.75, color: '#ffb3b3' }}>{a.summary}</div>
        </div>
      )}

      <div style={{ ...card, background: `linear-gradient(135deg, ${t.color}1f, rgba(255,255,255,0.03))`, borderColor: `${t.color}55` }}>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>我正在等：{c.waiting_for}</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: t.color }}>{t.label}</div>
        <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.7)', marginTop: 6, lineHeight: 1.6 }}>{crisis ? t.desc : (a.summary || t.desc)}</div>
      </div>

      {/* 分数可视化 */}
      <div style={card}>
        <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 12 }}>分辨指标</div>
        {SCORE_BARS.map(b => {
          const v = Math.round((a[b.key] || 0) * 100)
          return (
            <div key={b.key} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 3 }}>
                <span style={{ color: 'rgba(255,255,255,0.7)' }}>{b.name}</span>
                <span style={{ color: b.color, fontWeight: 700 }}>{v}</span>
              </div>
              <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${v}%`, height: '100%', background: b.color, borderRadius: 3, transition: 'width .6s' }} />
              </div>
            </div>
          )
        })}
      </div>

      {/* 分析文本 */}
      {a.analysis && (
        <div style={card}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 10 }}>温柔的分辨</div>
          {ANALYSIS_FIELDS.map(f => a.analysis[f.key] && (
            <div key={f.key} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, marginBottom: 3 }}>{f.label}</div>
              <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.74)', lineHeight: 1.7 }}>{a.analysis[f.key]}</div>
            </div>
          ))}
        </div>
      )}

      {/* 建议 */}
      {a.guidance && a.guidance.length > 0 && (
        <div style={card}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#5ac8fa', marginBottom: 8 }}>温和、可执行的下一步</div>
          {a.guidance.map((g, i) => (
            <div key={i} style={{ display: 'flex', gap: 8, fontSize: 12.5, color: 'rgba(255,255,255,0.76)', lineHeight: 1.65, marginBottom: 6 }}>
              <span style={{ color: '#5ac8fa' }}>{i + 1}.</span><span>{g}</span>
            </div>
          ))}
        </div>
      )}

      {/* 反思问题 */}
      {a.reflection_questions && (
        <div style={card}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 8 }}>带着这些问题安静片刻</div>
          {a.reflection_questions.map((q, i) => (
            <div key={i} style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.66)', lineHeight: 1.7, marginBottom: 6, fontStyle: 'italic' }}>· {q}</div>
          ))}
        </div>
      )}

      {/* 7 天操练 */}
      {practices.length === 0 ? (
        <button onClick={genPractices} disabled={busy} style={primaryBtn}>{busy ? '生成中…' : '生成 7 天等候操练'}</button>
      ) : (
        <div style={{ marginTop: 4 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.7)', margin: '8px 4px' }}>🌱 7 天等候操练</div>
          {practices.map(p => <PracticeCard key={p.id} p={p} onSaved={() => reload(c.id)} setError={setError} onNeedLogin={onNeedLogin} />)}
        </div>
      )}

      {/* 复盘 */}
      <ReflectBox caseId={c.id} onSaved={() => reload(c.id)} setError={setError} onNeedLogin={onNeedLogin} />

      {bundle.reflections && bundle.reflections.length > 0 && (
        <div style={{ ...card, marginTop: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 8 }}>复盘记录</div>
          {bundle.reflections.map(r => (
            <div key={r.id} style={{ borderLeft: '2px solid rgba(255,255,255,0.12)', paddingLeft: 10, marginBottom: 10 }}>
              <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)' }}>{(r.created_at || '').slice(0, 16).replace('T', ' ')} · 信靠 {Math.round(r.trust_level)}</div>
              {r.reflection_text && <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.7)', marginTop: 3, lineHeight: 1.6 }}>{r.reflection_text}</div>}
              {r.action_taken && <div style={{ fontSize: 11.5, color: '#5ac8fa', marginTop: 3 }}>行动：{r.action_taken}</div>}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function PracticeCard({ p, onSaved, setError, onNeedLogin }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState(p.user_reflection || '')
  const [busy, setBusy] = useState(false)

  async function complete() {
    const token = getToken(); if (!token) { onNeedLogin && onNeedLogin(); return }
    setBusy(true); setError('')
    try { await completeWaitingPractice(p.id, { user_reflection: text, completed: true }, token); onSaved() }
    catch (e) { setError(e.message || '提交失败') }
    finally { setBusy(false) }
  }

  return (
    <div style={{ ...card, borderColor: p.completed ? 'rgba(52,199,89,0.35)' : 'rgba(255,255,255,0.08)' }}>
      <div onClick={() => setOpen(!open)} style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
        <span style={{ width: 26, height: 26, borderRadius: '50%', background: p.completed ? '#34c759' : 'rgba(255,255,255,0.1)', color: '#fff', fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{p.completed ? '✓' : p.day_index}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600 }}>Day {p.day_index} · {p.practice_title}</div>
        </div>
        <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && (
        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.74)', lineHeight: 1.7, marginBottom: 8 }}>{p.practice_content}</div>
          <div style={{ fontSize: 12, color: '#a78bfa', fontStyle: 'italic', marginBottom: 8 }}>💭 {p.reflection_prompt}</div>
          <textarea value={text} onChange={e => setText(e.target.value)} rows={3} placeholder="写下你的反思…" style={{ ...input, resize: 'vertical' }} />
          <button onClick={complete} disabled={busy} style={{ ...primaryBtn, marginTop: 8, padding: 10, fontSize: 13 }}>{busy ? '保存中…' : (p.completed ? '更新反思' : '完成这一天')}</button>
        </div>
      )}
    </div>
  )
}

function ReflectBox({ caseId, onSaved, setError, onNeedLogin }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [anx, setAnx] = useState(5)
  const [hope, setHope] = useState(5)
  const [trust, setTrust] = useState(5)
  const [leaning, setLeaning] = useState('mixed')
  const [action, setAction] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    const token = getToken(); if (!token) { onNeedLogin && onNeedLogin(); return }
    setBusy(true); setError('')
    try {
      await submitWaitingReflection(caseId, { reflection_text: text, anxiety_level: anx, hope_level: hope, trust_level: trust, leaning, action_taken: action }, token)
      setText(''); setAction(''); setOpen(false); onSaved()
    } catch (e) { setError(e.message || '提交失败') }
    finally { setBusy(false) }
  }

  if (!open) return <button onClick={() => setOpen(true)} style={{ ...primaryBtn, background: 'rgba(255,255,255,0.06)', marginTop: 12 }}>＋ 记录一次复盘</button>
  return (
    <div style={{ ...card, marginTop: 12 }}>
      <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>今天的等待，状态如何？</div>
      <textarea value={text} onChange={e => setText(e.target.value)} rows={3} placeholder="今天等待中发生了什么？我的内心如何？" style={{ ...input, resize: 'vertical' }} />
      {[['焦虑', anx, setAnx], ['盼望', hope, setHope], ['信靠', trust, setTrust]].map(([n, v, set]) => (
        <div key={n} style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}><span style={{ color: 'rgba(255,255,255,0.7)' }}>{n}</span><span style={{ color: '#5ac8fa', fontWeight: 700 }}>{v}</span></div>
          <input type="range" min="0" max="10" step="1" value={v} onChange={e => set(parseInt(e.target.value))} style={{ width: '100%', accentColor: '#5ac8fa' }} />
        </div>
      ))}
      <input value={action} onChange={e => setAction(e.target.value)} placeholder="今天有没有一个忠心的小行动？" style={{ ...input, marginTop: 12 }} />
      <div style={{ marginTop: 12, fontSize: 12, color: 'rgba(255,255,255,0.6)', marginBottom: 6 }}>此刻我更像——</div>
      <div style={{ display: 'flex', gap: 8 }}>
        {[['godot', '等戈多', '#ff8787'], ['mixed', '交织', '#ffd43b'], ['god', '等候上帝', '#34c759']].map(([k, l, color]) => (
          <button key={k} onClick={() => setLeaning(k)} style={{ flex: 1, padding: '8px', borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 700, background: leaning === k ? `${color}33` : 'rgba(255,255,255,0.05)', color: leaning === k ? color : 'rgba(255,255,255,0.5)' }}>{l}</button>
        ))}
      </div>
      <button onClick={submit} disabled={busy} style={{ ...primaryBtn, marginTop: 12 }}>{busy ? '保存中…' : '保存复盘'}</button>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const primaryPill = { background: 'linear-gradient(135deg, #34c759, #5ac8fa)', border: 'none', borderRadius: 14, padding: '6px 14px', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }
const lbl = { display: 'block', fontSize: 12, color: 'rgba(255,255,255,0.6)', marginBottom: 6 }
const input = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13 }
const primaryBtn = { width: '100%', padding: '14px', borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #34c759, #5ac8fa)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }
const footNote = { fontSize: 10, color: 'rgba(255,255,255,0.25)', textAlign: 'center', marginTop: 16, lineHeight: 1.6 }
