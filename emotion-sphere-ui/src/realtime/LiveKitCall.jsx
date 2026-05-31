// 通用 LiveKit 通话组件 — 用于「圣徒相通」1对1 秒拨。
// 与 VoiceRoomPage 的 CallScreen 同样的高质量采集 (Opus+RED+DTX+原生回声消除)，
// 但解耦于"群"概念：直接吃 { url, token } 进房。
import { useCallback, useEffect, useRef, useState } from 'react'

export default function LiveKitCall({ url, token, title, selfName, outgoing, onLeave }) {
  const [status, setStatus] = useState('connecting') // connecting | live | error
  const [errMsg, setErrMsg] = useState('')
  const [participants, setParticipants] = useState([])
  const [micOn, setMicOn] = useState(true)
  const roomRef = useRef(null)
  const audioBin = useRef(null)

  const sync = useCallback(() => {
    const room = roomRef.current
    if (!room) return
    const lp = room.localParticipant
    const speakers = new Set(room.activeSpeakers?.map((p) => p.sid) || [])
    const list = [{
      sid: lp.sid, name: (lp.name || selfName || '我') + '（我）',
      isLocal: true, speaking: speakers.has(lp.sid), muted: !lp.isMicrophoneEnabled,
    }]
    room.remoteParticipants.forEach((p) => {
      list.push({
        sid: p.sid,
        name: p.name || p.identity?.split('@')[0] || '弟兄姐妹',
        isLocal: false, speaking: speakers.has(p.sid),
        muted: p.audioTrackPublications.size
          ? ![...p.audioTrackPublications.values()].some((pub) => !pub.isMuted)
          : false,
      })
    })
    setParticipants(list)
  }, [selfName])

  useEffect(() => {
    let cancelled = false
    let room = null
    async function start() {
      let LK
      try { LK = await import('livekit-client') }
      catch { setStatus('error'); setErrMsg('语音组件加载失败'); return }
      const { Room, RoomEvent, Track } = LK
      room = new Room({
        adaptiveStream: false,
        dynacast: true,
        audioCaptureDefaults: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        publishDefaults: { dtx: true, red: true, audioPreset: { maxBitrate: 32000 } },
      })
      roomRef.current = room
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
            const el = track.attach(); el.dataset.sid = participant.sid; el.autoplay = true
            audioBin.current.appendChild(el)
          }
          onChange()
        })
        .on(RoomEvent.TrackUnsubscribed, (track) => { track.detach().forEach((el) => el.remove()); onChange() })
      try {
        await room.connect(url, token)
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
      try { room?.disconnect() } catch { /* noop */ }
      roomRef.current = null
      if (audioBin.current) audioBin.current.innerHTML = ''
    }
  }, [url, token, sync])

  const toggleMic = async () => {
    const room = roomRef.current
    if (!room) return
    const next = !micOn
    await room.localParticipant.setMicrophoneEnabled(next)
    setMicOn(next); sync()
  }
  const hangUp = async () => { try { await roomRef.current?.disconnect() } catch { /* noop */ } onLeave?.() }

  const remoteCount = participants.filter((p) => !p.isLocal).length

  return (
    <div className="communion-call-overlay">
      <div className="communion-call-screen">
        <div ref={audioBin} style={{ display: 'none' }} />
        <div className="communion-call-top">
          <div className="communion-call-peer">{title || '语音通话'}</div>
          <div className="communion-call-state">
            {status === 'connecting' && <span style={{ color: '#f0ad4e' }}>● {outgoing ? '正在呼叫…' : '接入中…'}</span>}
            {status === 'live' && remoteCount === 0 && <span style={{ color: '#f0ad4e' }}>● 等待对方接听…</span>}
            {status === 'live' && remoteCount > 0 && <span style={{ color: '#34c759' }}>● 通话中</span>}
            {status === 'error' && <span style={{ color: '#ff6b6b' }}>● {errMsg || '连接失败'}</span>}
          </div>
        </div>

        <div className="communion-call-tiles">
          {participants.map((p) => (
            <div key={p.sid} className={`communion-call-tile ${p.speaking ? 'speaking' : ''}`}>
              <div className="communion-call-bubble">{p.muted ? '🔇' : (p.speaking ? '🔊' : '🎙')}</div>
              <div className="communion-call-tname">{p.name}</div>
            </div>
          ))}
        </div>

        <div className="communion-call-actions">
          <button className="communion-call-ctrl" onClick={toggleMic} disabled={status !== 'live'}
            style={{ background: micOn ? 'rgba(255,255,255,.12)' : '#ff6b6b' }}>
            <div style={{ fontSize: 22 }}>{micOn ? '🎙' : '🔇'}</div>
            <div className="communion-call-ctrl-label">{micOn ? '静音' : '取消静音'}</div>
          </button>
          <button className="communion-call-ctrl" onClick={hangUp} style={{ background: '#ff3b30' }}>
            <div style={{ fontSize: 22 }}>📴</div>
            <div className="communion-call-ctrl-label">挂断</div>
          </button>
        </div>
      </div>
    </div>
  )
}
