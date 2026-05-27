import { useRef, useState } from 'react'
import { fetchTranslate } from './api'

export default function TranslatableParagraph({ children, className, style }) {
  const [translation, setTranslation] = useState(null)
  const [translating, setTranslating] = useState(false)
  const [menuVisible, setMenuVisible] = useState(false)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })
  const longPressTimer = useRef(null)
  const containerRef = useRef(null)

  const text = typeof children === 'string' ? children : ''

  function showMenu(x, y) {
    setMenuPos({ x, y })
    setMenuVisible(true)
  }

  function hideMenu() {
    setMenuVisible(false)
  }

  function handleContextMenu(e) {
    e.preventDefault()
    showMenu(e.clientX, e.clientY)
  }

  function handleTouchStart(e) {
    const touch = e.touches[0]
    longPressTimer.current = setTimeout(() => {
      showMenu(touch.clientX, touch.clientY)
    }, 600)
  }

  function handleTouchEnd() {
    clearTimeout(longPressTimer.current)
  }

  function handleTouchMove() {
    clearTimeout(longPressTimer.current)
  }

  async function doTranslate() {
    hideMenu()
    if (!text.trim() || translating) return
    setTranslating(true)
    setTranslation(null)
    try {
      const result = await fetchTranslate(text, 'en')
      setTranslation(result)
    } catch (err) {
      setTranslation(`[Translation failed: ${err.message}]`)
    } finally {
      setTranslating(false)
    }
  }

  function dismissTranslation() {
    setTranslation(null)
  }

  return (
    <span ref={containerRef} style={{ display: 'block', position: 'relative' }}>
      <p
        className={className}
        style={style}
        onContextMenu={handleContextMenu}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onTouchMove={handleTouchMove}
      >
        {children}
      </p>

      {translating && (
        <p className={className} style={{ ...style, opacity: 0.5, fontStyle: 'italic', textIndent: '2em' }}>
          正在翻译...
        </p>
      )}

      {translation && (
        <p
          className={className}
          style={{
            ...style,
            color: 'rgba(180,200,255,0.85)',
            fontSize: '13px',
            borderLeft: '2px solid rgba(100,150,255,0.4)',
            paddingLeft: '10px',
            marginTop: '4px',
            textIndent: '0',
          }}
        >
          {translation}
          <button
            onClick={dismissTranslation}
            style={{
              display: 'inline-block',
              marginLeft: '8px',
              background: 'none',
              border: 'none',
              color: 'rgba(180,200,255,0.5)',
              cursor: 'pointer',
              fontSize: '12px',
              padding: '0',
              verticalAlign: 'middle',
            }}
            title="关闭译文"
          >
            ✕
          </button>
        </p>
      )}

      {menuVisible && (
        <>
          <div
            onClick={hideMenu}
            style={{
              position: 'fixed', inset: 0, zIndex: 9998,
            }}
          />
          <div
            style={{
              position: 'fixed',
              left: Math.min(menuPos.x, window.innerWidth - 160),
              top: Math.min(menuPos.y, window.innerHeight - 60),
              zIndex: 9999,
              background: 'rgba(30,30,40,0.97)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
              overflow: 'hidden',
              minWidth: '140px',
            }}
          >
            <button
              onClick={doTranslate}
              style={{
                display: 'block',
                width: '100%',
                padding: '12px 16px',
                background: 'none',
                border: 'none',
                color: '#fff',
                fontSize: '14px',
                textAlign: 'left',
                cursor: 'pointer',
                letterSpacing: '0.02em',
              }}
            >
              🌐 转为英文
            </button>
          </div>
        </>
      )}
    </span>
  )
}
