/**
 * HabitsPage — 灵修操练
 *
 * 简化重设计：
 *  - 8 个预设灵修习惯模板（可一键添加）
 *  - 每天打卡：已完成 / 未完成 + 简短反思笔记
 *  - 保留连续打卡 streak
 *  - 移除 Token / Red-Yellow-Green 电路层级 / 能量等级
 */

import { useState, useEffect } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'

// ── 8 个预设灵修习惯 ──────────────────────────────────────────────────────────
const PRESET_HABITS = [
  { key: 'bible',    icon: '📖', name: '读经',     desc: '每天读圣经，用SOAP法默想一段经文',             color: '#fbbf24' },
  { key: 'prayer',   icon: '🙏', name: '晨祷',     desc: '每天早起10分钟献上首先之时给神',              color: '#a78bfa' },
  { key: 'journal',  icon: '📝', name: '灵修日记', desc: '记录今天神对你说的话及内心的回应',            color: '#60a5fa' },
  { key: 'care',     icon: '💌', name: '关心他人', desc: '每天主动关心一位朋友、家人或需要帮助的人',    color: '#f472b6' },
  { key: 'tithe',    icon: '💰', name: '什一奉献', desc: '按期献上收入的十分之一，操练对神的信靠',      color: '#34c759' },
  { key: 'silence',  icon: '🤫', name: '静默等候', desc: '每天花5分钟安静等候神，不带议程',            color: '#2dd4bf' },
  { key: 'intercede',icon: '✝️', name: '代祷',     desc: '每天为他人祈祷——家人、朋友、未信者',        color: '#fb923c' },
  { key: 'sabbath',  icon: '🌅', name: '安息日',   desc: '每周一天完全休息、敬拜、与家人同在',         color: '#818cf8' },
]

// ── API helpers ───────────────────────────────────────────────────────────────
async function apiGet(path, token) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (!res.ok) throw new Error(res.statusText)
  return res.json()
}
async function apiPost(path, body, token) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body)
  })
  if (!res.ok) throw new Error(res.statusText)
  return res.json()
}

// ── Main component ────────────────────────────────────────────────────────────
export default function HabitsPage({ user, token: propToken, embedded = false, onNeedLogin }) {
  const [habits, setHabits]         = useState([])
  const [todayLogs, setTodayLogs]   = useState({})       // habitId → { done, note }
  const [streak, setStreak]         = useState(0)
  const [todayCount, setTodayCount] = useState(0)
  const [loading, setLoading]       = useState(true)
  const [activeView, setActiveView] = useState('today')  // 'today' | 'add'
  const [notes, setNotes]           = useState({})       // habitId → draft note
  const [saving, setSaving]         = useState({})       // habitId → bool
  const [addingPreset, setAddingPreset] = useState(null)
  const [customName, setCustomName]     = useState('')

  const token = propToken || getToken()
  const uid   = user?.id || user?.userId

  useEffect(() => {
    if (!uid) { setLoading(false); return }
    loadAll()
  }, [uid])

  async function loadAll() {
    try {
      setLoading(true)
      const [habitsRes, dashRes] = await Promise.all([
        apiGet('/habits', token).catch(() => ({ items: [] })),
        apiGet('/habits/dashboard', token).catch(() => null),
      ])
      const items = habitsRes.items || habitsRes || []
      setHabits(items)
      setStreak(dashRes?.current_streak || 0)
      setTodayCount(dashRes?.today_executions || 0)

      // Load today's logs for each habit
      const today = new Date().toISOString().split('T')[0]
      const logsRes = await apiGet(`/habits/logs?date=${today}`, token).catch(() => null)
      const logsMap = {}
      if (logsRes?.items) {
        logsRes.items.forEach(l => { logsMap[l.habit_id] = { done: l.was_completed, note: l.notes || '' } })
      }
      setTodayLogs(logsMap)
    } catch (err) {
      console.error('[HabitsPage] load error:', err)
    } finally {
      setLoading(false)
    }
  }

  async function toggleDone(habit) {
    if (!user) { onNeedLogin?.('登录后才能记录操练'); return }
    const current = todayLogs[habit.id]
    const newDone = !current?.done
    setSaving(s => ({ ...s, [habit.id]: true }))
    try {
      await apiPost('/habits/log', {
        habit_id: habit.id,
        was_completed: newDone,
        notes: notes[habit.id] || current?.note || '',
        tier_executed: 'Green',
        completion_percentage: newDone ? 100 : 0,
        mood_before: 5, mood_after: 5,
      }, token)
      setTodayLogs(prev => ({ ...prev, [habit.id]: { done: newDone, note: notes[habit.id] || current?.note || '' } }))
      if (newDone) setTodayCount(c => c + 1)
      else setTodayCount(c => Math.max(0, c - 1))
    } catch (err) {
      console.error('[HabitsPage] toggle error:', err)
    } finally {
      setSaving(s => ({ ...s, [habit.id]: false }))
    }
  }

  async function saveNote(habit) {
    if (!user) return
    const note = notes[habit.id] || ''
    setSaving(s => ({ ...s, [habit.id]: true }))
    try {
      await apiPost('/habits/log', {
        habit_id: habit.id,
        was_completed: todayLogs[habit.id]?.done || false,
        notes: note,
        tier_executed: 'Green',
        completion_percentage: todayLogs[habit.id]?.done ? 100 : 0,
        mood_before: 5, mood_after: 5,
      }, token)
      setTodayLogs(prev => ({ ...prev, [habit.id]: { ...prev[habit.id], note } }))
    } catch (err) {
      console.error('[HabitsPage] saveNote error:', err)
    } finally {
      setSaving(s => ({ ...s, [habit.id]: false }))
    }
  }

  async function addPreset(preset) {
    if (!user) { onNeedLogin?.('登录后才能添加操练习惯'); return }
    const alreadyAdded = habits.some(h => h.name === preset.name || h.preset_key === preset.key)
    if (alreadyAdded) return
    setAddingPreset(preset.key)
    try {
      const created = await apiPost('/habits', {
        name: preset.name,
        description: preset.desc,
        preset_key: preset.key,
        anchor: '',
        energy_required: 3,
      }, token)
      setHabits(prev => [...prev, created])
      setActiveView('today')
    } catch (err) {
      console.error('[HabitsPage] addPreset error:', err)
    } finally {
      setAddingPreset(null)
    }
  }

  async function addCustom() {
    if (!user) { onNeedLogin?.('登录后才能添加操练习惯'); return }
    if (!customName.trim()) return
    setAddingPreset('custom')
    try {
      const created = await apiPost('/habits', {
        name: customName.trim(),
        description: '',
        anchor: '',
        energy_required: 3,
      }, token)
      setHabits(prev => [...prev, created])
      setCustomName('')
      setActiveView('today')
    } catch (err) {
      console.error('[HabitsPage] addCustom error:', err)
    } finally {
      setAddingPreset(null)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
        <div style={{ fontSize: 32, marginBottom: 12 }}>🌱</div>
        <div>加载灵修操练…</div>
      </div>
    )
  }

  const todayDate = new Date().toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' })
  const doneCount = habits.filter(h => todayLogs[h.id]?.done).length

  return (
    <div style={{ paddingBottom: 20 }}>

      {/* ── 头部 ── */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(52,199,89,0.1) 0%, rgba(167,139,250,0.08) 100%)',
        borderRadius: '0 0 20px 20px',
        padding: '18px 16px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: '#fff' }}>灵修操练</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{todayDate}</div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            {streak > 0 && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: streak >= 7 ? '#ffd700' : '#34c759' }}>🔥 {streak}</div>
                <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>连续天数</div>
              </div>
            )}
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#60a5fa' }}>{doneCount}/{habits.length}</div>
              <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.35)' }}>今日完成</div>
            </div>
          </div>
        </div>

        {/* 进度条 */}
        {habits.length > 0 && (
          <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: `${habits.length > 0 ? (doneCount / habits.length) * 100 : 0}%`,
              background: 'linear-gradient(90deg, #34c759, #4ade80)',
              borderRadius: 3,
              transition: 'width 0.4s',
            }} />
          </div>
        )}

        {/* 视图切换 */}
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          {[
            { key: 'today', label: '今日操练', icon: '✅' },
            { key: 'add',   label: '添加习惯', icon: '＋' },
          ].map(v => (
            <button key={v.key} onClick={() => setActiveView(v.key)} style={{
              padding: '6px 14px',
              borderRadius: 20,
              border: 'none',
              background: activeView === v.key ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.07)',
              color: activeView === v.key ? '#34c759' : 'rgba(255,255,255,0.55)',
              fontSize: 12,
              fontWeight: activeView === v.key ? 700 : 400,
              cursor: 'pointer',
            }}>{v.icon} {v.label}</button>
          ))}
        </div>
      </div>

      {/* ── 今日操练清单 ── */}
      {activeView === 'today' && (
        <div style={{ padding: '0 16px' }}>
          {habits.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'rgba(255,255,255,0.3)' }}>
              <div style={{ fontSize: 36, marginBottom: 12 }}>🌱</div>
              <div style={{ fontSize: 14, marginBottom: 16 }}>还没有灵修操练习惯</div>
              <button onClick={() => setActiveView('add')} style={{
                padding: '10px 20px', borderRadius: 10, border: 'none',
                background: 'rgba(52,199,89,0.2)', color: '#34c759',
                fontSize: 13, fontWeight: 600, cursor: 'pointer',
              }}>＋ 从预设习惯开始</button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {habits.map(habit => {
                const log = todayLogs[habit.id]
                const done = log?.done || false
                const note = notes[habit.id] ?? (log?.note || '')
                const preset = PRESET_HABITS.find(p => p.key === habit.preset_key || p.name === habit.name)
                const color = preset?.color || '#60a5fa'
                const icon  = preset?.icon || '🌿'
                const isSaving = saving[habit.id]

                return (
                  <div key={habit.id} style={{
                    background: done ? 'rgba(52,199,89,0.07)' : 'rgba(255,255,255,0.04)',
                    borderRadius: 14,
                    padding: '14px 16px',
                    border: `1px solid ${done ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.08)'}`,
                    transition: 'all 0.2s',
                  }}>
                    {/* 习惯行 */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: note !== undefined ? 10 : 0 }}>
                      {/* 完成按钮 */}
                      <button onClick={() => toggleDone(habit)} disabled={isSaving} style={{
                        flexShrink: 0,
                        width: 32, height: 32,
                        borderRadius: '50%',
                        border: `2px solid ${done ? color : 'rgba(255,255,255,0.2)'}`,
                        background: done ? color : 'transparent',
                        color: done ? '#000' : 'rgba(255,255,255,0.4)',
                        fontSize: 16,
                        cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.2s',
                      }}>
                        {isSaving ? '…' : done ? '✓' : ''}
                      </button>

                      <span style={{ fontSize: 18, flexShrink: 0 }}>{icon}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 600, color: done ? color : '#fff', textDecoration: done ? 'line-through' : 'none', textDecorationColor: 'rgba(255,255,255,0.3)' }}>
                          {habit.name}
                        </div>
                        {habit.description && (
                          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginTop: 2, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {habit.description}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* 反思笔记 */}
                    <div style={{ paddingLeft: 44 }}>
                      <textarea
                        value={note}
                        onChange={e => setNotes(prev => ({ ...prev, [habit.id]: e.target.value }))}
                        onBlur={() => note !== (log?.note || '') && saveNote(habit)}
                        placeholder="今日反思（可选）…"
                        rows={note ? 2 : 1}
                        style={{
                          width: '100%',
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid rgba(255,255,255,0.08)',
                          borderRadius: 8,
                          padding: '6px 10px',
                          color: 'rgba(255,255,255,0.7)',
                          fontSize: 12,
                          lineHeight: 1.5,
                          resize: 'none',
                          outline: 'none',
                          fontFamily: 'inherit',
                          boxSizing: 'border-box',
                        }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* ── 添加习惯 ── */}
      {activeView === 'add' && (
        <div style={{ padding: '0 16px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 12 }}>
            灵修习惯模板
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 20 }}>
            {PRESET_HABITS.map(preset => {
              const alreadyAdded = habits.some(h => h.preset_key === preset.key || h.name === preset.name)
              const isAdding = addingPreset === preset.key
              return (
                <button key={preset.key} onClick={() => !alreadyAdded && addPreset(preset)} disabled={alreadyAdded || isAdding} style={{
                  background: alreadyAdded ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.05)',
                  border: `1px solid ${alreadyAdded ? 'rgba(255,255,255,0.08)' : preset.color + '40'}`,
                  borderRadius: 14,
                  padding: '14px 12px',
                  textAlign: 'left',
                  cursor: alreadyAdded ? 'default' : 'pointer',
                  opacity: alreadyAdded ? 0.5 : 1,
                  transition: 'all 0.15s',
                }}>
                  <div style={{ fontSize: 22, marginBottom: 6 }}>{isAdding ? '⏳' : preset.icon}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: alreadyAdded ? 'rgba(255,255,255,0.35)' : preset.color, marginBottom: 4 }}>
                    {preset.name} {alreadyAdded && '✓'}
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', lineHeight: 1.4 }}>{preset.desc}</div>
                </button>
              )
            })}
          </div>

          {/* 自定义习惯 */}
          <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: 14, padding: '14px 16px', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.6)', marginBottom: 10 }}>自定义操练</div>
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                value={customName}
                onChange={e => setCustomName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCustom()}
                placeholder="输入习惯名称…"
                style={{
                  flex: 1,
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.12)',
                  borderRadius: 8,
                  padding: '8px 12px',
                  color: '#fff',
                  fontSize: 13,
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              <button onClick={addCustom} disabled={!customName.trim() || addingPreset === 'custom'} style={{
                padding: '8px 16px',
                borderRadius: 8,
                border: 'none',
                background: customName.trim() ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.07)',
                color: customName.trim() ? '#34c759' : 'rgba(255,255,255,0.3)',
                fontSize: 13,
                fontWeight: 600,
                cursor: customName.trim() ? 'pointer' : 'default',
              }}>
                {addingPreset === 'custom' ? '…' : '添加'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
