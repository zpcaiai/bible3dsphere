/**
 * useGlobalAudio — Module-level singleton TTS hook.
 *
 * Guarantees only ONE audio plays at a time across the entire app.
 * Any component that starts playback automatically stops whatever is already playing.
 *
 * Usage:
 *   const { ttsState, speak, stop, togglePause } = useGlobalAudio()
 *   speak('Hello world')          // stops any current audio then plays
 *   stop()                        // stops current audio
 *   togglePause()                 // pause / resume
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { fetchTTS } from './api'

// ── Module-level singleton state ────────────────────────────────────────────
// All hook instances share this object. When any instance starts playing,
// it calls _globalStop() first, which notifies every registered listener.

const _singleton = {
  audioEl: null,         // current HTMLAudioElement (Google/Edge TTS)
  audioUrl: null,        // current object URL (to revoke on cleanup)
  stopListeners: new Set(), // registered () => void callbacks
}

function _globalStop() {
  // Stop and clean up the shared audio element
  if (_singleton.audioEl) {
    _singleton.audioEl.pause()
    _singleton.audioEl.src = ''
    _singleton.audioEl = null
  }
  if (_singleton.audioUrl) {
    try { URL.revokeObjectURL(_singleton.audioUrl) } catch (_) {}
    _singleton.audioUrl = null
  }
  // Cancel browser speechSynthesis
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
  // Notify every hook instance to reset its local state
  _singleton.stopListeners.forEach(fn => fn())
}

// ────────────────────────────────────────────────────────────────────────────

export function useGlobalAudio() {
  const [ttsState, setTtsState] = useState('idle') // idle | loading | playing | paused
  const isMountedRef = useRef(true)

  // Register / unregister stop listener on mount/unmount
  useEffect(() => {
    isMountedRef.current = true
    const handleStop = () => {
      if (isMountedRef.current) setTtsState('idle')
    }
    _singleton.stopListeners.add(handleStop)
    return () => {
      isMountedRef.current = false
      _singleton.stopListeners.delete(handleStop)
    }
  }, [])

  const stop = useCallback(() => {
    _globalStop()
  }, [])

  const togglePause = useCallback(() => {
    if (_singleton.audioEl) {
      if (_singleton.audioEl.paused) {
        _singleton.audioEl.play()
        setTtsState('playing')
      } else {
        _singleton.audioEl.pause()
        setTtsState('paused')
      }
    } else if (window.speechSynthesis) {
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume()
        setTtsState('playing')
      } else {
        window.speechSynthesis.pause()
        setTtsState('paused')
      }
    }
  }, [])

  const speak = useCallback(async (text) => {
    if (!text?.trim()) return

    // Stop whatever is currently playing globally
    _globalStop()

    if (!isMountedRef.current) return
    setTtsState('loading')

    // ── Try backend TTS (edge-tts / Google) ──────────────────────────
    try {
      const blob = await fetchTTS(text, 'zh-CN', 'zh-CN-XiaoxiaoNeural')
      if (!isMountedRef.current) return

      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)

      _singleton.audioEl = audio
      _singleton.audioUrl = url

      audio.onended = () => {
        if (_singleton.audioEl === audio) {
          _singleton.audioEl = null
          _singleton.audioUrl = null
          try { URL.revokeObjectURL(url) } catch (_) {}
        }
        if (isMountedRef.current) setTtsState('idle')
      }
      audio.onerror = () => {
        if (_singleton.audioEl === audio) {
          _singleton.audioEl = null
          _singleton.audioUrl = null
        }
        if (isMountedRef.current) setTtsState('idle')
      }

      await audio.play()
      if (isMountedRef.current) setTtsState('playing')
      return
    } catch (_backendErr) {
      // Fall through to browser speechSynthesis
    }

    // ── Fallback: browser speechSynthesis ─────────────────────────────
    if (!window.speechSynthesis) {
      if (isMountedRef.current) setTtsState('idle')
      return
    }

    window.speechSynthesis.cancel()
    const utter = new SpeechSynthesisUtterance(text)
    utter.lang = 'zh-CN'
    utter.rate = 0.9
    utter.pitch = 1.05

    // Prefer Xiaoxiao or any zh-CN neural voice
    const voices = window.speechSynthesis.getVoices()
    const zhVoice =
      voices.find(v => /xiaoxiao/i.test(v.name)) ||
      voices.find(v => v.lang === 'zh-CN') ||
      voices.find(v => v.lang.startsWith('zh'))
    if (zhVoice) utter.voice = zhVoice

    utter.onend = () => { if (isMountedRef.current) setTtsState('idle') }
    utter.onerror = () => { if (isMountedRef.current) setTtsState('idle') }

    window.speechSynthesis.speak(utter)
    if (isMountedRef.current) setTtsState('playing')
  }, [])

  return { ttsState, speak, stop, togglePause }
}

// ── Shared TTS UI components ─────────────────────────────────────────────────

/**
 * TTSButton — small inline 🔊 icon button for a single section.
 * Props: text (string), style (optional)
 */
export function TTSButton({ text, style }) {
  const { ttsState, speak, stop } = useGlobalAudio()

  function handleClick(e) {
    e.stopPropagation()
    if (ttsState === 'playing' || ttsState === 'loading') {
      stop()
    } else {
      speak(text)
    }
  }

  const isActive = ttsState === 'playing' || ttsState === 'loading'

  return (
    <button
      type="button"
      onClick={handleClick}
      title={isActive ? '停止' : '朗读'}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        padding: '2px 4px',
        borderRadius: '4px',
        fontSize: '14px',
        lineHeight: 1,
        color: isActive ? '#34c759' : 'rgba(255,255,255,0.45)',
        transition: 'color 0.2s',
        flexShrink: 0,
        ...style,
      }}
    >
      {ttsState === 'loading' ? '⏳' : isActive ? '⏹' : '🔊'}
    </button>
  )
}

/**
 * TTSFullBar — full-width play bar for reading a long piece of content.
 * Props: buildText (fn → string), label (optional string)
 */
export function TTSFullBar({ buildText, label = '全文朗读' }) {
  const { ttsState, speak, stop, togglePause } = useGlobalAudio()

  const isIdle = ttsState === 'idle'
  const isLoading = ttsState === 'loading'
  const isPlaying = ttsState === 'playing'
  const isPaused = ttsState === 'paused'

  function handleMain() {
    if (isIdle) {
      const text = typeof buildText === 'function' ? buildText() : buildText
      speak(text)
    } else if (isPlaying || isPaused) {
      togglePause()
    }
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      padding: '8px 12px',
      background: 'rgba(52,199,89,0.08)',
      border: '1px solid rgba(52,199,89,0.2)',
      borderRadius: 10,
      marginBottom: 12,
    }}>
      <button
        type="button"
        onClick={handleMain}
        disabled={isLoading}
        style={{
          background: isPlaying ? 'rgba(52,199,89,0.2)' : 'rgba(52,199,89,0.12)',
          border: '1px solid rgba(52,199,89,0.35)',
          borderRadius: 8,
          color: '#34c759',
          padding: '5px 12px',
          fontSize: 13,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        {isLoading ? '⏳' : isPlaying ? '⏸' : isPaused ? '▶' : '🔊'}
        <span>{isLoading ? '加载中...' : isPlaying ? '暂停' : isPaused ? '继续' : label}</span>
      </button>

      {(isPlaying || isPaused || isLoading) && (
        <button
          type="button"
          onClick={stop}
          style={{
            background: 'none',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 8,
            color: 'rgba(255,255,255,0.5)',
            padding: '5px 10px',
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          ⏹ 停止
        </button>
      )}

      {isIdle && (
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', marginLeft: 4 }}>
          小晓语音 · XiaoxiaoNeural
        </span>
      )}
    </div>
  )
}
