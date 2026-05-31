// 圣徒相通 (Communion) — 好友 + 1对1聊天 (QQ式)。
// 语音通话复用现有的 LiveKit 多人语音 (VoiceRoomPage)：本页的"语音通话"按钮
// 通过 onOpenVoice 跳转到该页，不再内置 mesh WebRTC。
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRealtime } from './realtime/useRealtime'
import {
  fetchFriends, requestFriend, acceptFriend, removeFriend,
  fetchChatHistory, markRead, fetchDirectVoiceToken, fetchVoiceEnabled,
} from './realtime/realtimeApi'
import LiveKitCall from './realtime/LiveKitCall'

function shortName(email, nickname) {
  return nickname || (email ? email.split('@')[0] : '弟兄姐妹')
}
function timeLabel(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  } catch { return '' }
}
function dedupe(arr) {
  const seen = new Set(); const out = []
  for (const m of arr) {
    const k = m.id ? `s${m.id}` : m.key
    if (seen.has(k)) continue
    seen.add(k); out.push(m)
  }
  return out
}

export default function CommunionPage({ user, onBack, onOpenVoice }) {
  const myEmail = (user?.email || '').toLowerCase()
  const [friends, setFriends] = useState([])
  const [incoming, setIncoming] = useState([])
  const [activePeer, setActivePeer] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [addEmail, setAddEmail] = useState('')
  const [toast, setToast] = useState('')
  const [typingFrom, setTypingFrom] = useState(null)
  const [incomingCall, setIncomingCall] = useState(null)
  const [activeCall, setActiveCall] = useState(null)

  const activePeerRef = useRef(null)
  activePeerRef.current = activePeer
  const friendsRef = useRef([])
  friendsRef.current = friends
  const activeCallRef = useRef(null)
  activeCallRef.current = activeCall
  const messagesEndRef = useRef(null)

  const showToast = useCallback((t) => {
    setToast(t); setTimeout(() => setToast(''), 2600)
  }, [])

  function normMsg(m) {
    return {
      key: m.id ? `s${m.id}` : (m.client_id || `${m.from}-${m.created_at}-${Math.random()}`),
      id: m.id,
      body: m.body,
      mine: (m.sender || m.from) === myEmail || m.self === true,
      created_at: m.created_at,
      client_id: m.client_id,
    }
  }

  // ---------------- WebSocket dispatcher ----------------
  const onMessage = useCallback((msg) => {
    switch (msg.type) {
      case 'ready': {
        const online = new Set(msg.online_friends || [])
        setFriends((fs) => fs.map((f) => ({ ...f, online: online.has(f.email) })))
        break
      }
      case 'presence':
        setFriends((fs) => fs.map((f) => f.email === msg.email ? { ...f, online: msg.online } : f))
        break
      case 'friend_request':
      case 'friend_added':
        loadFriends()
        break
      case 'chat': {
        const peer = msg.self ? msg.to : msg.from
        const active = activePeerRef.current
        if (active && active.email === peer) {
          setMessages((m) => dedupe([...m, normMsg(msg)]))
          if (!msg.self) markRead(peer).catch(() => {})
        } else if (!msg.self) {
          setFriends((fs) => fs.map((f) => f.email === peer
            ? { ...f, unread: (f.unread || 0) + 1, last_message: msg.body } : f))
        }
        break
      }
      case 'typing': {
        const active = activePeerRef.current
        if (active && active.email === msg.from) {
          setTypingFrom(msg.from)
          setTimeout(() => setTypingFrom(null), 2500)
        }
        break
      }
      case 'call_invite': {
        if (activeCallRef.current) { send({ type: 'call_decline', to: msg.from, room: msg.room }); break }
        const f = friendsRef.current?.find?.((x) => x.email === msg.from)
        setIncomingCall({ from: msg.from, room: msg.room, name: shortName(msg.from, f?.nickname) })
        break
      }
      case 'call_decline':
        if (activeCallRef.current?.outgoing) { showToast('对方未接听'); setActiveCall(null) }
        setIncomingCall((ic) => (ic && ic.from === msg.from ? null : ic))
        break
      case 'error':
        if (msg.code === 'not_friends') showToast('仅好友之间可以聊天')
        break
      default:
        break
    }
  }, [])

  const { connected, send } = useRealtime(onMessage, !!myEmail)

  // ---------------- Friends ----------------
  const loadFriends = useCallback(async () => {
    try {
      const data = await fetchFriends()
      setFriends(data.friends || [])
      setIncoming(data.incoming || [])
    } catch (e) { /* ignore */ }
  }, [])

  useEffect(() => { if (myEmail) loadFriends() }, [myEmail, loadFriends])
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typingFrom])

  async function onAddFriend() {
    const email = addEmail.trim().toLowerCase()
    if (!email) return
    try {
      const r = await requestFriend(email)
      showToast(r.status === 'accepted' ? '已成为好友' : '好友请求已发送')
      setAddEmail(''); loadFriends()
    } catch (e) { showToast(e.message || '添加失败') }
  }
  async function onAccept(email) {
    try { await acceptFriend(email); showToast('已添加好友'); loadFriends() }
    catch (e) { showToast(e.message) }
  }
  async function onRemove(email) {
    if (!window.confirm('确定删除该好友？')) return
    try { await removeFriend(email); if (activePeer?.email === email) setActivePeer(null); loadFriends() }
    catch (e) { showToast(e.message) }
  }

  // ---------------- Chat ----------------
  async function openChat(friend) {
    setActivePeer(friend); setMessages([]); setTypingFrom(null)
    try {
      const data = await fetchChatHistory(friend.email, { limit: 50 })
      setMessages((data.messages || []).map(normMsg))
      await markRead(friend.email)
      setFriends((fs) => fs.map((f) => f.email === friend.email ? { ...f, unread: 0 } : f))
    } catch (e) { /* ignore */ }
  }
  function sendChat() {
    const body = draft.trim()
    if (!body || !activePeer) return
    const ok = send({ type: 'chat', to: activePeer.email, body, client_id: 'c-' + Date.now() })
    if (!ok) { showToast('连接断开，正在重连…'); return }
    setDraft('')
  }
  function onDraftChange(v) {
    setDraft(v)
    if (activePeer) send({ type: 'typing', to: activePeer.email })
  }
  function startVoice() {
    if (typeof onOpenVoice === 'function') onOpenVoice()
    else showToast('语音通话请前往「语音通话」页')
  }
  async function startDirectCall(friend) {
    if (!friend) return
    if (activeCallRef.current) { showToast('通话进行中'); return }
    const enabled = await fetchVoiceEnabled()
    if (!enabled) { showToast('语音通话尚未配置（需管理员设置 LiveKit）'); return }
    if (!friend.online) { showToast('对方当前不在线'); return }
    try {
      const creds = await fetchDirectVoiceToken(friend.email)
      send({ type: 'call_invite', to: friend.email, room: creds.room,
             title: `${shortName(myEmail, user?.nickname)} 邀请你语音通话` })
      setActiveCall({ creds, title: shortName(friend.email, friend.nickname), outgoing: true, peer: friend.email })
    } catch (e) { showToast(e.message || '发起通话失败') }
  }
  async function acceptIncoming() {
    const ic = incomingCall
    if (!ic) return
    setIncomingCall(null)
    try {
      const creds = await fetchDirectVoiceToken(ic.from)
      setActiveCall({ creds, title: ic.name, outgoing: false, peer: ic.from })
    } catch (e) { showToast(e.message || '接听失败') }
  }
  function declineIncoming() {
    if (incomingCall) send({ type: 'call_decline', to: incomingCall.from, room: incomingCall.room })
    setIncomingCall(null)
  }
  function endCall() {
    const ac = activeCallRef.current
    if (ac?.outgoing && ac.peer) send({ type: 'call_decline', to: ac.peer, room: ac.creds?.room })
    setActiveCall(null)
  }

  // ---------------- Render ----------------
  return (
    <div className="communion-page">
      <header className="communion-header glass">
        <button className="communion-back" onClick={onBack}>← 返回</button>
        <div className="communion-title">
          圣徒相通
          <span className={`communion-conn ${connected ? 'on' : 'off'}`}>
            {connected ? '● 在线' : '○ 连接中'}
          </span>
        </div>
        <div style={{ width: 56 }} />
      </header>

      <div className="communion-body">
        <aside className={`communion-sidebar ${activePeer ? 'has-active' : ''}`}>
          <div className="communion-add">
            <input
              value={addEmail}
              onChange={(e) => setAddEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && onAddFriend()}
              placeholder="输入好友邮箱添加"
            />
            <button onClick={onAddFriend}>添加</button>
          </div>

          {incoming.length > 0 && (
            <div className="communion-incoming">
              <div className="communion-section-title">好友请求</div>
              {incoming.map((r) => (
                <div key={r.email} className="communion-req">
                  <span>{shortName(r.email, r.nickname)}</span>
                  <button onClick={() => onAccept(r.email)}>接受</button>
                </div>
              ))}
            </div>
          )}

          <div className="communion-section-title">好友 ({friends.length})</div>
          <div className="communion-friends">
            {friends.length === 0 && <div className="communion-empty">还没有好友，添加邮箱开始相通</div>}
            {friends.map((f) => (
              <div
                key={f.email}
                className={`communion-friend ${activePeer?.email === f.email ? 'active' : ''}`}
                onClick={() => openChat(f)}
                onContextMenu={(e) => { e.preventDefault(); onRemove(f.email) }}
              >
                <div className="communion-avatar">
                  {f.avatar ? <img src={f.avatar} alt="" /> : shortName(f.email, f.nickname)[0]}
                  <span className={`communion-dot ${f.online ? 'online' : ''}`} />
                </div>
                <div className="communion-finfo">
                  <div className="communion-fname">{shortName(f.email, f.nickname)}</div>
                  <div className="communion-flast">{f.last_message || (f.online ? '在线' : '离线')}</div>
                </div>
                {f.unread > 0 && <span className="communion-badge">{f.unread}</span>}
                <button className="communion-call-btn" title="语音通话"
                  onClick={(e) => { e.stopPropagation(); startDirectCall(f) }}>📞</button>
              </div>
            ))}
          </div>
        </aside>

        <main className={`communion-chat ${activePeer ? 'open' : ''}`}>
          {!activePeer ? (
            <div className="communion-placeholder">
              <div style={{ fontSize: 40 }}>🕊️</div>
              <p>选择一位弟兄姊妹开始聊天</p>
              <button className="communion-head-call" onClick={startVoice}>🎙 多人语音通话</button>
            </div>
          ) : (
            <>
              <div className="communion-chat-head glass">
                <button className="communion-back-mobile" onClick={() => setActivePeer(null)}>←</button>
                <div className="communion-chat-name">
                  {shortName(activePeer.email, activePeer.nickname)}
                  <span className={`communion-dot ${activePeer.online ? 'online' : ''}`} />
                </div>
                <button className="communion-head-call" onClick={() => startDirectCall(activePeer)}>📞 语音通话</button>
              </div>

              <div className="communion-messages">
                {messages.map((m) => (
                  <div key={m.key} className={`communion-msg ${m.mine ? 'mine' : ''}`}>
                    <div className="communion-bubble">{m.body}</div>
                    <div className="communion-msg-time">{timeLabel(m.created_at)}</div>
                  </div>
                ))}
                {typingFrom && <div className="communion-typing">对方正在输入…</div>}
                <div ref={messagesEndRef} />
              </div>

              <div className="communion-compose glass">
                <textarea
                  value={draft}
                  onChange={(e) => onDraftChange(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                  placeholder="输入消息，Enter 发送"
                  rows={1}
                />
                <button onClick={sendChat} disabled={!draft.trim()}>发送</button>
              </div>
            </>
          )}
        </main>
      </div>

      {activeCall && (
        <LiveKitCall
          url={activeCall.creds.url}
          token={activeCall.creds.token}
          title={activeCall.title}
          selfName={shortName(myEmail, user?.nickname)}
          outgoing={activeCall.outgoing}
          onLeave={endCall}
        />
      )}

      {incomingCall && !activeCall && (
        <div className="communion-invite-overlay">
          <div className="communion-invite glass">
            <div className="communion-invite-title">📞 {incomingCall.name} 邀请你语音通话</div>
            <div className="communion-invite-actions">
              <button className="communion-accept" onClick={acceptIncoming}>接听</button>
              <button className="communion-decline" onClick={declineIncoming}>拒绝</button>
            </div>
          </div>
        </div>
      )}

      {toast && <div className="communion-toast">{toast}</div>}
    </div>
  )
}
