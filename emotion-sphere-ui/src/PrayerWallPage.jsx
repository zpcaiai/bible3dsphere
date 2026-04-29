import { useEffect, useRef, useState } from 'react'
import { amenPrayer, fetchPrayers, submitPrayer } from './api'

const AMEN_KEY = 'pw-amened-v1'

function loadAmened() {
  try { return new Set(JSON.parse(localStorage.getItem(AMEN_KEY) || '[]')) }
  catch { return new Set() }
}
function saveAmened(set) {
  localStorage.setItem(AMEN_KEY, JSON.stringify([...set]))
}

function timeAgo(ts) {
  const diff = Math.floor(Date.now() / 1000 - ts)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)} 天前`
  const d = new Date(ts * 1000)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function Avatar({ nickname }) {
  const char = nickname?.[0] || '🙏'
  const colors = ['#007aff','#5e5ce6','#34c759','#ff9f0a','#ff6b6b','#32ade6','#af52de']
  const idx = (nickname?.charCodeAt(0) || 0) % colors.length
  return (
    <div style={{
      width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
      background: `linear-gradient(135deg, ${colors[idx]}, ${colors[(idx+2)%colors.length]})`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 15, fontWeight: 700, color: '#fff',
    }}>
      {char}
    </div>
  )
}

export default function PrayerWallPage({ user, token, onBack }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState('')
  const [amened, setAmened] = useState(loadAmened)
  const [showCompose, setShowCompose] = useState(false)
  const [draft, setDraft] = useState('')
  const [isAnon, setIsAnon] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitDone, setSubmitDone] = useState(false)
  const textareaRef = useRef(null)
  const PAGE = 40

  async function load(replace = true) {
    try {
      replace ? setLoading(true) : setLoadingMore(true)
      const data = await fetchPrayers(PAGE, replace ? 0 : items.length)
      setTotal(data.total || 0)
      setItems(prev => replace ? data.items : [...prev, ...data.items])
      setError('')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (showCompose) setTimeout(() => textareaRef.current?.focus(), 100)
  }, [showCompose])

  async function handleAmen(id) {
    if (amened.has(id)) return
    const next = new Set(amened)
    next.add(id)
    setAmened(next)
    saveAmened(next)
    setItems(prev => prev.map(p => p.id === id ? { ...p, amen_count: p.amen_count + 1 } : p))
    try { await amenPrayer(id, token) } catch { /* optimistic */ }
  }

  async function handleSubmit() {
    if (!draft.trim() || submitting) return
    setSubmitting(true)
    try {
      await submitPrayer(draft.trim(), isAnon, token)
      setDraft('')
      setSubmitDone(true)
      setShowCompose(false)
      await load(true)
      setTimeout(() => setSubmitDone(false), 3000)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="pw-page">
      {/* Header */}
      <header className="pw-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="pw-header-center">
          <div className="pw-title">🙏 代祷墙</div>
          <div className="pw-subtitle">{total > 0 ? `共 ${total} 条祷告` : '众人的祷告'}</div>
        </div>
        <button
          className="pw-compose-btn"
          onClick={() => setShowCompose(true)}
          title="提交祷告"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
        </button>
      </header>

      {/* Success toast */}
      {submitDone && (
        <div className="pw-toast">✅ 祷告已提交，愿神垂听</div>
      )}

      {/* Compose sheet */}
      {showCompose && (
        <div className="pw-compose-overlay" onClick={e => e.target === e.currentTarget && setShowCompose(false)}>
          <div className="pw-compose-sheet glass">
            <div className="pw-compose-title">📝 提交代祷</div>
            <textarea
              ref={textareaRef}
              className="pw-compose-textarea"
              placeholder="写下你想让弟兄姊妹为你代祷的内容…（最多 500 字）"
              value={draft}
              onChange={e => setDraft(e.target.value.slice(0, 500))}
              rows={5}
            />
            <div className="pw-compose-count">{draft.length} / 500</div>
            <label className="pw-anon-row">
              <input
                type="checkbox"
                checked={isAnon}
                onChange={e => setIsAnon(e.target.checked)}
                style={{ marginRight: 8 }}
              />
              <span>匿名提交</span>
            </label>
            <div className="pw-compose-actions">
              <button className="pw-cancel-btn" onClick={() => setShowCompose(false)}>取消</button>
              <button
                className="primary-btn"
                style={{ flex: 1, minHeight: 42 }}
                disabled={!draft.trim() || submitting}
                onClick={handleSubmit}
              >
                {submitting ? '提交中…' : '🙏 提交代祷'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      <div className="pw-list">
        {loading ? (
          <div className="pw-loading">
            <div className="pw-loading-dots"><span /><span /><span /></div>
            <div style={{ color: 'rgba(255,255,255,0.35)', fontSize: 13, marginTop: 12 }}>加载中…</div>
          </div>
        ) : error ? (
          <div className="pw-error">
            <div style={{ fontSize: 32 }}>⚠️</div>
            <div>{error}</div>
            <button className="pw-retry-btn" onClick={() => load()}>重试</button>
          </div>
        ) : items.length === 0 ? (
          <div className="pw-empty">
            <div className="pw-empty-icon">🕊️</div>
            <div className="pw-empty-title">还没有代祷</div>
            <div className="pw-empty-sub">成为第一个分享代祷事项的人</div>
            <button
              className="primary-btn"
              style={{ maxWidth: 200, marginTop: 20 }}
              onClick={() => setShowCompose(true)}
            >
              提交代祷
            </button>
          </div>
        ) : (
          <>
            {items.map(prayer => (
              <div key={prayer.id} className="pw-card glass">
                <div className="pw-card-top">
                  <Avatar nickname={prayer.nickname} />
                  <div className="pw-card-meta">
                    <span className="pw-card-name">{prayer.nickname}</span>
                    <span className="pw-card-time">{timeAgo(prayer.created_at)}</span>
                  </div>
                </div>
                <div className="pw-card-content">{prayer.content}</div>
                <div className="pw-card-footer">
                  <button
                    className={`pw-amen-btn ${amened.has(prayer.id) ? 'amened' : ''}`}
                    onClick={() => handleAmen(prayer.id)}
                    disabled={amened.has(prayer.id)}
                  >
                    <span className="pw-amen-icon">🙏</span>
                    <span className="pw-amen-label">
                      {amened.has(prayer.id) ? '已同心' : '同心'}
                    </span>
                    {prayer.amen_count > 0 && (
                      <span className="pw-amen-count">{prayer.amen_count}</span>
                    )}
                  </button>
                </div>
              </div>
            ))}

            {items.length < total && (
              <button
                className="pw-load-more"
                onClick={() => load(false)}
                disabled={loadingMore}
              >
                {loadingMore ? '加载中…' : `加载更多 (还有 ${total - items.length} 条)`}
              </button>
            )}
            <div className="pw-footer-tip">
              愿神垂听每一个呼求 · 以弗所书 6:18
            </div>
          </>
        )}
      </div>
    </div>
  )
}
