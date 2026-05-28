/**
 * SoulTabs - 心迹 Tab 导航组件
 * 提取自 DecisionSupportPage 的 renderTabs 函数
 */

export default function SoulTabs({ activeTab, onTabChange }) {
  const tabs = [
    { key: 'dashboard', label: '心迹仪表盘', emoji: '📊' },
    { key: 'personality', label: '人格塑造', emoji: '🔮' },
    { key: 'habits', label: '习惯养成', emoji: '🌱' },
    { key: 'behavior', label: '行为追踪', emoji: '📈' },
    { key: 'new', label: '决策支持', emoji: '⚖️' },
  ]

  return (
    <div style={{
      display: 'flex',
      gap: '8px',
      padding: '12px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.1)',
      background: 'rgba(28,28,30,0.8)',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      {tabs.map(tab => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          style={{
            flex: 1,
            padding: '10px 12px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === tab.key ? '#007aff' : 'rgba(120,120,128,0.2)',
            color: activeTab === tab.key ? '#fff' : 'rgba(255,255,255,0.6)',
            fontSize: '12px',
            fontWeight: 500,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '4px',
          }}
        >
          <span>{tab.emoji}</span>
          <span>{tab.label}</span>
        </button>
      ))}
    </div>
  )
}
