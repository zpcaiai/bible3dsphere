// CommunityPage.jsx — 在线社区：发个人状态 + 消息，浏览、阿们、评论
import { useCallback, useEffect, useState } from 'react'
import {
  fetchCommunityFeed, createCommunityPost, deleteCommunityPost, amenCommunityPost,
  fetchCommunityComments, createCommunityComment, deleteCommunityComment,
} from './api'
import { requestFriend } from './realtime/realtimeApi'
import { COMMUNITY_STATUS_GROUPS } from './communityStatuses'

const PAGE = 20

function relTime(iso) {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const s = Math.floor((Date.now() - t) / 1000)
  if (s < 60) return '刚刚'
  if (s < 3600) return `${Math.floor(s / 60)} 分钟前`
  if (s < 86400) return `${Math.floor(s / 3600)} 小时前`
  if (s < 7 * 86400) return `${Math.floor(s / 86400)} 天前`
  return iso.slice(0, 10)
}

function Avatar({ avatar, nickname }) {
  if (avatar && /^https?:\/\//.test(avatar)) {
    return <img className="cmty-avatar" src={avatar} alt="" />
  }
  const ch = avatar || (nickname || '友').trim().charAt(0)
  return <span className="cmty-avatar cmty-avatar-text">{ch}</span>
}

function Comments({ postId, token, user, onCountChange }) {
  const [items, setItems] = useState(null)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    let alive = true
    fetchCommunityComments(postId, token)
      .then(d => { if (alive) setItems(d.items || []) })
      .catch(e => { if (alive) setErr(e.message) })
    return () => { alive = false }
  }, [postId, token])

  async function submit() {
    const content = text.trim()
    if (!content) return
    setBusy(true); setErr('')
    try {
      const d = await createCommunityComment(postId, content, token)
      setItems(prev => [...(prev || []), {
        id: d.id, nickname: user?.nickname || '弟兄姐妹', avatar: user?.avatar || '',
        content, is_own: true, created_at: d.created_at,
      }])
      setText('')
      onCountChange?.(1)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  async function remove(id) {
    try {
      await deleteCommunityComment(id, token)
      setItems(prev => (prev || []).filter(c => c.id !== id))
      onCountChange?.(-1)
    } catch (e) { setErr(e.message) }
  }

  return (
    <div className="cmty-comments">
      {items === null && <div className="cmty-dim">加载评论…</div>}
      {items && items.length === 0 && <div className="cmty-dim">还没有评论，来写第一条吧</div>}
      {items && items.map(c => (
        <div key={c.id} className="cmty-comment">
          <Avatar avatar={c.avatar} nickname={c.nickname} />
          <div className="cmty-comment-body">
            <div className="cmty-comment-head">
              <span className="cmty-name">{c.nickname}</span>
              <span className="cmty-time">{relTime(c.created_at)}</span>
              {c.is_own && <button className="cmty-del" onClick={() => remove(c.id)}>删除</button>}
            </div>
            <div className="cmty-comment-text">{c.content}</div>
          </div>
        </div>
      ))}
      {user ? (
        <div className="cmty-comment-compose">
          <input value={text} onChange={e => setText(e.target.value)} maxLength={500}
            placeholder="写下你的回应或祝福…" onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }} />
          <button disabled={busy || !text.trim()} onClick={submit}>{busy ? '…' : '评论'}</button>
        </div>
      ) : <div className="cmty-dim">登录后可评论</div>}
      {err && <div className="cmty-err">{err}</div>}
    </div>
  )
}

export default function CommunityPage({ user, token, onBack }) {
  const [posts, setPosts] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [offset, setOffset] = useState(0)

  // composer
  const [status, setStatus] = useState(null)
  const [pickerOpen, setPickerOpen] = useState(false)
  const [content, setContent] = useState('')
  const [isPublic, setIsPublic] = useState(false)
  const [posting, setPosting] = useState(false)
  const [postErr, setPostErr] = useState('')
  const [friendRequested, setFriendRequested] = useState({})

  const [openComments, setOpenComments] = useState({})

  const load = useCallback(async (off = 0) => {
    setLoading(true); setError('')
    try {
      const d = await fetchCommunityFeed(PAGE, off, token)
      setTotal(d.total || 0)
      setPosts(prev => off === 0 ? (d.items || []) : [...prev, ...(d.items || [])])
      setOffset(off)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }, [token])

  useEffect(() => { load(0) }, [load])

  async function submitPost() {
    const text = content.trim()
    if (!status && !text) { setPostErr('请选择一个状态，或写点什么'); return }
    setPosting(true); setPostErr('')
    try {
      await createCommunityPost({
        content: text,
        statusKey: status?.key, statusLabel: status?.label, statusEmoji: status?.emoji,
      }, token, isPublic)
      setContent(''); setStatus(null); setPickerOpen(false); setIsPublic(false)
      await load(0)
    } catch (e) {
      const msg = e.message || ''
      if (msg.includes('请先加入或创建教会')) {
        setPostErr('请先加入或创建一个教会才能发布内容')
      } else {
        setPostErr(msg || '发布失败')
      }
    } finally { setPosting(false) }
  }

  async function handleAddFriend(email) {
    if (!email || friendRequested[email]) return
    try {
      await requestFriend(email)
      setFriendRequested(prev => ({ ...prev, [email]: true }))
      window.showToast?.('好友请求已发送', 'success')
    } catch (e) {
      window.showToast?.(e.message || '发送失败', 'error')
    }
  }

  async function toggleAmen(post) {
    if (!user) return
    // optimistic
    setPosts(prev => prev.map(p => p.id === post.id
      ? { ...p, amened: !p.amened, amen_count: p.amen_count + (p.amened ? -1 : 1) } : p))
    try {
      const d = await amenCommunityPost(post.id, token)
      setPosts(prev => prev.map(p => p.id === post.id ? { ...p, amened: d.amened, amen_count: d.amen_count } : p))
    } catch {
      setPosts(prev => prev.map(p => p.id === post.id
        ? { ...p, amened: post.amened, amen_count: post.amen_count } : p))
    }
  }

  async function removePost(post) {
    if (!window.confirm('确定删除这条状态？')) return
    try {
      await deleteCommunityPost(post.id, token)
      setPosts(prev => prev.filter(p => p.id !== post.id))
      setTotal(t => Math.max(0, t - 1))
    } catch (e) { alert(e.message) }
  }

  function bumpComment(postId, delta) {
    setPosts(prev => prev.map(p => p.id === postId
      ? { ...p, comment_count: Math.max(0, p.comment_count + delta) } : p))
  }

  return (
    <div className="cmty">
      <div className="cmty-head">
        {onBack && <button className="cmty-back" onClick={onBack}>← 返回</button>}
        <div className="cmty-title">
          <h2>🌐 在线社区</h2>
          <p>分享你此刻的状态与心声，彼此守望、回应、代祷</p>
        </div>
      </div>

      {/* 发布区 */}
      {user ? (
        <div className="cmty-composer">
          <div className="cmty-compose-top">
            <button className={`cmty-status-pick ${status ? 'has' : ''}`} onClick={() => setPickerOpen(o => !o)}>
              {status ? <span>{status.emoji} {status.label}</span> : <span>＋ 选择状态</span>}
            </button>
            {status && <button className="cmty-status-clear" onClick={() => setStatus(null)}>×</button>}
          </div>
          {pickerOpen && (
            <div className="cmty-picker">
              {COMMUNITY_STATUS_GROUPS.map(g => (
                <div key={g.group} className="cmty-picker-group">
                  <div className="cmty-picker-label">{g.group}</div>
                  <div className="cmty-picker-items">
                    {g.items.map(it => (
                      <button key={it.key}
                        className={`cmty-status-chip ${status?.key === it.key ? 'on' : ''}`}
                        onClick={() => { setStatus(it); setPickerOpen(false) }}>
                        {it.emoji} {it.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          <textarea className="cmty-textarea" value={content} maxLength={1000}
            onChange={e => setContent(e.target.value)} placeholder="说点什么吧…（也可只发一个状态）" rows={3} />
          <div className="cmty-compose-actions">
            <span className="cmty-count">{content.length}/1000</span>
            <label style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'rgba(255,255,255,0.55)', cursor: 'pointer', userSelect: 'none' }}>
              <input type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} style={{ accentColor: '#007aff' }} />
              🌍 公开到全平台
            </label>
            <button className="cmty-post-btn" disabled={posting || (!status && !content.trim())} onClick={submitPost}>
              {posting ? '发布中…' : '发布'}
            </button>
          </div>
          {postErr && <div className="cmty-err">{postErr}</div>}
        </div>
      ) : (
        <div className="cmty-login-hint">👋 登录后即可发布状态与消息（现在也能浏览大家的分享）</div>
      )}

      {/* 信息流 */}
      {error && <div className="cmty-err">{error}</div>}
      {loading && posts.length === 0 && <div className="cmty-dim">加载中…</div>}
      {!loading && posts.length === 0 && !error && (
        <div className="cmty-empty">还没有人分享，成为第一个吧 🌱</div>
      )}

      <div className="cmty-feed">
        {posts.map(post => (
          <div key={post.id} className="cmty-post">
            <div className="cmty-post-head">
              <Avatar avatar={post.avatar} nickname={post.nickname} />
              <div className="cmty-post-meta">
                <div className="cmty-name-row">
                  <span className="cmty-name">{post.nickname}</span>
                  {post.status?.label && (
                    <span className="cmty-status-badge">{post.status.emoji} {post.status.label}</span>
                  )}
                  {post.is_public && !post.same_church && !post.is_own && (
                    <span style={{ fontSize: 10, background: 'rgba(0,122,255,0.15)', border: '1px solid rgba(0,122,255,0.35)', color: '#60a5fa', borderRadius: 6, padding: '1px 6px', marginLeft: 4 }}>🌍 全平台</span>
                  )}
                </div>
                <span className="cmty-time">{relTime(post.created_at)}</span>
              </div>
              {post.is_own && <button className="cmty-del" onClick={() => removePost(post)}>删除</button>}
            </div>
            {post.content && <div className="cmty-post-content">{post.content}</div>}
            <div className="cmty-post-actions">
              <button className={`cmty-act ${post.amened ? 'on' : ''}`} disabled={!user}
                onClick={() => toggleAmen(post)} title={user ? '阿们' : '登录后可阿们'}>
                🙏 阿们{post.amen_count > 0 ? ` · ${post.amen_count}` : ''}
              </button>
              <button className="cmty-act"
                onClick={() => setOpenComments(o => ({ ...o, [post.id]: !o[post.id] }))}>
                💬 评论{post.comment_count > 0 ? ` · ${post.comment_count}` : ''}
              </button>
              {post.is_public && !post.same_church && !post.is_own && post.author_email && user && (
                <button
                  className="cmty-act"
                  disabled={!!friendRequested[post.author_email]}
                  onClick={() => handleAddFriend(post.author_email)}
                  title="加为好友"
                >
                  {friendRequested[post.author_email] ? '已请求 ✓' : '➕ 加好友'}
                </button>
              )}
            </div>
            {openComments[post.id] && (
              <Comments postId={post.id} token={token} user={user}
                onCountChange={(d) => bumpComment(post.id, d)} />
            )}
          </div>
        ))}
      </div>

      {posts.length < total && (
        <button className="cmty-more" disabled={loading} onClick={() => load(offset + PAGE)}>
          {loading ? '加载中…' : '加载更多'}
        </button>
      )}
    </div>
  )
}
