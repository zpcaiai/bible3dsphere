/**
 * MemoryVersePage — 背经（SM-2 间隔重复）
 * 灵修 tab 子页。复习 / 我的 / 添加。
 */
import { useEffect, useState } from 'react'
import { addMemoryVerse, fetchMemoryDue, fetchMemoryList, reviewMemoryVerse, deleteMemoryVerse } from './api'
import { getToken } from './auth'

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 16, marginBottom: 12 }
const GRADES = [
  { g: 0, label: '忘了', color: '#ff8787' },
  { g: 1, label: '吃力', color: '#ffa94d' },
  { g: 2, label: '记得', color: '#5ac8fa' },
  { g: 3, label: '轻松', color: '#34c759' },
]

export default function MemoryVersePage({ user }) {
  const [tab, setTab] = useState('review')   // review | list | add
  const [due, setDue] = useState([])
  const [list, setList] = useState([])
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [ref, setRef] = useState('')
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => { loadDue(); loadList() }, [])
  async function loadDue() { const t = getToken(); if (!t) return; try { const r = await fetchMemoryDue(t); setDue(r.cards || []); setIdx(0); setRevealed(false) } catch (e) {} }
  async function loadList() { const t = getToken(); if (!t) return; try { const r = await fetchMemoryList(t); setList(r.cards || []) } catch (e) {} }

  async function grade(g) {
    const t = getToken(); const cardObj = due[idx]; if (!t || !cardObj) return
    setBusy(true)
    try {
      await reviewMemoryVerse(cardObj.id, g, t)
      const rest = due.filter((_, i) => i !== idx)
      setDue(rest); setIdx(0); setRevealed(false)
      loadList()
    } catch (e) {} finally { setBusy(false) }
  }

  async function add() {
    const t = getToken(); if (!t) return
    if (!ref.trim() || !text.trim()) { setMsg('请填写经节与经文'); return }
    setBusy(true); setMsg('')
    try { await addMemoryVerse({ reference: ref.trim(), verse_text: text.trim() }, t); setRef(''); setText(''); setMsg('✓ 已加入背诵'); loadDue(); loadList() }
    catch (e) { setMsg(e.message || '添加失败') } finally { setBusy(false) }
  }

  async function del(id) {
    const t = getToken(); if (!t) return
    await deleteMemoryVerse(id, t); loadList(); loadDue()
  }

  const TABS = [['review', `复习 ${due.length ? `(${due.length})` : ''}`], ['list', '我的'], ['add', '＋ 添加']]

  return (
    <div style={{ padding: '14px 16px 90px', maxWidth: 640, margin: '0 auto', color: '#fff' }}>
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {TABS.map(([k, l]) => (
          <button key={k} onClick={() => setTab(k)} style={{ flex: 1, padding: '9px', borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700,
            background: tab === k ? 'rgba(139,92,246,0.22)' : 'rgba(255,255,255,0.05)', color: tab === k ? '#a78bfa' : 'rgba(255,255,255,0.5)' }}>{l}</button>
        ))}
      </div>

      {tab === 'review' && (
        due.length === 0 ? (
          <div style={{ ...card, textAlign: 'center', padding: '32px 16px' }}>
            <div style={{ fontSize: 26, marginBottom: 8 }}>🎉</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>今天的背诵都复习完了</div>
            <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.55)', lineHeight: 1.7 }}>愿这些话语住在你心里。明天会有新的卡片到期。</div>
          </div>
        ) : (
          <>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 8, textAlign: 'center' }}>还剩 {due.length} 张 · 先回想，再翻看</div>
            <div style={{ ...card, minHeight: 180, display: 'flex', flexDirection: 'column', justifyContent: 'center', textAlign: 'center', padding: '28px 18px' }}>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#a78bfa', marginBottom: 14 }}>{due[idx]?.reference}</div>
              {revealed
                ? <div style={{ fontSize: 15, lineHeight: 1.9, color: 'rgba(255,255,255,0.92)' }}>{due[idx]?.verse_text}</div>
                : <button onClick={() => setRevealed(true)} style={{ alignSelf: 'center', padding: '10px 22px', borderRadius: 20, border: '1px solid rgba(167,139,250,0.4)', background: 'rgba(167,139,250,0.12)', color: '#a78bfa', fontSize: 14, cursor: 'pointer' }}>先在心里背一遍，再点开</button>}
            </div>
            {revealed && (
              <div style={{ display: 'flex', gap: 8 }}>
                {GRADES.map(gr => (
                  <button key={gr.g} onClick={() => grade(gr.g)} disabled={busy} style={{ flex: 1, padding: '12px 4px', borderRadius: 12, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700, background: `${gr.color}24`, color: gr.color }}>{gr.label}</button>
                ))}
              </div>
            )}
          </>
        )
      )}

      {tab === 'list' && (
        list.length === 0
          ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>还没有背诵卡片，去「添加」开始吧</div>
          : list.map(c => (
            <div key={c.id} style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                <span style={{ fontSize: 13.5, fontWeight: 700, color: '#a78bfa' }}>{c.reference}</span>
                <button onClick={() => del(c.id)} style={{ background: 'none', border: 'none', color: 'rgba(255,135,135,0.6)', fontSize: 12, cursor: 'pointer', flexShrink: 0 }}>删除</button>
              </div>
              <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.72)', lineHeight: 1.7, marginTop: 6 }}>{c.verse_text}</div>
              <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.35)', marginTop: 6 }}>下次复习 {c.due_date} · 已复习 {c.repetitions} 次</div>
            </div>
          ))
      )}

      {tab === 'add' && (
        <div style={card}>
          <label style={{ display: 'block', fontSize: 12, color: 'rgba(255,255,255,0.6)', marginBottom: 6 }}>经节出处</label>
          <input value={ref} onChange={e => setRef(e.target.value)} placeholder="如：腓立比书 4:6-7" style={inp} />
          <label style={{ display: 'block', fontSize: 12, color: 'rgba(255,255,255,0.6)', margin: '14px 0 6px' }}>经文</label>
          <textarea value={text} onChange={e => setText(e.target.value)} rows={4} placeholder="把要背诵的经文抄在这里…" style={{ ...inp, resize: 'vertical' }} />
          <button onClick={add} disabled={busy} style={{ width: '100%', marginTop: 14, padding: 13, borderRadius: 12, border: 'none', background: 'linear-gradient(135deg, #8b5cf6, #5ac8fa)', color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>加入背诵</button>
          {msg && <div style={{ textAlign: 'center', marginTop: 12, fontSize: 13, color: msg.startsWith('✓') ? '#34c759' : '#ffd43b' }}>{msg}</div>}
        </div>
      )}
    </div>
  )
}

const inp = { width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13 }
