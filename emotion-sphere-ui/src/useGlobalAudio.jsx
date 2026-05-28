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

// ── Bible reference expansion ────────────────────────────────────────────────
// Expands abbreviated references like "太 六 10" → "马太福音6章10节" before TTS.
const _BOOK_ABBR = {
  // ── 多字简写（优先匹配，放前面）────────────────────────────────────────
  '撒上':'撒母耳记上', '撒下':'撒母耳记下',
  '王上':'列王纪上',   '王下':'列王纪下',
  '代上':'历代志上',   '代下':'历代志下',
  '林前':'哥林多前书', '林后':'哥林多后书',
  '帖前':'帖撒罗尼迦前书', '帖后':'帖撒罗尼迦后书',
  '提前':'提摩太前书', '提后':'提摩太后书',
  '彼前':'彼得前书',   '彼后':'彼得后书',
  '约壹':'约翰一书',   '约贰':'约翰二书', '约叁':'约翰三书',
  // ── 单字简写 ─────────────────────────────────────────────────────────
  '创':'创世记', '出':'出埃及记', '利':'利未记', '民':'民数记', '申':'申命记',
  '书':'约书亚记', '士':'士师记', '得':'路得记',
  '拉':'以斯拉记', '尼':'尼希米记', '斯':'以斯帖记', '伯':'约伯记',
  '诗':'诗篇', '箴':'箴言', '传':'传道书', '歌':'雅歌',
  '赛':'以赛亚书', '耶':'耶利米书', '哀':'耶利米哀歌', '结':'以西结书', '但':'但以理书',
  '何':'何西阿书', '珥':'约珥书', '摩':'阿摩司书', '俄':'俄巴底亚书', '拿':'约拿书',
  '弥':'弥迦书', '鸿':'那鸿书', '哈':'哈巴谷书', '番':'西番雅书', '该':'哈该书',
  '亚':'撒迦利亚书', '玛':'玛拉基书',
  '太':'马太福音', '可':'马可福音', '路':'路加福音', '约':'约翰福音', '徒':'使徒行传',
  '罗':'罗马书', '加':'加拉太书', '弗':'以弗所书', '腓':'腓立比书',
  '西':'歌罗西书', '多':'提多书', '门':'腓利门书',
  '来':'希伯来书', '雅':'雅各书', '犹':'犹大书', '启':'启示录',
}

// Chinese numeral → Arabic integer
function _cnToInt(s) {
  if (!s) return null
  if (/^\d+$/.test(s)) return parseInt(s, 10)
  const D = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
  const U = {'十':10,'百':100,'千':1000}
  let res = 0, tmp = 0
  for (const c of s) {
    if (D[c] !== undefined) { tmp = D[c] }
    else if (U[c] !== undefined) {
      const u = U[c]
      if (tmp === 0 && u === 10) tmp = 1   // 十五 → 15
      res += tmp * u; tmp = 0
    }
  }
  return (res + tmp) || null
}

// Build the regex once (abbrs sorted longest-first to avoid partial matches)
const _ABBR_PAT = Object.keys(_BOOK_ABBR)
  .sort((a, b) => b.length - a.length)
  .map(a => a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  .join('|')
const _NUM = '[零一二三四五六七八九十百千\\d]+'
// Matches: <abbr> <space?> <chapter> <space?> [章/:] <space?> <verse?> [节?]
const _BIBLE_RE = new RegExp(
  `(${_ABBR_PAT})\\s*(${_NUM})\\s*[章篇卷:：]?\\s*(${_NUM})?\\s*节?`,
  'g'
)

/**
 * Expand Bible abbreviations in text before TTS.
 * "太 六 10" → "马太福音6章10节"
 * "约3:16"  → "约翰福音3章16节"
 * "诗篇23"  → unchanged (full name, not an abbr key)
 */
function _expandBibleRefs(text) {
  if (!text) return text
  return text.replace(_BIBLE_RE, (_m, abbr, chStr, verseStr) => {
    const full = _BOOK_ABBR[abbr]
    if (!full) return _m
    const ch = _cnToInt(chStr)
    if (!ch) return _m
    const v = verseStr ? _cnToInt(verseStr) : null
    return v ? `${full}${ch}章${v}节` : `${full}${ch}章`
  })
}



// ── Module-level singleton state ────────────────────────────────────────────
// All hook instances share this object. When any instance starts playing,
// it calls _globalStop() first, which notifies every registered listener.

const _singleton = {
  audioEl: null,         // current HTMLAudioElement (Google/Edge TTS)
  audioUrl: null,        // current object URL (to revoke on cleanup)
  stopListeners: new Set(), // registered () => void callbacks
  speakGen: 0,           // monotonically increasing — each speak() call gets its own gen;
                         // stale in-flight fetches that don't match the current gen are discarded
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

  const speak = useCallback(async (rawText) => {
    if (!rawText?.trim()) return
    const text = _expandBibleRefs(rawText)

    // Stop whatever is currently playing globally, then claim a new generation
    // so any previous in-flight fetchTTS() call is silently discarded when it resolves.
    _globalStop()
    const myGen = ++_singleton.speakGen

    if (!isMountedRef.current) return
    setTtsState('loading')

    // ── Try backend TTS (edge-tts / Google) ──────────────────────────
    try {
      const blob = await fetchTTS(text, 'zh-CN', 'zh-CN-XiaoxiaoNeural')
      // If speak() was called again while we were fetching, bail out immediately
      // so we never create a second audio element.
      if (_singleton.speakGen !== myGen || !isMountedRef.current) return

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
  const { ttsState, speak, stop } = useGlobalAudio()

  const isIdle = ttsState === 'idle'
  const isLoading = ttsState === 'loading'
  const isPlaying = ttsState === 'playing'
  const isPaused = ttsState === 'paused'

  // Clicking the main button always (re-)starts from the beginning.
  // speak() calls _globalStop() internally first, so rapid double-clicks are safe.
  // The generation counter in speak() discards any stale in-flight fetch, preventing
  // multiple simultaneous audio streams.
  function handleMain() {
    const text = typeof buildText === 'function' ? buildText() : buildText
    speak(text)
  }

  const isActive = isLoading || isPlaying || isPaused

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
        style={{
          background: isActive ? 'rgba(52,199,89,0.2)' : 'rgba(52,199,89,0.12)',
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
        {isLoading ? '⏳' : isActive ? '🔄' : '🔊'}
        <span>{isLoading ? '加载中...' : isActive ? '重新播放' : label}</span>
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
