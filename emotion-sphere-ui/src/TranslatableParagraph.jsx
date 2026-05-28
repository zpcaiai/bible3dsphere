import { useRef, useState } from 'react'
import { fetchTranslate } from './api'

const _translationCache = new Map()

export default function TranslatableParagraph({ children, className, style }) {
  const [translation, setTranslation] = useState(null)
  const [translating, setTranslating] = useState(false)
  const [menuVisible, setMenuVisible] = useState(false)
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 })
  const [copied, setCopied] = useState(false)
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
    if (_translationCache.has(text)) {
      setTranslation(_translationCache.get(text))
      return
    }
    setTranslating(true)
    setTranslation(null)
    try {
      const result = await fetchTranslate(text, 'en')
      _translationCache.set(text, result)
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

  async function doCopy(textToCopy) {
    hideMenu()
    try {
      await navigator.clipboard.writeText(textToCopy)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = textToCopy
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const menuBtnStyle = {
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
  }

  const dividerStyle = {
    height: '1px',
    background: 'rgba(255,255,255,0.08)',
    margin: '0 12px',
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

      {copied && (
        <span style={{
          position: 'absolute', top: '-28px', left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(30,30,40,0.92)', color: '#4ade80', fontSize: '12px',
          padding: '4px 10px', borderRadius: '6px', pointerEvents: 'none',
          whiteSpace: 'nowrap', zIndex: 9999,
        }}>
          已复制 ✓
        </span>
      )}

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
          onContextMenu={(e) => { e.preventDefault(); doCopy(translation) }}
          onTouchStart={(e) => {
            const touch = e.touches[0]
            longPressTimer.current = setTimeout(() => doCopy(translation), 600)
          }}
          onTouchEnd={() => clearTimeout(longPressTimer.current)}
          onTouchMove={() => clearTimeout(longPressTimer.current)}
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
            style={{ position: 'fixed', inset: 0, zIndex: 9998 }}
          />
          <div
            style={{
              position: 'fixed',
              left: Math.min(menuPos.x, window.innerWidth - 180),
              top: Math.min(menuPos.y, window.innerHeight - 120),
              zIndex: 9999,
              background: 'rgba(30,30,40,0.97)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '10px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
              overflow: 'hidden',
              minWidth: '160px',
            }}
          >
            <button onClick={() => doCopy(text)} style={menuBtnStyle}>
              📋 复制原文
            </button>
            <div style={dividerStyle} />
            <button onClick={doTranslate} style={menuBtnStyle}>
              🌐 转为英文
            </button>
            {translation && (
              <>
                <div style={dividerStyle} />
                <button onClick={() => doCopy(translation)} style={menuBtnStyle}>
                  📋 复制译文
                </button>
              </>
            )}
          </div>
        </>
      )}
    </span>
  )
}
