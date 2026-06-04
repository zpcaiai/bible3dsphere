/**
 * PracticeHubPage — 灵修操练（聚合：感恩 / 认罪与赦免 / 教会历 / 灵修问责 / 我的数据）
 * 单一入口减少导航碎片化。入口：今日心镜 (SoulDashboard) 卡片。
 */
import { useEffect, useState } from 'react'
import { currentSeason } from './churchCalendar'
import {
  addGratitude, fetchGratitude, deleteGratitude,
  fetchGoals, addGoal, checkinGoal, deleteGoal,
  recordConfession, exportMyData,
} from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }
const TILES = [
  { id: 'gratitude', icon: '🙏', name: '感恩日记', desc: '数算今天的恩典', color: '#34c759' },
  { id: 'confession', icon: '🕊', name: '认罪与赦免', desc: '看见 · 认罪 · 领受赦免', color: '#a78bfa' },
  { id: 'calendar', icon: '📜', name: '教会历', desc: '与普世教会同走节期', color: '#ffd43b' },
  { id: 'accountability', icon: '🤝', name: '灵修问责', desc: '立约 · 忠心 · 同行', color: '#5ac8fa' },
  { id: 'export', icon: '📦', name: '我的数据', desc: '导出属于你的记录', color: '#94a3b8' },
]

export default function PracticeHubPage({ user, onBack, onNeedLogin }) {
  const [view, setView] = useState('menu')
  const back = () => setView('menu')
  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <button onClick={view === 'menu' ? onBack : back} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>灵修操练</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>感恩 · 认罪 · 节期 · 问责 · 数据</div></div>
      </div>
      <div style={{ padding: '14px 16px 100px', maxWidth: 640, margin: '0 auto' }}>
        {view === 'menu' && TILES.map(t => (
          <button key={t.id} onClick={() => setView(t.id)} style={{ display: 'flex', alignItems: 'center', gap: 14, width: '100%', textAlign: 'left', cursor: 'pointer', ...card, borderColor: `${t.color}33` }}>
            <span style={{ fontSize: 26 }}>{t.icon}</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>{t.name}</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>{t.desc}</div>
            </div>
            <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.35)' }}>›</span>
          </button>
        ))}
        {view === 'gratitude' && <Gratitude onNeedLogin={onNeedLogin} />}
        {view === 'confession' && <Confession onNeedLogin={onNeedLogin} />}
        {view === 'calendar' && <Calendar />}
        {view === 'accountability' && <Accountability onNeedLogin={onNeedLogin} />}
        {view === 'export' && <ExportData onNeedLogin={onNeedLogin} />}
      </div>
    </div>
  )
}

function Gratitude({ onNeedLogin }) {
  const [text, setText] = useState(''); const [list, setList] = useState([]); const [busy, setBusy] = useState(false)
  useEffect(() => { load() }, [])
  async function load() { const t = getToken(); if (!t) return; try { const r = await fetchGratitude(t); setList(r.entries || []) } catch (e) {} }
  async function add() { const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return } if (!text.trim()) return; setBusy(true); try { await addGratitude(text.trim(), t); setText(''); load() } catch (e) {} finally { setBusy(false) } }
  async function del(id) { const t = getToken(); await deleteGratitude(id, t); load() }
  return (
    <>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(52,199,89,0.10), rgba(90,200,250,0.06))' }}>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: 'rgba(255,255,255,0.8)' }}>感恩使人看见恩典的手。写下今天哪怕最小的一件，让喜乐落地生根。</div>
      </div>
      <div style={card}>
        <textarea value={text} onChange={e => setText(e.target.value)} rows={2} placeholder="今天我感谢神……" style={inp} />
        <button onClick={add} disabled={busy} style={btn('#34c759')}>{busy ? '添加中…' : '＋ 数算这件恩典'}</button>
      </div>
      {list.map(g => (
        <div key={g.id} style={{ ...card, display: 'flex', justifyContent: 'space-between', gap: 10 }}>
          <div><div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.85)', lineHeight: 1.6 }}>🙏 {g.content}</div>
            <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)', marginTop: 4 }}>{(g.created_at || '').slice(0, 16).replace('T', ' ')}</div></div>
          <button onClick={() => del(g.id)} style={delBtn}>删除</button>
        </div>
      ))}
    </>
  )
}

function Confession({ onNeedLogin }) {
  const [step, setStep] = useState(0); const [verse, setVerse] = useState(null); const [busy, setBusy] = useState(false)
  const STEPS = [
    { t: '安静', d: '来到神面前，深呼吸。他不是来定你的罪，是来释放你。' },
    { t: '省察', d: '求圣灵光照：今天有什么言语、行为、念头，亏欠了神与人？不必急，诚实就好。' },
    { t: '认罪', d: '在心里、或低声向神说出来。承认不是为了羞耻，是为了交托。' },
    { t: '舍弃', d: '一句祷告：「我愿意离开它，求你帮助我转向你。」' },
  ]
  async function receive() { const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return } setBusy(true); try { const r = await recordConfession(t); setVerse(r.scripture); setStep(STEPS.length) } catch (e) {} finally { setBusy(false) } }
  return (
    <>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(167,139,250,0.12), rgba(90,200,250,0.06))' }}>
        <div style={{ fontSize: 13, lineHeight: 1.75, color: 'rgba(255,255,255,0.82)' }}>这是你与神之间的时刻。<strong style={{ color: '#a78bfa' }}>本功能不保存任何内容</strong>——它只陪你走一遍认罪与领受赦免。</div>
      </div>
      {step < STEPS.length ? (
        <div style={card}>
          <div style={{ fontSize: 11, color: '#a78bfa', fontWeight: 700, marginBottom: 8 }}>第 {step + 1} / {STEPS.length} 步</div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{STEPS[step].t}</div>
          <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.78)', lineHeight: 1.8 }}>{STEPS[step].d}</div>
          <button onClick={() => step < STEPS.length - 1 ? setStep(step + 1) : receive()} disabled={busy} style={btn('#a78bfa')}>
            {busy ? '…' : step < STEPS.length - 1 ? '继续' : '领受赦免的确据'}
          </button>
        </div>
      ) : (
        <div style={{ ...card, textAlign: 'center', background: 'linear-gradient(135deg, rgba(52,199,89,0.12), rgba(167,139,250,0.08))' }}>
          <div style={{ fontSize: 28, marginBottom: 8 }}>🕊</div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#34c759', marginBottom: 12 }}>你的罪已得赦免</div>
          {verse && <div style={{ fontSize: 14, lineHeight: 1.9, color: 'rgba(255,255,255,0.9)', fontStyle: 'italic' }}>「{verse.text}」<div style={{ fontStyle: 'normal', color: '#a78bfa', marginTop: 6 }}>—— {verse.ref}</div></div>}
          <button onClick={() => { setStep(0); setVerse(null) }} style={{ ...btn('rgba(255,255,255,0.1)'), color: 'rgba(255,255,255,0.7)' }}>完成</button>
        </div>
      )}
    </>
  )
}

function Calendar() {
  const s = currentSeason()
  return (
    <div style={{ ...card, background: `linear-gradient(135deg, ${s.color}1f, rgba(255,255,255,0.03))`, borderColor: `${s.color}44` }}>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginBottom: 4 }}>当前节期</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.name}</div>
      <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.8)', lineHeight: 1.8, marginTop: 10 }}>{s.theme}</div>
      <div style={{ marginTop: 14, borderLeft: `3px solid ${s.color}88`, paddingLeft: 12, fontSize: 13, color: 'rgba(255,255,255,0.72)', fontStyle: 'italic' }}>
        「{s.scripture.text}」<span style={{ color: s.color, fontStyle: 'normal' }}> —— {s.scripture.ref}</span>
      </div>
    </div>
  )
}

function Accountability({ onNeedLogin }) {
  const [goals, setGoals] = useState([]); const [title, setTitle] = useState(''); const [cadence, setCadence] = useState('daily'); const [busy, setBusy] = useState(false); const [adding, setAdding] = useState(false)
  useEffect(() => { load() }, [])
  async function load() { const t = getToken(); if (!t) return; try { const r = await fetchGoals(t); setGoals(r.goals || []) } catch (e) {} }
  async function create() { const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return } if (!title.trim()) return; setBusy(true); try { await addGoal({ title: title.trim(), cadence }, t); setTitle(''); setAdding(false); load() } catch (e) {} finally { setBusy(false) } }
  async function check(id) { const t = getToken(); await checkinGoal({ goal_id: id, status: 'done' }, t); load() }
  async function del(id) { const t = getToken(); await deleteGoal(id, t); load() }
  return (
    <>
      <div style={{ ...card, background: 'linear-gradient(135deg, rgba(90,200,250,0.10), rgba(52,199,89,0.06))' }}>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: 'rgba(255,255,255,0.8)' }}>立一个属灵的小约——每天读经、为某人祷告、戒一个习惯。忠心不在大，在恒久。</div>
      </div>
      {goals.map(g => (
        <div key={g.id} style={card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
            <div style={{ flex: 1 }}><div style={{ fontSize: 14.5, fontWeight: 700 }}>{g.title}</div>
              <div style={{ fontSize: 11, color: '#5ac8fa', marginTop: 3 }}>🔥 连续 {g.streak} {g.cadence === 'weekly' ? '周' : '天'} · 共 {g.total_checkins} 次</div></div>
            <button onClick={() => del(g.id)} style={delBtn}>结束</button>
          </div>
          <button onClick={() => check(g.id)} style={{ ...btn('#5ac8fa'), marginTop: 12, padding: 11 }}>✓ 今天忠心完成了</button>
        </div>
      ))}
      {adding ? (
        <div style={card}>
          <input value={title} onChange={e => setTitle(e.target.value)} placeholder="我的属灵目标（如：每天为家人祷告）" style={inp} />
          <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
            {[['daily', '每天'], ['weekly', '每周']].map(([k, l]) => (
              <button key={k} onClick={() => setCadence(k)} style={{ flex: 1, padding: 9, borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700, background: cadence === k ? 'rgba(90,200,250,0.22)' : 'rgba(255,255,255,0.05)', color: cadence === k ? '#5ac8fa' : 'rgba(255,255,255,0.5)' }}>{l}</button>
            ))}
          </div>
          <button onClick={create} disabled={busy} style={btn('#5ac8fa')}>{busy ? '…' : '立约'}</button>
        </div>
      ) : <button onClick={() => setAdding(true)} style={{ ...btn('rgba(255,255,255,0.06)'), color: 'rgba(255,255,255,0.7)' }}>＋ 立一个新目标</button>}
    </>
  )
}

function ExportData({ onNeedLogin }) {
  const [busy, setBusy] = useState(false); const [msg, setMsg] = useState('')
  async function run() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return } setBusy(true); setMsg('')
    try {
      const data = await exportMyData(t)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob); const a = document.createElement('a')
      a.href = url; a.download = `属灵星球-我的数据-${(data.exported_at || '').slice(0, 10)}.json`
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
      const tot = Object.values(data.counts || {}).reduce((s, n) => s + n, 0)
      setMsg(`✓ 已导出 ${tot} 条记录`)
    } catch (e) { setMsg(e.message || '导出失败') } finally { setBusy(false) }
  }
  return (
    <div style={card}>
      <div style={{ fontSize: 13.5, lineHeight: 1.8, color: 'rgba(255,255,255,0.8)' }}>
        你的日记、祷告、省察、感恩、背经与读经进度等，都属于你。点击导出为一个 JSON 文件，随时带走、备份。
      </div>
      <button onClick={run} disabled={busy} style={btn('#94a3b8')}>{busy ? '导出中…' : '📦 导出我的全部数据'}</button>
      {msg && <div style={{ textAlign: 'center', marginTop: 12, fontSize: 13, color: msg.startsWith('✓') ? '#34c759' : '#ffd43b' }}>{msg}</div>}
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const inp = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, resize: 'vertical' }
const delBtn = { background: 'none', border: 'none', color: 'rgba(255,135,135,0.6)', fontSize: 12, cursor: 'pointer', flexShrink: 0 }
function btn(color) { return { width: '100%', marginTop: 12, padding: 13, borderRadius: 12, border: 'none', cursor: 'pointer', fontSize: 14.5, fontWeight: 700, background: color, color: '#fff' } }
