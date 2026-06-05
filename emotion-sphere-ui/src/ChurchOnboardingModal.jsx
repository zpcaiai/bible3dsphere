// ChurchOnboardingModal.jsx — 登录后无教会时的引导弹窗
import { useState } from 'react'
import { createChurch, joinChurch } from './api'

const ACCENT = '#007aff'
const toast = (m, t = 'info') => window.showToast?.(m, t)

export default function ChurchOnboardingModal({ token, onJoined, onSkip }) {
  const [tab, setTab] = useState('join') // 'join' | 'create'

  // Join tab state
  const [code, setCode] = useState('')
  const [joining, setJoining] = useState(false)
  const [joinErr, setJoinErr] = useState('')

  // Create tab state
  const [name, setName] = useState('')
  const [creating, setCreating] = useState(false)
  const [createErr, setCreateErr] = useState('')
  const [createdChurch, setCreatedChurch] = useState(null)
  const [copied, setCopied] = useState(false)

  async function doJoin() {
    const c = code.trim().toUpperCase()
    if (!c) { setJoinErr('请输入邀请码'); return }
    setJoining(true); setJoinErr('')
    try {
      const data = await joinChurch(c, token)
      toast('已成功加入教会！', 'success')
      onJoined?.(data.church || null)
    } catch (e) {
      setJoinErr(e.message || '邀请码无效，请重试')
    } finally {
      setJoining(false)
    }
  }

  async function doCreate() {
    const n = name.trim()
    if (!n) { setCreateErr('请输入教会名称'); return }
    setCreating(true); setCreateErr('')
    try {
      const data = await createChurch(n, token)
      setCreatedChurch(data.church || data)
      toast('教会创建成功！', 'success')
    } catch (e) {
      setCreateErr(e.message || '创建失败，请重试')
    } finally {
      setCreating(false)
    }
  }

  function copyCode() {
    const c = createdChurch?.join_code || ''
    if (!c) return
    navigator.clipboard?.writeText(c)
      .then(() => { setCopied(true); setTimeout(() => setCopied(false), 2000) })
      .catch(() => toast('复制失败', 'error'))
  }

  function handleDone() {
    onJoined?.(createdChurch)
  }

  return (
    <div style={S.overlay} onClick={onSkip}>
      <div style={S.card} onClick={e => e.stopPropagation()}>
        <div style={S.title}>⛪ 加入或创建教会</div>
        <div style={S.hint}>社区发帖、代祷等功能需要隶属一个教会。你可以输入邀请码加入现有教会，或创建一个新的。</div>

        {/* Tabs */}
        <div style={S.tabs}>
          <button style={{ ...S.tabBtn, ...(tab === 'join' ? S.tabActive : {}) }} onClick={() => setTab('join')}>
            输入邀请码加入
          </button>
          <button style={{ ...S.tabBtn, ...(tab === 'create' ? S.tabActive : {}) }} onClick={() => setTab('create')}>
            创建教会
          </button>
        </div>

        {/* Join Tab */}
        {tab === 'join' && (
          <div style={S.panel}>
            <input
              style={{ ...S.input, letterSpacing: 3, textTransform: 'uppercase' }}
              value={code}
              maxLength={12}
              placeholder="输入邀请码（如 ABC123）"
              onChange={e => setCode(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doJoin()}
              autoFocus
            />
            {joinErr && <div style={S.err}>{joinErr}</div>}
            <button style={S.primaryBtn} disabled={joining || !code.trim()} onClick={doJoin}>
              {joining ? '加入中…' : '加入教会'}
            </button>
          </div>
        )}

        {/* Create Tab */}
        {tab === 'create' && (
          <div style={S.panel}>
            {!createdChurch ? (
              <>
                <input
                  style={S.input}
                  value={name}
                  maxLength={50}
                  placeholder="教会名称，如「恩典河滨教会」"
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && doCreate()}
                  autoFocus
                />
                {createErr && <div style={S.err}>{createErr}</div>}
                <button style={S.primaryBtn} disabled={creating || !name.trim()} onClick={doCreate}>
                  {creating ? '创建中…' : '创建教会'}
                </button>
              </>
            ) : (
              <div style={S.successBox}>
                <div style={S.successIcon}>🎉</div>
                <div style={S.successTitle}>「{createdChurch.name}」已创建！</div>
                <div style={S.codeLabel}>教会邀请码</div>
                <div style={S.codeRow}>
                  <span style={S.codeText}>{createdChurch.join_code}</span>
                  <button style={S.copyBtn} onClick={copyCode}>
                    {copied ? '已复制 ✓' : '复制'}
                  </button>
                </div>
                <div style={S.codeHint}>将邀请码发给弟兄姐妹，他们即可加入你的教会。</div>
                <button style={S.primaryBtn} onClick={handleDone}>完成</button>
              </div>
            )}
          </div>
        )}

        {/* Skip */}
        <button style={S.skipBtn} onClick={onSkip}>暂时跳过</button>
      </div>
    </div>
  )
}

const S = {
  overlay: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.72)',
    backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center',
    justifyContent: 'center', zIndex: 200, padding: 20, boxSizing: 'border-box',
  },
  card: {
    width: '100%', maxWidth: 380,
    background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
    border: '1px solid rgba(255,255,255,0.14)',
    borderRadius: 18, padding: '24px 20px', boxSizing: 'border-box',
    color: '#fff', fontFamily: 'inherit',
  },
  title: { fontSize: 18, fontWeight: 700, textAlign: 'center', marginBottom: 10 },
  hint: { fontSize: 13, color: 'rgba(255,255,255,0.6)', lineHeight: 1.6, marginBottom: 18, textAlign: 'center' },
  tabs: { display: 'flex', gap: 8, marginBottom: 18 },
  tabBtn: {
    flex: 1, padding: '9px 0', background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10,
    color: 'rgba(255,255,255,0.6)', fontSize: 13, cursor: 'pointer', fontFamily: 'inherit',
  },
  tabActive: {
    background: 'rgba(0,122,255,0.18)', border: `1px solid ${ACCENT}`,
    color: '#fff', fontWeight: 600,
  },
  panel: { display: 'flex', flexDirection: 'column', gap: 12 },
  input: {
    width: '100%', boxSizing: 'border-box',
    background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.16)',
    borderRadius: 10, padding: '12px 14px', color: '#fff', fontSize: 15,
    fontFamily: 'inherit', outline: 'none',
  },
  primaryBtn: {
    background: ACCENT, border: 'none', borderRadius: 10, padding: '12px',
    color: '#fff', fontWeight: 700, fontSize: 15, cursor: 'pointer',
    fontFamily: 'inherit', opacity: 1, transition: 'opacity 0.15s',
  },
  err: { fontSize: 13, color: '#ff6b6b', textAlign: 'center' },
  successBox: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 },
  successIcon: { fontSize: 36 },
  successTitle: { fontSize: 15, fontWeight: 700, textAlign: 'center' },
  codeLabel: { fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 4 },
  codeRow: { display: 'flex', alignItems: 'center', gap: 10 },
  codeText: { fontSize: 22, fontWeight: 800, letterSpacing: 4, color: ACCENT },
  copyBtn: {
    background: 'rgba(0,122,255,0.15)', border: `1px solid ${ACCENT}`,
    borderRadius: 8, padding: '5px 12px', color: ACCENT, fontSize: 13,
    cursor: 'pointer', fontFamily: 'inherit',
  },
  codeHint: { fontSize: 12, color: 'rgba(255,255,255,0.45)', textAlign: 'center', lineHeight: 1.5 },
  skipBtn: {
    width: '100%', marginTop: 16, padding: '10px',
    background: 'none', border: 'none',
    color: 'rgba(255,255,255,0.35)', fontSize: 13, cursor: 'pointer',
    fontFamily: 'inherit', textDecoration: 'underline',
  },
}
