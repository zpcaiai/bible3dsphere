// 圣徒相通 — WebSocket connection hook (presence + signaling + chat transport).
import { useCallback, useEffect, useRef, useState } from 'react'
import { buildWsUrl } from './realtimeApi'
import { getToken } from '../auth'

/**
 * Maintains a single auto-reconnecting WebSocket to /api/ws/rtc.
 * @param {(msg:object)=>void} onMessage  called for every server message
 * @param {boolean} enabled  only connect when true (e.g. user logged in)
 */
export function useRealtime(onMessage, enabled = true) {
  const wsRef = useRef(null)
  const handlerRef = useRef(onMessage)
  const reconnectRef = useRef(null)
  const attemptsRef = useRef(0)
  const closedByUs = useRef(false)
  const [connected, setConnected] = useState(false)

  handlerRef.current = onMessage

  const send = useCallback((obj) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj))
      return true
    }
    return false
  }, [])

  useEffect(() => {
    if (!enabled || !getToken()) return undefined
    closedByUs.current = false

    function connect() {
      let ws
      try {
        ws = new WebSocket(buildWsUrl())
      } catch (e) {
        scheduleReconnect()
        return
      }
      wsRef.current = ws

      ws.onopen = () => {
        attemptsRef.current = 0
        setConnected(true)
      }
      ws.onmessage = (ev) => {
        let msg
        try { msg = JSON.parse(ev.data) } catch { return }
        handlerRef.current?.(msg)
      }
      ws.onclose = () => {
        setConnected(false)
        if (!closedByUs.current) scheduleReconnect()
      }
      ws.onerror = () => {
        try { ws.close() } catch (e) { /* noop */ }
      }
    }

    function scheduleReconnect() {
      attemptsRef.current += 1
      const delay = Math.min(15000, 1000 * 2 ** Math.min(attemptsRef.current, 4))
      reconnectRef.current = setTimeout(connect, delay)
    }

    connect()

    return () => {
      closedByUs.current = true
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      const ws = wsRef.current
      if (ws) {
        try { ws.close() } catch (e) { /* noop */ }
      }
      wsRef.current = null
      setConnected(false)
    }
  }, [enabled])

  return { connected, send }
}
