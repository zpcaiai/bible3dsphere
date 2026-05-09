import { useRef, useState, useCallback, useEffect } from 'react'

export default function usePullToRefresh(onRefresh, containerRef) {
  const [pulling, setPulling] = useState(false)
  const [pullDistance, setPullDistance] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef(0)
  const isPulling = useRef(false)
  const THRESHOLD = 60

  const handleTouchStart = useCallback((e) => {
    const el = containerRef?.current || document.scrollingElement || document.documentElement
    const scrollTop = el === document.scrollingElement || el === document.documentElement
      ? window.scrollY || document.documentElement.scrollTop
      : el.scrollTop
    if (scrollTop <= 0) {
      startY.current = e.touches[0].clientY
      isPulling.current = true
    }
  }, [containerRef])

  const handleTouchMove = useCallback((e) => {
    if (!isPulling.current) return
    const dy = e.touches[0].clientY - startY.current
    if (dy > 0) {
      setPulling(true)
      setPullDistance(Math.min(dy * 0.5, 100))
    } else {
      isPulling.current = false
      setPulling(false)
      setPullDistance(0)
    }
  }, [])

  const handleTouchEnd = useCallback(async () => {
    if (!isPulling.current) return
    isPulling.current = false
    if (pullDistance >= THRESHOLD && onRefresh) {
      setRefreshing(true)
      setPullDistance(THRESHOLD)
      try {
        await onRefresh()
      } finally {
        setRefreshing(false)
      }
    }
    setPulling(false)
    setPullDistance(0)
  }, [pullDistance, onRefresh])

  useEffect(() => {
    const el = containerRef?.current || window
    el.addEventListener('touchstart', handleTouchStart, { passive: true })
    el.addEventListener('touchmove', handleTouchMove, { passive: true })
    el.addEventListener('touchend', handleTouchEnd)
    return () => {
      el.removeEventListener('touchstart', handleTouchStart)
      el.removeEventListener('touchmove', handleTouchMove)
      el.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleTouchStart, handleTouchMove, handleTouchEnd, containerRef])

  const indicatorStyle = {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    display: pulling || refreshing ? 'flex' : 'none',
    justifyContent: 'center',
    alignItems: 'center',
    height: `${pullDistance}px`,
    transition: pulling ? 'none' : 'height 0.2s ease',
    background: 'rgba(0,0,0,0.3)',
    backdropFilter: 'blur(4px)',
    color: 'rgba(255,255,255,0.8)',
    fontSize: '13px',
    overflow: 'hidden',
  }

  const indicatorText = refreshing
    ? '刷新中...'
    : pullDistance >= THRESHOLD
      ? '松手刷新'
      : '下拉刷新'

  return { pulling, refreshing, pullDistance, indicatorStyle, indicatorText }
}
