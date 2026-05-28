import { useEffect, useState } from 'react'
import { fetchRecycleBin, restoreRecycleItem } from './api'
import { getToken } from './auth'

const TYPE_ICONS = {
  prayer: '🙏',
  evangelism: '🌍',
  devotion: '📖',
  personal: '📔',
  sermon: '📜',
}

function daysLeft(deletedAtStr) {
  if (!deletedAtStr) return 0
  const deleted = new Date(deletedAtStr)
  const now = new Date()
  const diffMs = 30 * 86400000 - (now.getTime() - deleted.getTime())
  return Math.max(0, Math.ceil(diffMs / 86400000))
}

export default function RecycleBinPage({ onBack }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [restoringId, setRestoringId] = useState(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const token = getToken()
      const data = await fetchRecycleBin(token)
      setItems(data.items || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleRestore(item) {
    setRestoringId(`${item.type}-${item.id}`)
    try {
      const token = getToken()
      await restoreRecycleItem(item.type, item.id, token)
      setItems(prev => prev.filter(i => !(i.type === item.type && i.id === item.id)))
    } catch (e) {
      alert('恢复失败: ' + e.message)
    } finally {
      setRestoringId(null)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%)',
      color: 'rgba(255,255,255,0.9)',
      padding: '0 0 80px',
    }}>
      {/* Header */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 10,
        background: 'rgba(10,10,26,0.92)',
        backdropFilter: 'blur(12px)',
        padding: '12px 16px',
        display: 'flex', alignItems: 'center', gap: '12px',
        borderBottom: '1px solid rgba(255,255,255,0.08)',
      }}>
        <button
          onClick={onBack}
          style={{
            background: 'none', border: 'none',
            color: 'rgba(255,255,255,0.7)', fontSize: '20px',
            cursor: 'pointer', padding: '4px',
          }}
        >
          ←
        </button>
        <span style={{ fontSize: '17px', fontWeight: 600 }}>🗑️ 回收站</span>
        <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginLeft: 'auto' }}>
          删除后30天自动清除
        </span>
      </div>

      {/* Content */}
      <div style={{ padding: '12px 16px' }}>
        {loading && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'rgba(255,255,255,0.5)' }}>
            加载中...
          </div>
        )}

        {error && (
          <div style={{ textAlign: 'center', padding: '20px', color: '#ff6b6b' }}>
            {error}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div style={{
            textAlign: 'center', padding: '60px 20px',
            color: 'rgba(255,255,255,0.4)',
          }}>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>🗑️</div>
            <div style={{ fontSize: '15px' }}>回收站为空</div>
            <div style={{ fontSize: '12px', marginTop: '8px' }}>删除的内容会在这里保留30天</div>
          </div>
        )}

        {items.map(item => {
          const key = `${item.type}-${item.id}`
          const remaining = daysLeft(item.deleted_at)
          const isRestoring = restoringId === key
          return (
            <div
              key={key}
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '12px',
                padding: '14px 16px',
                marginBottom: '10px',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <span style={{ fontSize: '24px', flexShrink: 0 }}>
                {TYPE_ICONS[item.type] || '📄'}
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px',
                }}>
                  <span style={{
                    fontSize: '10px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: 'rgba(94,92,230,0.2)',
                    color: '#a5a3ff',
                    fontWeight: 600,
                  }}>
                    {item.type_label}
                  </span>
                  <span style={{
                    fontSize: '10px',
                    color: remaining <= 3 ? '#ff6b6b' : 'rgba(255,255,255,0.35)',
                  }}>
                    {remaining > 0 ? `${remaining}天后清除` : '即将清除'}
                  </span>
                </div>
                <div style={{
                  fontSize: '14px',
                  color: 'rgba(255,255,255,0.8)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}>
                  {item.title}
                </div>
                {item.subtitle && (
                  <div style={{
                    fontSize: '11px',
                    color: 'rgba(255,255,255,0.35)',
                    marginTop: '2px',
                  }}>
                    {item.subtitle}
                  </div>
                )}
              </div>
              <button
                onClick={() => handleRestore(item)}
                disabled={isRestoring}
                style={{
                  flexShrink: 0,
                  padding: '8px 14px',
                  fontSize: '12px',
                  fontWeight: 600,
                  background: isRestoring ? 'rgba(255,255,255,0.05)' : 'rgba(52,199,89,0.15)',
                  border: '1px solid rgba(52,199,89,0.3)',
                  borderRadius: '8px',
                  color: '#34c759',
                  cursor: isRestoring ? 'not-allowed' : 'pointer',
                  opacity: isRestoring ? 0.5 : 1,
                }}
              >
                {isRestoring ? '⏳' : '♻️ 恢复'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
