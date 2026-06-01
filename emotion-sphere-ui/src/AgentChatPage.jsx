/**
 * AgentChatPage — 双属灵 Agent 对话（司布真牧养 / 钟马田诊断）
 * 今日心镜 overlay。
 */
import { useEffect, useRef, useState } from 'react'
import { fetchAgentMeta, chatAgent } from './api'
import { getToken } from './auth'

export default function AgentChatPage({ onBack, onNeedLogin }) {
  const [agents, setAgents] = useState([])
  const [active, setActive] = useState('spurgeon')
  const [configured, setConfigured] = useState(true)
  const [msgs, setMsgs] = useState([])          // {role, content}
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    fetchAgentMeta(getToken()).then(r => { setAgents(r.agents || []); setConfigured(r.configured) }).catch(() => {})
  }, [])
  useEffect(() => {
    const a = agents.find(x => x.key === active)
    if (a) setMsgs([{ role: 'assistant', content: a.opening }])
  }, [active, agents])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs, busy])

  const agentMeta = agents.find(a => a.key === active) || { name: '', color: '#ffd43b', icon: '🕊', role: '' }

  async function send() {
    const t = getToken(); if (!t) { onNeedLogin && onNeedLogin(); return }
    const text = input.trim(); if (!text || busy) return
    const next = [...msgs, { role: 'user', content: text }]
    setMsgs(next); setInput(''); setBusy(true)
    try {
      const r = await chatAgent(active, next.filter(m => m.role !== 'system'), t)
      setMsgs([...next, { role: 'assistant', content: r.reply }])
      if (typeof r.configured === 'boolean') setConfigured(r.configured)
    } catch (e) {
      setMsgs([...next, { role: 'assistant', content: '（一时无法回应，请稍后再试。）' }])
    } finally { setBusy(false) }
  }

  return (
    <div style={{ width: '100%', height: '100%', background: '#000', color: '#fff', display: 'flex', flexDirection: 'column', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(28,28,30,0.92)', flexShrink: 0 }}>
        <button onClick={onBack} style={backBtn}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>属灵牧者</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{agentMeta.icon} {agentMeta.name} · {agentMeta.role}</div></div>
      </div>

      <div style={{ display: 'flex', gap: 8, padding: '10px 16px', flexShrink: 0 }}>
        {agents.map(a => (
          <button key={a.key} onClick={() => setActive(a.key)} style={{ flex: 1, padding: '9px', borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 700, background: active === a.key ? `${a.color}28` : 'rgba(255,255,255,0.05)', color: active === a.key ? a.color : 'rgba(255,255,255,0.5)' }}>{a.icon} {a.name}</button>
        ))}
      </div>

      {!configured && (
        <div style={{ margin: '0 16px 8px', padding: 12, borderRadius: 10, background: 'rgba(255,212,59,0.08)', border: '1px solid rgba(255,212,59,0.25)', fontSize: 12, color: '#ffd43b', lineHeight: 1.6 }}>
          AI 牧者暂未配置（需服务器设置 LLM 密钥）。福音诊断室 / 属灵低潮体检等结构化功能无需联网即可使用。
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '6px 16px 16px' }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start', marginBottom: 10 }}>
            <div style={{ maxWidth: '82%', padding: '10px 13px', borderRadius: 14, fontSize: 13.5, lineHeight: 1.7,
              background: m.role === 'user' ? 'rgba(90,200,250,0.18)' : `${agentMeta.color}1c`,
              border: `1px solid ${m.role === 'user' ? 'rgba(90,200,250,0.25)' : agentMeta.color + '33'}`,
              color: 'rgba(255,255,255,0.9)', whiteSpace: 'pre-wrap' }}>{m.content}</div>
          </div>
        ))}
        {busy && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', paddingLeft: 4 }}>{agentMeta.name}正在回应…</div>}
        <div ref={endRef} />
      </div>

      <div style={{ display: 'flex', gap: 8, padding: '10px 16px', borderTop: '1px solid rgba(255,255,255,0.1)', background: 'rgba(28,28,30,0.92)', flexShrink: 0 }}>
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder={`对${agentMeta.name}说…`}
          style={{ flex: 1, padding: '11px 14px', borderRadius: 22, background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.12)', color: '#fff', fontSize: 14 }} />
        <button onClick={send} disabled={busy} style={{ width: 64, borderRadius: 22, border: 'none', background: `linear-gradient(135deg, ${agentMeta.color}, #5ac8fa)`, color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>发送</button>
      </div>
    </div>
  )
}

const backBtn = { background: 'rgba(120,120,128,0.2)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }
