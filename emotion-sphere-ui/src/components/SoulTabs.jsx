/**
 * SoulTabs - 心迹 Tab 导航组件
 *
 * 重设计：
 *  - 移除「行为追踪」tab（合并入灵修操练）
 *  - 「习惯养成」→「灵修操练」
 */

export default function SoulTabs({ activeTab, onTabChange }) {
  const tabs = [
    { key: 'dashboard',   label: '今日心镜', emoji: '🪞' },
    { key: 'personality', label: '人格塑造', emoji: '🔮' },
    { key: 'habits',      label: '灵修操练', emoji: '🌱' },
    { key: 'new',         label: '决策支持', emoji: '⚖️' },
  ]

  return (
    <div style={{
      display: 'flex',
      gap: '6px',
      padding: '10px 12px',
      borderBottom: '1px solid rgba(255,255,255,0.08)',
      background: 'rgba(13,17,23,0.92)',
      backdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
      overflowX: 'auto',
    }}>
      {tabs.map(tab => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          style={{
            flex: 1,
            minWidth: 60,
            padding: '8px 6px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === tab.key
              ? 'rgba(52,199,89,0.18)'
              : 'rgba(255,255,255,0.05)',
            color: activeTab === tab.key ? '#34c759' : 'rgba(255,255,255,0.5)',
            fontSize: '11px',
            fontWeight: activeTab === tab.key ? 700 : 400,
            cursor: 'pointer',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '3px',
            transition: 'all 0.15s',
            outline: 'none',
          }}
        >
          <span style={{ fontSize: '16px' }}>{tab.emoji}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )
}
