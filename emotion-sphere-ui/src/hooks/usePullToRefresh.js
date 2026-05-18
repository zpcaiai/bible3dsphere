import { useRef, useState, useEffect } from 'react'

export default function usePullToRefresh(onRefresh, containerRef) {
  const [pulling, setPulling] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)

  // Keep latest callback in ref so event handlers never go stale
  const onRefreshRef = useRef(onRefresh)
  useEffect(() => { onRefreshRef.current = onRefresh }, [onRefresh])

  const startY = useRef(0)
  const currentY = useRef(0)
  const isPulling = useRef(false)
  const isRefreshing = useRef(false)
  const THRESHOLD = 60

  useEffect(() => {
    const el = containerRef?.current || null
    if (!el) return

    function getScrollTop() {
      return el.scrollTop
    }

    function onTouchStart(e) {
      if (isRefreshing.current) return
      if (getScrollTop() <= 1) {
        startY.current = e.touches[0].clientY
        isPulling.current = true
      }
    }

    function onTouchMove(e) {
      if (!isPulling.current || isRefreshing.current) return
      currentY.current = e.touches[0].clientY
      const dy = currentY.current - startY.current
      if (dy > 5) {
        // Damped distance
        const dist = Math.min(dy * 0.45, 110)
        setPulling(true)
        setPullDistance(dist)
      } else if (dy < -5) {
        // User is scrolling down — abort pull
        isPulling.current = false
        setPulling(false)
        setPullDistance(0)
      }
    }

    async function onTouchEnd() {
      if (!isPulling.current || isRefreshing.current) return
      isPulling.current = false
      const dy = currentY.current - startY.current
      const dist = Math.min(dy * 0.45, 110)
      if (dist >= THRESHOLD && onRefreshRef.current) {
        isRefreshing.current = true
        setRefreshing(true)
        setPullDistance(THRESHOLD)
        try {
          await onRefreshRef.current()
        } finally {
          isRefreshing.current = false
          setRefreshing(false)
        }
      }
      setPulling(false)
      setPullDistance(0)
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: true })
    el.addEventListener('touchend', onTouchEnd)
    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
    }
  }, [containerRef])

  const indicatorStyle = {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    display: pulling || refreshing ? 'flex' : 'none',
    justifyContent: 'center',
    alignItems: 'center',
    height: `${pullDistance}px`,
    transition: pulling ? 'none' : 'height 0.2s ease',
    background: 'rgba(0,0,0,0.4)',
    backdropFilter: 'blur(6px)',
    color: 'rgba(255,255,255,0.85)',
    fontSize: '13px',
    fontWeight: 500,
    overflow: 'hidden',
    pointerEvents: 'none',
  }

  const indicatorText = refreshing
    ? '⟳ 刷新中...'
    : pullDistance >= THRESHOLD
      ? '↑ 松手刷新'
      : '↓ 下拉刷新'

  return { pulling, refreshing, pullDistance, indicatorStyle, indicatorText }
}
