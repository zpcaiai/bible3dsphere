import { useEffect, useRef, useState } from 'react'

const EMOJI_GROUPS = [
  { label: '常用', emojis: ['😀','😂','🥰','😇','🤗','😊','😍','🥺','😢','😭','🙏','❤️','💖','🔥','✨','🌟','💪','👍','👏','🎉','✝️','📖','🕊️','⭐','💡','🌈','☀️','🌙'] },
  { label: '表情', emojis: ['😃','😄','😁','😆','😅','🤣','😊','😌','😏','🤔','🤨','😐','😑','😶','🫡','🤐','😬','😮‍💨','🤥','😌','😴','🤤','😷','🤒','🤕','🤢','🤮','🥴'] },
  { label: '心情', emojis: ['❤️','🧡','💛','💚','💙','💜','🖤','🤍','🤎','💔','❣️','💕','💞','💓','💗','💖','💘','💝','♥️','🫶','🤝','🫂','💒','💐','🌹','🌸','🌺','🌻'] },
  { label: '信仰', emojis: ['✝️','🙏','📖','🕊️','⛪','🕯️','👼','🐑','🍞','🍷','💒','🌿','🫒','🌾','🐟','⚓','🪨','🏔️','🌅','🌄','☁️','🌊','💧','🔔','🎵','🎶','📜','🪶'] },
  { label: '动物', emojis: ['🐶','🐱','🐭','🐹','🐰','🦊','🐻','🐼','🐨','🐯','🦁','🐮','🐷','🐸','🐵','🐔','🐧','🐦','🦅','🦋','🐛','🐝','🐞','🐢','🐠','🐬','🐳','🦀'] },
  { label: '手势', emojis: ['👍','👎','👊','✊','🤛','🤜','👏','🙌','🫶','👐','🤲','🤝','💪','✋','🤚','👋','🤟','✌️','🤞','🫰','🤙','👆','👇','👈','👉','👌','🤏','☝️'] },
]

export default function EmojiTextarea({ value, onChange, rows, placeholder, style, className }) {
  const [showPicker, setShowPicker] = useState(false)
  const [activeGroup, setActiveGroup] = useState(0)
  const textareaRef = useRef(null)
  const pickerRef = useRef(null)

  function insertEmoji(emoji) {
    const ta = textareaRef.current
    if (!ta) {
      onChange(value + emoji)
      return
    }
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const newVal = value.substring(0, start) + emoji + value.substring(end)
    onChange(newVal)
    requestAnimationFrame(() => {
      ta.focus()
      const pos = start + emoji.length
      ta.setSelectionRange(pos, pos)
    })
  }

  useEffect(() => {
    if (!showPicker) return
    function handleClickOutside(e) {
      if (pickerRef.current && !pickerRef.current.contains(e.target)) {
        setShowPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('touchstart', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('touchstart', handleClickOutside)
    }
  }, [showPicker])

  return (
    <div style={{ position: 'relative' }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={e => onChange(e.target.value)}
        rows={rows}
        placeholder={placeholder}
        style={style}
        className={className}
      />
      <button
        type="button"
        onClick={() => setShowPicker(v => !v)}
        style={{
          position: 'absolute',
          right: '8px',
          bottom: '8px',
          background: showPicker ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.06)',
          border: '1px solid rgba(255,255,255,0.12)',
          borderRadius: '6px',
          padding: '4px 8px',
          fontSize: '16px',
          cursor: 'pointer',
          lineHeight: 1,
          color: 'rgba(255,255,255,0.7)',
        }}
        title="插入表情"
      >
        😊
      </button>
      {showPicker && (
        <div
          ref={pickerRef}
          style={{
            position: 'absolute',
            bottom: '100%',
            right: 0,
            marginBottom: '4px',
            width: '280px',
            maxHeight: '220px',
            background: 'rgba(20,20,40,0.98)',
            border: '1px solid rgba(255,255,255,0.15)',
            borderRadius: '12px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            zIndex: 50,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div style={{
            display: 'flex',
            gap: '2px',
            padding: '6px 6px 4px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            overflowX: 'auto',
            flexShrink: 0,
          }}>
            {EMOJI_GROUPS.map((g, i) => (
              <button
                key={g.label}
                type="button"
                onClick={() => setActiveGroup(i)}
                style={{
                  padding: '4px 8px',
                  fontSize: '11px',
                  background: activeGroup === i ? 'rgba(255,255,255,0.15)' : 'transparent',
                  border: 'none',
                  borderRadius: '6px',
                  color: activeGroup === i ? 'rgba(255,255,255,0.9)' : 'rgba(255,255,255,0.45)',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  fontWeight: activeGroup === i ? 600 : 400,
                }}
              >
                {g.label}
              </button>
            ))}
          </div>
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '8px',
            display: 'flex',
            flexWrap: 'wrap',
            gap: '2px',
            alignContent: 'flex-start',
          }}>
            {EMOJI_GROUPS[activeGroup].emojis.map(em => (
              <button
                key={em}
                type="button"
                onClick={() => insertEmoji(em)}
                style={{
                  width: '34px',
                  height: '34px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '20px',
                  background: 'transparent',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                {em}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
