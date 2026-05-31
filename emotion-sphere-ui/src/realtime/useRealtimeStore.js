// Hooks to consume the singleton realtimeStore from React.
import { useEffect, useRef, useState } from 'react'
import realtimeStore from './realtimeStore'

/** Subscribe to shared state (connected, onlineFriends, incomingCall, activeCall). */
export function useRealtimeState() {
  const [snap, setSnap] = useState(() => realtimeStore.getState())
  useEffect(() => realtimeStore.subscribeState(setSnap), [])
  return snap
}

/** Subscribe to the raw message stream with a stable handler ref. */
export function useRealtimeMessages(handler) {
  const ref = useRef(handler)
  ref.current = handler
  useEffect(() => realtimeStore.subscribe((m) => ref.current?.(m)), [])
}

export { realtimeStore }
