/**
 * Tests for useSpeechInput hook.
 * Uses vi.stubGlobal to mock navigator APIs and fetch.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useSpeechInput } from '../hooks/useSpeechInput'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeMediaRecorderMock () {
  const mock = {
    start: vi.fn(),
    stop: vi.fn(),
    state: 'inactive',
    ondataavailable: null,
    onstop: null,
  }
  mock.start.mockImplementation(() => { mock.state = 'recording' })
  mock.stop.mockImplementation(() => {
    mock.state = 'inactive'
    mock.onstop?.()
  })
  return mock
}

function makeStreamMock () {
  return { getTracks: () => [{ stop: vi.fn() }] }
}

function makeDeepgramResponse (transcript) {
  return {
    ok: true,
    json: async () => ({
      results: {
        channels: [{
          alternatives: [{ transcript }],
          detected_language: 'zh',
        }],
      },
    }),
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('useSpeechInput', () => {
  let mediaRecorderMock
  let streamMock

  beforeEach(() => {
    vi.useFakeTimers()
    mediaRecorderMock = makeMediaRecorderMock()
    streamMock = makeStreamMock()

    vi.stubGlobal('MediaRecorder', vi.fn(() => mediaRecorderMock))
    vi.stubGlobal('Blob', class MockBlob {
      constructor (parts, opts) { this.type = opts?.type }
    })

    vi.stubGlobal('navigator', {
      userAgent: 'TestBrowser/1.0',
      mediaDevices: {
        getUserMedia: vi.fn(async () => streamMock),
      },
    })

    Object.defineProperty(window, 'location', {
      value: { protocol: 'https:', hostname: 'test.local' },
      writable: true,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('initial state: not recording, no error, 0 seconds', () => {
    const { result } = renderHook(() => useSpeechInput({}))
    expect(result.current.isRecording).toBe(false)
    expect(result.current.recordingSeconds).toBe(0)
    expect(result.current.recordingError).toBeNull()
  })

  it('browser detection — isWeChat true when UA contains MicroMessenger', () => {
    vi.stubGlobal('navigator', { userAgent: 'Mozilla/5.0 MicroMessenger/8.0' })
    const { result } = renderHook(() => useSpeechInput({}))
    expect(result.current.isWeChat).toBe(true)
  })

  it('startRecording sets isRecording = true', async () => {
    const { result } = renderHook(() => useSpeechInput({}))

    await act(async () => { await result.current.startRecording() })

    expect(result.current.isRecording).toBe(true)
    expect(mediaRecorderMock.start).toHaveBeenCalledOnce()
  })

  it('stopRecording sets isRecording = false', async () => {
    const { result } = renderHook(() => useSpeechInput({}))

    await act(async () => { await result.current.startRecording() })
    expect(result.current.isRecording).toBe(true)

    act(() => { result.current.stopRecording() })
    expect(result.current.isRecording).toBe(false)
  })

  it('timer increments recordingSeconds each second', async () => {
    const { result } = renderHook(() => useSpeechInput({}))

    await act(async () => { await result.current.startRecording() })

    act(() => { vi.advanceTimersByTime(3000) })
    expect(result.current.recordingSeconds).toBe(3)
  })

  it('onTranscript called with Deepgram result after stop', async () => {
    const onTranscript = vi.fn()
    const fakeFetch = vi.fn(async () => makeDeepgramResponse('我感到很平安'))
    vi.stubGlobal('fetch', fakeFetch)

    const { result } = renderHook(() =>
      useSpeechInput({ deepgramApiKey: 'test-key', onTranscript })
    )

    await act(async () => { await result.current.startRecording() })
    // Simulate data + stop
    act(() => { mediaRecorderMock.ondataavailable?.({ data: { size: 10 } }) })
    await act(async () => { mediaRecorderMock.onstop?.() })

    // Let async work settle
    await act(async () => {})

    expect(onTranscript).toHaveBeenCalledWith('我感到很平安')
  })

  it('sets recordingError when getUserMedia is denied', async () => {
    vi.stubGlobal('navigator', {
      userAgent: 'TestBrowser',
      mediaDevices: {
        getUserMedia: vi.fn(async () => {
          const err = new Error('denied')
          err.name = 'NotAllowedError'
          throw err
        }),
      },
    })

    const { result } = renderHook(() => useSpeechInput({}))
    await act(async () => { await result.current.startRecording() })

    expect(result.current.recordingError).toContain('权限被拒绝')
  })

  it('postProcess callback transforms transcript before onTranscript', async () => {
    const onTranscript = vi.fn()
    const postProcess = vi.fn(async (raw) => `[processed] ${raw}`)
    vi.stubGlobal('fetch', vi.fn(async () => makeDeepgramResponse('hello world')))

    const { result } = renderHook(() =>
      useSpeechInput({ deepgramApiKey: 'key', onTranscript, postProcess })
    )

    await act(async () => { await result.current.startRecording() })
    act(() => { mediaRecorderMock.ondataavailable?.({ data: { size: 5 } }) })
    await act(async () => { mediaRecorderMock.onstop?.() })
    await act(async () => {})

    expect(postProcess).toHaveBeenCalledWith('hello world')
    expect(onTranscript).toHaveBeenCalledWith('[processed] hello world')
  })

  it('maxRecordingSeconds is 120', () => {
    const { result } = renderHook(() => useSpeechInput({}))
    expect(result.current.maxRecordingSeconds).toBe(120)
  })
})
