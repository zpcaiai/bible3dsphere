import { useState, useEffect, useRef, useCallback } from 'react'
import {
  fetchVoiceConfig, fetchVoiceGroups, createVoiceGroup,
  joinVoiceGroup, fetchVoiceToken, leaveVoiceGroup,
} from './api'

const ACCENT = '#34c759'
const toast = (m, t = 'info') => window.showToast?.(m, t)

// 端到端加密口令：仅存浏览器本地，绝不上送后端/服务器。密钥由口令本地派生，
// LiveKit SFU 拿到的是密文，无法解密 → 即便服务器/服务商也听不到通话内容。
const e2eeKeyFor = (gid) => { try { return localStorage.getItem('voice-e2ee-' + gid) || '' } catch { return '' } }
const setE2eeKeyFor = (gid, v) => { try { v ? localStorage.setItem('voice-e2ee-' + gid, v) : localStorage.removeItem('voice-e2ee-' + gid) } catch {} }

// ─────────────────────────────────────────────────────────────────────────────
// 语音通话页 — 多人实时群语音 (LiveKit SFU, Zoom 级音质)
// 三种视图: list(群列表) / call(通话中)
// ─────────────────────────────────────────────────────────────────────────────
export default function VoiceRoomPage({ user, token, onBack }) {
  const [view, setView] = useState('list')        // 'list' | 'call'
  const [enabled, setEnabled] = useState(true)     // LiveKit 是否已配置
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeGroup, setActiveGroup] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const data = await fetchVoiceGroups(token)
      setGroups(data.groups || [])
      if (data.enabled === false) setEnabled(false)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [token])

  useEffect(() => {
    fetchVoiceConfig(token).then(c => setEnabled(!!c.enabled)).catch(() => {})
    refresh()
  }, [token, refresh])

  const enterCall = (group) => { setActiveGroup(group); setView('call') }
  const exitCall = () => { setView('list'); setActiveGroup(null); refresh() }

  return (
    <div style={S.page}>
      <header style={S.header}>
        <button onClick={onBack} style={S.backBtn}>← 返回</button>
        <span style={S.title}>🎙 语音通话</span>
        <span style={{ width: 56 }} />
      </header>

      {view === 'call' && activeGroup ? (
        <CallScreen group={activeGroup} user={user} token={token} onLeave={exitCall} />
      ) : (
        <GroupList
          enabled={enabled} groups={groups} loading={loading}
          token={token} onRefresh={refresh} onEnter={enterCall}
        />
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 群列表 + 建群 + 加群
// ─────────────────────────────────────────────────────────────────────────────
function GroupList({ enabled, groups, loading, token, onRefresh, onEnter }) {
  const [newName, setNewName] = useState('')
  const [code, setCode] = useState('')
  const [creating, setCreating] = useState(false)
  const [joining, setJoining] = useState(false)

  const doCreate = async () => {
    const name = newName.trim() || '语音祷告群'
    setCreating(true)
    try {
      const { group } = await createVoiceGroup(name, token)
      toast('建群成功，邀请码 ' + group.join_code, 'success')
      setNewName('')
      await onRefresh()
    } catch (e) { toast(e.message || '建群失败', 'error') }
    finally { setCreating(false) }
  }

  const doJoin = async () => {
    const c = code.trim()
    if (!c) return toast('请输入邀请码', 'error')
    setJoining(true)
    try {
      const { group, already_member } = await joinVoiceGroup(c, token)
      toast(already_member ? '你已在该群中' : `已加入「${group.name}」`, 'success')
      setCode('')
      await onRefresh()
    } catch (e) { toast(e.message || '加入失败', 'error') }
    finally { setJoining(false) }
  }

  const copyCode = (c) => {
    navigator.clipboard?.writeText(c).then(() => toast('邀请码已复制', 'success')).catch(() => {})
  }

  return (
    <div style={S.scroll}>
      {!enabled && (
        <div style={S.warnBox}>
          ⚠️ 语音服务尚未配置。管理员需在后端设置 <code>LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET</code>
          （免费注册 livekit.cloud 即可）。配置后即可发起 Zoom 级群语音通话。
        </div>
      )}

      {/* 建群 / 加群 */}
      <section style={S.card}>
        <div style={S.cardTitle}>发起 / 加入</div>
        <div style={S.row}>
          <input
            style={S.input} value={newName} maxLength={40}
            placeholder="群名称，如「周三晚祷告会」"
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doCreate()}
          />
          <button style={S.primaryBtn} disabled={creating} onClick={doCreate}>
            {creating ? '建群中…' : '＋ 建群'}
          </button>
        </div>
        <div style={S.row}>
          <input
            style={{ ...S.input, letterSpacing: 2, textTransform: 'uppercase' }}
            value={code} maxLength={12} placeholder="输入邀请码加入他人的群"
            onChange={e => setCode(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doJoin()}
          />
          <button style={S.ghostBtn} disabled={joining} onClick={doJoin}>
            {joining ? '加入中…' : '加入'}
          </button>
        </div>
      </section>

      {/* 我的群 */}
      <div style={S.sectionLabel}>我的语音群</div>
      {loading ? (
        <div style={S.muted}>加载中…</div>
      ) : groups.length === 0 ? (
        <div style={S.empty}>还没有语音群。建一个群，把邀请码发给弟兄姐妹，一起开声祷告。</div>
      ) : (
        groups.map(g => (
          <div key={g.id} style={S.groupRow}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={S.groupName}>
                {g.name} {g.is_owner && <span style={S.ownerTag}>群主</span>}
              </div>
              <div style={S.groupMeta}>
                {g.member_count}/{g.max_members} 人 · 邀请码{' '}
                <span style={S.codeChip} onClick={() => copyCode(g.join_code)}>{g.join_code} 📋</span>
              </div>
            </div>
            <button style={S.callBtn} onClick={() => onEnter(g)} disabled={!enabled}>
              📞 进入
            </button>
          </div>
        ))
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// 通话中 — LiveKit 房间
// ─────────────────────────────────────────────────────────────────────────────
function CallScreen({ group, user, token, onLeave }) {
  const [status, setStatus] = useState('connecting')   // connecting | live | error
  const [errMsg, setErrMsg] = useState('')
  const [participants, setParticipants] = useState([]) // {sid, identity, name, isLocal, speaking, muted}
  const [micOn, setMicOn] = useState(true)
  const [denoise, setDenoise] = useState(false)
  const [encrypted, setEncrypted] = useState(false)   // E2EE 是否已生效
  const [keyPanel, setKeyPanel] = useState(false)
  const [keyDraft, setKeyDraft] = useState('')
  const [reconnectN, setReconnectN] = useState(0)

  const roomRef = useRef(null)
  const audioBin = useRef(null)
  const krispRef = useRef(null)
  const e2eeWorkerRef = useRef(null)

  // 把房间参与者状态同步到 React
  const sync = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const lp = room.localParticipant
    const speakers = new Set(room.activeSpeakers?.map(p => p.sid) || [])
    const list = [{
      sid: lp.sid, identity: lp.identity,
      name: (lp.name || user?.nickname || '我') + '（我）',
      isLocal: true, speaking: speakers.has(lp.sid),
      muted: !lp.isMicrophoneEnabled,
    }]
    room.remoteParticipants.forEach(p => {
      list.push({
        sid: p.sid, identity: p.identity,
        name: p.name || p.identity?.split('@')[0] || '弟兄姐妹',
        isLocal: false, speaking: speakers.has(p.sid),
        muted: !p.audioTrackPublications.size
          ? false
          : ![...p.audioTrackPublications.values()].some(pub => !pub.isMuted),
      })
    })
    setParticipants(list)
  }, [user])

  useEffect(() => {
    let cancelled = false
    let room = null

    async function start() {
      let LK
      try {
        LK = await import('livekit-client')
      } catch (e) {
        setStatus('error'); setErrMsg('语音组件加载失败'); return
      }
      const { Room, RoomEvent, Track } = LK

      let creds
      try {
        creds = await fetchVoiceToken(group.id, token)
      } catch (e) {
        if (!cancelled) { setStatus('error'); setErrMsg(e.message || '获取通话凭证失败') }
        return
      }
      if (cancelled) return

      // 端到端加密（可选）：有本地口令时启用，密钥本地派生，服务器只转发密文
      const e2eePass = e2eeKeyFor(group.id)
      let keyProvider = null
      if (e2eePass) {
        try {
          keyProvider = new LK.ExternalE2EEKeyProvider()
          e2eeWorkerRef.current = new Worker(new URL('livekit-client/e2ee-worker', import.meta.url))
        } catch (err) { keyProvider = null; e2eeWorkerRef.current = null }
      }

      room = new Room({
        adaptiveStream: false,
        dynacast: true,
        // Zoom 级采集：浏览器原生回声消除 / 降噪 / 自动增益
        audioCaptureDefaults: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        // Opus + RED(冗余抗丢包) + DTX(静音不发包)，语音码率上调
        publishDefaults: {
          dtx: true,
          red: true,
          audioPreset: { maxBitrate: 32000 },
        },
        ...(keyProvider && e2eeWorkerRef.current ? { e2ee: { keyProvider, worker: e2eeWorkerRef.current } } : {}),
      })
      roomRef.current = room

      // 启用 E2EE（口令派生密钥；浏览器不支持时优雅降级为仅传输加密）
      if (keyProvider && e2eePass) {
        try {
          await keyProvider.setKey(e2eePass)
          await room.setE2EEEnabled(true)
          if (!cancelled) setEncrypted(true)
        } catch (err) {
          console.error('E2EE 启用失败', err)
          if (!cancelled) { setEncrypted(false); toast('此浏览器不支持端到端加密，已降级为传输加密', 'info') }
        }
      } else if (!cancelled) {
        setEncrypted(false)
      }

      const onChange = () => { if (!cancelled) sync() }
      room
        .on(RoomEvent.ParticipantConnected, onChange)
        .on(RoomEvent.ParticipantDisconnected, onChange)
        .on(RoomEvent.ActiveSpeakersChanged, onChange)
        .on(RoomEvent.TrackMuted, onChange)
        .on(RoomEvent.TrackUnmuted, onChange)
        .on(RoomEvent.LocalTrackPublished, onChange)
        .on(RoomEvent.Disconnected, () => { if (!cancelled) { setStatus('error'); setErrMsg('通话已断开') } })
        .on(RoomEvent.TrackSubscribed, (track, pub, participant) => {
          if (track.kind === Track.Kind.Audio && audioBin.current) {
            const el = track.attach()
            el.dataset.sid = participant.sid
            el.autoplay = true
            audioBin.current.appendChild(el)
          }
          onChange()
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => {
          track.detach().forEach(el => el.remove())
          onChange()
        })

      try {
        await room.connect(creds.url, creds.token)
        await room.localParticipant.setMicrophoneEnabled(true)
        if (!cancelled) { setStatus('live'); setMicOn(true); sync() }
      } catch (e) {
        if (!cancelled) {
          setStatus('error')
          setErrMsg(/permission|NotAllowed/i.test(String(e)) ? '麦克风权限被拒绝，请在浏览器允许麦克风' : (e.message || '连接失败'))
        }
      }
    }

    start()
    return () => {
      cancelled = true
      try { krispRef.current?.dispose?.() } catch {}
      try { e2eeWorkerRef.current?.terminate?.() } catch {}
      e2eeWorkerRef.current = null
      try { room?.disconnect() } catch {}
      roomRef.current = null
      if (audioBin.current) audioBin.current.innerHTML = ''
    }
  }, [group.id, token, sync, reconnectN])

  const toggleMic = async () => {
    const room = roomRef.current
    if (!room) return
    const next = !micOn
    await room.localParticipant.setMicrophoneEnabled(next)
    setMicOn(next); sync()
  }

  // 可选：Krisp AI 降噪（需 LiveKit Cloud；失败则静默回退到原生降噪）
  const toggleDenoise = async () => {
    const room = roomRef.current
    if (!room) return
    if (!denoise) {
      try {
        const { KrispNoiseFilter } = await import('@livekit/krisp-noise-filter')
        const pub = [...room.localParticipant.audioTrackPublications.values()][0]
        const track = pub?.track
        if (!track) throw new Error('no mic track')
        krispRef.current = KrispNoiseFilter()
        await track.setProcessor(krispRef.current)
        setDenoise(true)
        toast('AI 降噪已开启', 'success')
      } catch (e) {
        console.error(e)
        toast('AI 降噪不可用（已使用浏览器原生降噪）', 'info')
      }
    } else {
      try {
        const pub = [...room.localParticipant.audioTrackPublications.values()][0]
        await pub?.track?.stopProcessor?.()
      } catch {}
      setDenoise(false)
      toast('AI 降噪已关闭', 'info')
    }
  }

  const hangUp = async () => { try { await roomRef.current?.disconnect() } catch {}; onLeave() }

  const openKey = () => { setKeyDraft(e2eeKeyFor(group.id)); setKeyPanel(true) }
  const saveKey = () => {
    setE2eeKeyFor(group.id, keyDraft.trim())
    setKeyPanel(false)
    setReconnectN(n => n + 1)   // 重连以应用新加密口令
    toast(keyDraft.trim() ? '已设置加密口令，正在以端到端加密重连…' : '已关闭端到端加密', 'info')
  }

  return (
    <div style={S.callWrap}>
      <div ref={audioBin} style={{ display: 'none' }} />

      <div style={S.callHead}>
        <div style={S.callName}>{group.name}</div>
        <div style={S.callStatus}>
          {status === 'connecting' && <span style={{ color: '#f0ad4e' }}>● 连接中…</span>}
          {status === 'live' && <span style={{ color: ACCENT }}>● 通话中 · {participants.length} 人在线</span>}
          {status === 'error' && <span style={{ color: '#ff6b6b' }}>● {errMsg || '连接失败'}</span>}
        </div>
        <div style={S.e2eeBar}>
          {encrypted ? (
            <span style={{ color: ACCENT }}>🔒 端到端加密已开 · 服务器也听不到
              <b onClick={openKey} style={S.e2eeAction}>更改口令</b></span>
          ) : (
            <span style={{ color: 'rgba(255,255,255,0.5)' }}>🔓 仅链路加密（服务器可解）·
              <b onClick={openKey} style={{ ...S.e2eeAction, color: '#f0ad4e' }}>设置加密口令</b></span>
          )}
        </div>
      </div>

      {keyPanel && (
        <div style={S.keyOverlay} onClick={() => setKeyPanel(false)}>
          <div style={S.keyCard} onClick={e => e.stopPropagation()}>
            <div style={S.keyTitle}>🔐 端到端加密口令</div>
            <div style={S.keyHint}>
              群内所有人填 <b>同一个口令</b> 才能互相听见。口令只存在你本机、由本地派生密钥，
              <b>绝不上送服务器</b>——LiveKit 与后端都拿到的是密文。请通过当面/Signal 等
              安全渠道私下约定，不要发在本群邀请码或微信里。
            </div>
            <input
              style={S.keyInput} value={keyDraft} type="text" autoFocus
              placeholder="输入共享口令（留空=关闭加密）"
              onChange={e => setKeyDraft(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && saveKey()}
            />
            <div style={S.keyBtns}>
              <button style={S.ghostBtn} onClick={() => setKeyPanel(false)}>取消</button>
              <button style={S.primaryBtn} onClick={saveKey}>保存并重连</button>
            </div>
          </div>
        </div>
      )}

      <div style={S.tiles}>
        {participants.map(p => (
          <div key={p.sid} style={{
            ...S.tile,
            boxShadow: p.speaking ? `0 0 0 3px ${ACCENT}, 0 0 22px rgba(52,199,89,0.55)` : 'none',
            borderColor: p.speaking ? ACCENT : 'rgba(255,255,255,0.12)',
          }}>
            <div style={{ ...S.avatar, background: p.isLocal ? 'rgba(52,199,89,0.18)' : 'rgba(255,255,255,0.08)' }}>
              {p.muted ? '🔇' : (p.speaking ? '🔊' : '🎙')}
            </div>
            <div style={S.tileName}>{p.name}</div>
            {p.muted && <div style={S.mutedTag}>已静音</div>}
          </div>
        ))}
        {status === 'live' && participants.length === 1 && (
          <div style={S.waitHint}>等待其他人加入…把邀请码 <b>{group.join_code}</b> 发给他们</div>
        )}
      </div>

      <div style={S.controls}>
        <button onClick={toggleMic} style={{ ...S.ctrlBtn, background: micOn ? 'rgba(255,255,255,0.1)' : '#ff6b6b' }}
          disabled={status !== 'live'}>
          <div style={{ fontSize: 22 }}>{micOn ? '🎙' : '🔇'}</div>
          <div style={S.ctrlLabel}>{micOn ? '静音' : '取消静音'}</div>
        </button>
        <button onClick={toggleDenoise} style={{ ...S.ctrlBtn, background: denoise ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.1)' }}
          disabled={status !== 'live'}>
          <div style={{ fontSize: 22 }}>✨</div>
          <div style={S.ctrlLabel}>{denoise ? 'AI降噪开' : 'AI降噪'}</div>
        </button>
        <button onClick={hangUp} style={{ ...S.ctrlBtn, background: '#ff3b30' }}>
          <div style={{ fontSize: 22 }}>📴</div>
          <div style={S.ctrlLabel}>挂断</div>
        </button>
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
const S = {
  page: { position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', background: '#0d1117', color: '#fff', fontFamily: 'inherit' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', borderBottom: '1px solid rgba(255,255,255,0.1)', background: 'rgba(13,17,23,0.98)', flexShrink: 0 },
  backBtn: { background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', fontSize: 14, cursor: 'pointer', width: 56, textAlign: 'left' },
  title: { fontSize: 16, fontWeight: 700 },
  scroll: { flex: 1, overflowY: 'auto', padding: '14px', boxSizing: 'border-box' },
  warnBox: { background: 'rgba(240,173,78,0.12)', border: '1px solid rgba(240,173,78,0.4)', borderRadius: 12, padding: '12px 14px', fontSize: 13, lineHeight: 1.6, color: '#f0c674', marginBottom: 14 },
  card: { background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: 14, marginBottom: 18 },
  cardTitle: { fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 10 },
  row: { display: 'flex', gap: 8, marginBottom: 8 },
  input: { flex: 1, minWidth: 0, background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 10, padding: '10px 12px', color: '#fff', fontSize: 14, fontFamily: 'inherit', outline: 'none' },
  primaryBtn: { background: ACCENT, border: 'none', borderRadius: 10, padding: '10px 16px', color: '#06210f', fontWeight: 700, fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap' },
  ghostBtn: { background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 10, padding: '10px 16px', color: '#fff', fontSize: 14, cursor: 'pointer', whiteSpace: 'nowrap' },
  sectionLabel: { fontSize: 13, color: 'rgba(255,255,255,0.45)', margin: '4px 2px 10px' },
  muted: { color: 'rgba(255,255,255,0.4)', fontSize: 14, padding: 8 },
  empty: { color: 'rgba(255,255,255,0.4)', fontSize: 14, lineHeight: 1.7, padding: '18px 12px', textAlign: 'center', border: '1px dashed rgba(255,255,255,0.14)', borderRadius: 12 },
  groupRow: { display: 'flex', alignItems: 'center', gap: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, padding: '12px 14px', marginBottom: 10 },
  groupName: { fontSize: 15, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  ownerTag: { fontSize: 10, background: 'rgba(52,199,89,0.2)', color: ACCENT, padding: '1px 6px', borderRadius: 6, marginLeft: 6, fontWeight: 700 },
  groupMeta: { fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 3 },
  codeChip: { color: ACCENT, cursor: 'pointer', fontWeight: 600 },
  callBtn: { background: ACCENT, border: 'none', borderRadius: 10, padding: '9px 14px', color: '#06210f', fontWeight: 700, fontSize: 13, cursor: 'pointer', whiteSpace: 'nowrap' },

  callWrap: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  callHead: { textAlign: 'center', padding: '18px 14px 6px' },
  callName: { fontSize: 18, fontWeight: 700 },
  callStatus: { fontSize: 13, marginTop: 6 },
  e2eeBar: { fontSize: 12, marginTop: 8, lineHeight: 1.5 },
  e2eeAction: { marginLeft: 6, cursor: 'pointer', textDecoration: 'underline', fontWeight: 600 },
  keyOverlay: { position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.72)', backdropFilter: 'blur(6px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 20, boxSizing: 'border-box' },
  keyCard: { width: '100%', maxWidth: 380, background: '#161b22', border: '1px solid rgba(255,255,255,0.14)', borderRadius: 16, padding: 18 },
  keyTitle: { fontSize: 16, fontWeight: 700, marginBottom: 10 },
  keyHint: { fontSize: 12.5, color: 'rgba(255,255,255,0.6)', lineHeight: 1.7, marginBottom: 14 },
  keyInput: { width: '100%', boxSizing: 'border-box', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.16)', borderRadius: 10, padding: '11px 12px', color: '#fff', fontSize: 15, fontFamily: 'inherit', outline: 'none', marginBottom: 14 },
  keyBtns: { display: 'flex', gap: 10, justifyContent: 'flex-end' },
  tiles: { flex: 1, overflowY: 'auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(110px, 1fr))', gap: 12, padding: 16, alignContent: 'start' },
  tile: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 16, padding: '16px 8px', transition: 'box-shadow 0.12s, border-color 0.12s' },
  avatar: { width: 56, height: 56, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 26 },
  tileName: { fontSize: 12, color: 'rgba(255,255,255,0.85)', textAlign: 'center', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' },
  mutedTag: { fontSize: 10, color: 'rgba(255,255,255,0.4)' },
  waitHint: { gridColumn: '1 / -1', textAlign: 'center', color: 'rgba(255,255,255,0.45)', fontSize: 13, lineHeight: 1.7, padding: 12 },
  controls: { display: 'flex', justifyContent: 'center', gap: 18, padding: '14px 16px 26px', borderTop: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 },
  ctrlBtn: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, border: 'none', borderRadius: 16, padding: '12px 16px', color: '#fff', cursor: 'pointer', minWidth: 76 },
  ctrlLabel: { fontSize: 11 },
}
