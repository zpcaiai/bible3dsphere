/**
 * ExamenPage — 每日省察 Examen（依纳爵式）
 *
 * 回顾今天的「安慰 / 枯涩」，感恩一件、求恕一件、明日一个微顺服。
 * 不定罪、温柔陪伴。入口：今日心镜 (SoulDashboard) 卡片。
 */
import { useEffect, useState } from 'react'
import { fetchExamenToday, saveExamen, fetchExamenHistory } from './api'
import { getToken } from './auth'

const FIELDS = [
  { key: 'consolation',   icon: '🌤', title: '安慰 · 神的同在',
    prompt: '今天哪一刻，我感到被爱、被陪伴，或心里有平安？', ph: '一个画面、一句话、一件小事…' },
  { key: 'desolation',    icon: '🌫', title: '枯涩 · 远离',
    prompt: '今天哪一刻，我感到焦虑、远离神，或失了平安？', ph: '诚实地写下，无需修饰…' },
  { key: 'gratitude',     icon: '🙏', title: '感恩一件',
    prompt: '今天我要为哪一件事，向神说谢谢？', ph: '哪怕很小…' },
  { key: 'confession',    icon: '🕊', title: '求恕 · 交托',
    prompt: '有什么我想求神赦免、或交在祂手中？', ph: '不是为了定罪，是为了被释放…' },
  { key: 'tomorrow_step', icon: '🌱', title: '明日一个微顺服',
    prompt: '明天我可以忠心去做的一件小事是什么？', ph: '一个具体、微小、可完成的行动…' },
]

const card = { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 14, padding: 14, marginBottom: 12 }

export default function ExamenPage({ user, onBack, onNeedLogin }) {
  const [vals, setVals] = useState({ consolation: '', desolation: '', gratitude: '', confession: '', tomorrow_step: '', consolation_level: 5 })
  const [view, setView] = useState('today')   // today | history
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const t = getToken(); if (!t) { setLoading(false); return }
    fetchExamenToday(t)
      .then(r => { if (r.entry) setVals(v => ({ ...v, ...r.entry })) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  function set(k, val) { setVals(v => ({ ...v, [k]: val })); setSaved(false) }

  async function save() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    setSaving(true); setError('')
    try {
      await saveExamen({
        consolation: vals.consolation, desolation: vals.desolation,
        gratitude: vals.gratitude, confession: vals.confession,
        tomorrow_step: vals.tomorrow_step, consolation_level: vals.consolation_level,
      }, t)
      setSaved(true)
    } catch (e) { setError(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  async function openHistory() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    try { const r = await fetchExamenHistory(t, 30); setHistory(r.entries || []); setView('history') }
    catch (e) { setError(e.message || '加载失败') }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'rgba(28,28,30,0.92)', position: 'sticky', top: 0, zIndex: 100, backdropFilter: 'blur(10px)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={backBtn}>‹</button>
          <div>
            <div style={{ fontSize: 17, fontWeight: 600 }}>今日省察</div>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>依纳爵式 Examen · 与神同回顾这一天</div>
          </div>
        </div>
        <button onClick={view === 'history' ? () => setView('today') : openHistory} style={pill}>
          {view === 'history' ? '← 返回' : '历史'}
        </button>
      </div>

      <div style={{ padding: '14px 16px 100px', maxWidth: 680, margin: '0 auto' }}>
        {error && <div style={{ ...card, borderColor: 'rgba(255,135,135,0.4)', color: '#ff8787', fontSize: 13 }}>{error}</div>}

        {view === 'today' && (
          <>
            <div style={{ ...card, background: 'linear-gradient(135deg, rgba(139,92,246,0.12), rgba(90,200,250,0.08))' }}>
              <div style={{ fontSize: 13, lineHeight: 1.75, color: 'rgba(255,255,255,0.8)' }}>
                安静一分钟。让这一天在神面前重演一遍——不为打分，只为看见祂在哪里，
                也把心交还给祂。
              </div>
            </div>

            {/* 亲近感 */}
            <div style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                <span style={{ color: 'rgba(255,255,255,0.8)' }}>今天，我感到与神有多亲近？</span>
                <span style={{ color: '#a78bfa', fontWeight: 700 }}>{vals.consolation_level}</span>
              </div>
              <input type="range" min="0" max="10" step="1" value={vals.consolation_level}
                onChange={e => set('consolation_level', parseInt(e.target.value))}
                style={{ width: '100%', accentColor: '#a78bfa', marginTop: 8 }} />
            </div>

            {FIELDS.map(f => (
              <div key={f.key} style={card}>
                <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 4 }}>{f.icon} {f.title}</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', marginBottom: 8, lineHeight: 1.6 }}>{f.prompt}</div>
                <textarea value={vals[f.key]} onChange={e => set(f.key, e.target.value)} rows={2} placeholder={f.ph}
                  style={{ width: '100%', boxSizing: 'border-box', padding: '10px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: '#fff', fontSize: 13, resize: 'vertical' }} />
              </div>
            ))}

            <button onClick={save} disabled={saving || loading} style={{ width: '100%', padding: 14, borderRadius: 12, border: 'none', background: saved ? 'rgba(52,199,89,0.25)' : 'linear-gradient(135deg, #8b5cf6, #5ac8fa)', color: saved ? '#34c759' : '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer' }}>
              {saving ? '保存中…' : saved ? '✓ 已保存今日省察' : '保存今日省察'}
            </button>
            <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.25)', textAlign: 'center', marginTop: 14, lineHeight: 1.6 }}>
              每天一条；今天的省察会自动覆盖更新。这是温柔的回顾，不是考核。
            </div>
          </>
        )}

        {view === 'history' && (
          history.length === 0
            ? <div style={{ ...card, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>还没有省察记录</div>
            : history.map(e => (
              <div key={e.id} style={card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600 }}>{e.entry_date}</span>
                  <span style={{ fontSize: 11, color: '#a78bfa' }}>亲近感 {Math.round(e.consolation_level)}</span>
                </div>
                {e.gratitude && <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.74)', lineHeight: 1.6 }}>🙏 {e.gratitude}</div>}
                {e.tomorrow_step && <div style={{ fontSize: 12, color: '#5ac8fa', marginTop: 4 }}>🌱 {e.tomorrow_step}</div>}
              </div>
            ))
        )}
      </div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
const pill = { background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 14, padding: '6px 12px', color: 'rgba(255,255,255,0.7)', fontSize: 12, cursor: 'pointer' }
