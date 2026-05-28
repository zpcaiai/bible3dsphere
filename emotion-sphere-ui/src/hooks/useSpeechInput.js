/**
 * useSpeechInput
 *
 * Encapsulates all browser microphone + Deepgram transcription logic
 * that was previously inline in App.jsx.
 *
 * Usage:
 *   const speech = useSpeechInput({
 *     deepgramApiKey,
 *     onTranscript: (text) => setQuery(q => q ? `${q} ${text}` : text),
 *     onLoadingChange: setLoading,
 *     postProcess: async (raw) => { /* punctuation + bilingual * / return raw },
 *   })
 *
 * Returns:
 *   isRecording, recordingSeconds, recordingError, setRecordingError,
 *   isWeChat, isIOS, isSafari, isAndroid,
 *   maxRecordingSeconds,
 *   recordingDelayRef,
 *   startRecording(), stopRecording()
 */
import { useState, useRef, useCallback } from 'react'

const MAX_RECORDING_SECONDS = 120

export function useSpeechInput ({
  deepgramApiKey = '',
  onTranscript,
  onLoadingChange,
  postProcess,
} = {}) {
  // ── Browser detection (stable across renders) ──────────────────────────────
  const ua = (typeof navigator !== 'undefined' && navigator.userAgent) || ''
  const isWeChat  = /MicroMessenger/i.test(ua)
  const isIOS     = /iPhone|iPad|iPod/i.test(ua)
  const isSafari  = /Safari/i.test(ua) && !/Chrome/i.test(ua)
  const isAndroid = /Android/i.test(ua)

  // ── State ──────────────────────────────────────────────────────────────────
  const [isRecording,     setIsRecording]     = useState(false)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [recordingError,  setRecordingError]  = useState(null)

  // ── Refs ───────────────────────────────────────────────────────────────────
  const mediaRecorderRef  = useRef(null)
  const audioChunksRef    = useRef([])
  const recordingTimerRef = useRef(null)
  /** Long-press delay handle — exposed so callers can cancel it on mouseLeave */
  const recordingDelayRef = useRef(null)

  // ── Internal: Deepgram transcription ──────────────────────────────────────
  const _transcribe = useCallback(async (audioBlob) => {
    onLoadingChange?.(true)
    setRecordingError('正在识别语音...')
    try {
      const res = await fetch(
        'https://api.deepgram.com/v1/listen?model=nova-2&punctuate=true&paragraphs=true&smart_format=true',
        {
          method: 'POST',
          headers: {
            Authorization: `Token ${deepgramApiKey}`,
            'Content-Type': 'audio/webm',
          },
          body: audioBlob,
        }
      )
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        throw new Error(errBody.err_msg || `语音识别失败: ${res.status}`)
      }

      const data = await res.json()
      const raw  = data.results?.channels?.[0]?.alternatives?.[0]?.transcript

      if (raw?.trim()) {
        setRecordingError('正在优化文本...')
        const processed = postProcess
          ? await postProcess(raw.trim())
          : raw.trim()
        onTranscript?.(processed)
        setRecordingError(null)
      } else {
        setRecordingError('未能识别到语音内容，请重试')
      }
    } catch (err) {
      console.error('[useSpeechInput] transcribe error:', err)
      setRecordingError(err.message || '语音识别失败，请检查网络连接')
    } finally {
      onLoadingChange?.(false)
    }
  }, [deepgramApiKey, postProcess, onTranscript, onLoadingChange])

  // ── startRecording ─────────────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    setRecordingError(null)
    audioChunksRef.current = []

    if (!navigator.mediaDevices?.getUserMedia) {
      setRecordingError('您的浏览器不支持录音功能，请使用 Chrome、Safari 或 Edge 浏览器')
      return
    }
    if (
      window.location.protocol !== 'https:' &&
      window.location.hostname !== 'localhost'
    ) {
      setRecordingError('录音功能需要 HTTPS 安全连接。请确保网址以 https:// 开头')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        clearInterval(recordingTimerRef.current)
        setRecordingSeconds(0)
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        await _transcribe(blob)
        stream.getTracks().forEach(t => t.stop())
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
      setRecordingSeconds(0)

      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds(prev => {
          if (prev + 1 >= MAX_RECORDING_SECONDS) {
            stopRecording()             // eslint-disable-line no-use-before-define
            return MAX_RECORDING_SECONDS
          }
          return prev + 1
        })
      }, 1000)
    } catch (err) {
      console.error('[useSpeechInput] start error:', err)

      let errorMsg = '无法访问麦克风'
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        if (isWeChat) {
          errorMsg = '【微信限制】请点击右上角「···」→「在Safari/浏览器中打开」'
        } else if (isIOS && isSafari) {
          errorMsg = '【iOS Safari】设置：①打开「设置」→「Safari」→「麦克风」→开启 ②或刷新页面在弹窗中点击「允许」'
        } else if (isIOS && /Chrome|CriOS/i.test(ua)) {
          errorMsg = '【iOS Chrome】打开「设置」→「Chrome」→开启「麦克风」权限'
        } else if (isAndroid) {
          errorMsg = '【Android】点击地址栏左侧「ⓘ」图标，找到麦克风选项并允许'
        } else {
          errorMsg = '【权限被拒绝】刷新页面，在弹窗中点击「允许」，或检查浏览器设置中的麦克风权限'
        }
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errorMsg = '【未找到麦克风】请检查麦克风已连接且系统已授权'
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        errorMsg = '【麦克风被占用】请关闭微信语音通话、会议等应用'
      } else if (err.name === 'SecurityError') {
        errorMsg = '【安全限制】录音功能必须使用 HTTPS。请确保网址以 https:// 开头'
      } else if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost') {
        errorMsg = '【连接不安全】录音需要 HTTPS 加密连接'
      } else if (err.message?.toLowerCase().includes('permission')) {
        if (isWeChat) {
          errorMsg = '【微信限制】请点击右上角「···」→「在Safari/浏览器中打开」后使用录音'
        } else if (isIOS) {
          errorMsg = '【iOS设置】打开「设置」→「隐私与安全性」→「麦克风」→找到浏览器并开启'
        } else {
          errorMsg = '【权限被拒绝】请刷新页面，在弹出的权限请求中点击「允许」'
        }
      }

      setRecordingError(errorMsg)
    }
  }, [_transcribe, isWeChat, isIOS, isSafari, isAndroid, ua])

  // ── stopRecording ──────────────────────────────────────────────────────────
  const stopRecording = useCallback(() => {
    clearInterval(recordingTimerRef.current)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setIsRecording(false)
  }, [])

  return {
    // State
    isRecording,
    recordingSeconds,
    recordingError,
    setRecordingError,
    // Browser flags
    isWeChat,
    isIOS,
    isSafari,
    isAndroid,
    // Constants
    maxRecordingSeconds: MAX_RECORDING_SECONDS,
    // Refs
    recordingDelayRef,
    // Actions
    startRecording,
    stopRecording,
  }
}
