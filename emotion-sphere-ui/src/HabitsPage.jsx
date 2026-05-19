import { useState, useEffect } from 'react'
import { useHabitsList, useHabitsDashboard, useCreateHabit, useExecuteHabit, useLogHabitExecution } from './hooks/usePsychology'

/**
 * 人格塑造、习惯养成、行为追踪页面
 * 从 emotion-sphere 项目移植的 L0-L4 心理学引擎
 */

// 能量等级对应的emoji和颜色
const ENERGY_LEVELS = [
  { value: 1, emoji: '🔴', label: '极低', color: '#ff3b30', desc: '身心俱疲，仅可做1分钟行动' },
  { value: 2, emoji: '🟠', label: '低', color: '#ff9500', desc: '精力有限，建议60秒原子动作' },
  { value: 3, emoji: '🟡', label: '中等', color: '#ffcc00', desc: '正常状态，标准执行' },
  { value: 4, emoji: '🟢', label: '高', color: '#34c759', desc: '状态良好，完整执行' },
  { value: 5, emoji: '🔵', label: '充沛', color: '#007aff', desc: '巅峰状态，高质量执行' },
]

const TIER_INFO = {
  Red: { label: 'Red熔断', color: '#ff3b30', desc: '60秒原子动作，防崩溃保护' },
  Yellow: { label: 'Yellow标准', color: '#ffcc00', desc: '正常执行' },
  Green: { label: 'Green完整', color: '#34c759', desc: '高质量完整执行' },
}

export default function HabitsPage({ user, token, embedded = false }) {
  const [activeTab, setActiveTab] = useState('habits') // habits, dashboard, create, execute
  const [selectedHabit, setSelectedHabit] = useState(null)
  const [energyLevel, setEnergyLevel] = useState(3)
  const [moodBefore, setMoodBefore] = useState(5)
  const [moodAfter, setMoodAfter] = useState(5)
  const [executionResult, setExecutionResult] = useState(null)
  const [showAntiGuilt, setShowAntiGuilt] = useState(false)

  // 表单状态
  const [newHabitName, setNewHabitName] = useState('')
  const [newHabitAnchor, setNewHabitAnchor] = useState('')

  // React Query hooks
  const { data: habitsData, isLoading: habitsLoading } = useHabitsList(token)
  const { data: dashboardData, isLoading: dashboardLoading } = useHabitsDashboard(token)
  const createHabitMutation = useCreateHabit(token)
  const executeHabitMutation = useExecuteHabit(token)
  const logHabitMutation = useLogHabitExecution(token)

  const habits = habitsData?.items || []
  const dashboard = dashboardData || { active_habits: 0, token_balance: 0, current_streak: 0, today_executions: 0 }

  // 创建新习惯
  const handleCreateHabit = async (e) => {
    e.preventDefault()
    if (!newHabitName.trim()) return

    try {
      await createHabitMutation.mutateAsync({
        habitName: newHabitName,
        anchor: newHabitAnchor,
        energyLevel
      })
      setNewHabitName('')
      setNewHabitAnchor('')
      setActiveTab('habits')
    } catch (err) {
      console.error('创建习惯失败:', err)
    }
  }

  // 执行习惯
  const handleExecuteHabit = async (habit) => {
    setSelectedHabit(habit)
    setActiveTab('execute')
    setExecutionResult(null)
    setShowAntiGuilt(false)

    try {
      const result = await executeHabitMutation.mutateAsync({
        habitId: habit.id,
        energyLevel
      })
      setExecutionResult(result)
      
      // 如果是Red Tier，显示防羞耻消息
      if (result.selected_tier === 'Red') {
        setShowAntiGuilt(true)
      }
    } catch (err) {
      console.error('执行习惯失败:', err)
    }
  }

  // 记录执行结果
  const handleLogExecution = async (wasCompleted) => {
    if (!selectedHabit || !executionResult) return

    try {
      await logHabitMutation.mutateAsync({
        habitId: selectedHabit.id,
        tierExecuted: executionResult.selected_tier,
        wasCompleted,
        completionPercentage: wasCompleted ? 100 : 0,
        moodBefore,
        moodAfter
      })
      
      // 重置状态并返回习惯列表
      setSelectedHabit(null)
      setExecutionResult(null)
      setShowAntiGuilt(false)
      setActiveTab('dashboard')
    } catch (err) {
      console.error('记录执行失败:', err)
    }
  }

  // 渲染标签导航
  const renderTabs = () => (
    <div style={{
      display: 'flex',
      gap: '8px',
      padding: '12px 16px',
      borderBottom: '1px solid rgba(255,255,255,0.1)',
      overflowX: 'auto',
    }}>
      {[
        { key: 'dashboard', label: '仪表盘', emoji: '📊' },
        { key: 'habits', label: '我的习惯', emoji: '🌱' },
        { key: 'create', label: '新建习惯', emoji: '➕' },
      ].map(tab => (
        <button
          key={tab.key}
          onClick={() => {
            setActiveTab(tab.key)
            setSelectedHabit(null)
            setExecutionResult(null)
          }}
          style={{
            padding: '8px 16px',
            borderRadius: '20px',
            border: 'none',
            background: activeTab === tab.key ? '#007aff' : 'rgba(120,120,128,0.2)',
            color: activeTab === tab.key ? '#fff' : 'rgba(255,255,255,0.7)',
            fontSize: '14px',
            fontWeight: 500,
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            transition: 'all 0.2s',
          }}
        >
          {tab.emoji} {tab.label}
        </button>
      ))}
    </div>
  )

  // 渲染仪表盘
  const renderDashboard = () => (
    <div style={{ padding: '16px' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: '12px',
        marginBottom: '20px'
      }}>
        <div style={statCardStyle}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🪙</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#ffd700' }}>
            {dashboard.token_balance || 0}
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>代币余额</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔥</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#ff6b35' }}>
            {dashboard.current_streak || 0}
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>当前连胜</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🌱</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#34c759' }}>
            {dashboard.active_habits || 0}
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>活跃习惯</div>
        </div>
        <div style={statCardStyle}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>✅</div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#007aff' }}>
            {dashboard.today_executions || 0}
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>今日执行</div>
        </div>
      </div>

      {/* 能量等级快速选择 */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>⚡ 当前能量等级</div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {ENERGY_LEVELS.map(level => (
            <button
              key={level.value}
              onClick={() => setEnergyLevel(level.value)}
              style={{
                padding: '12px 16px',
                borderRadius: '12px',
                border: 'none',
                background: energyLevel === level.value ? level.color : 'rgba(120,120,128,0.2)',
                color: '#fff',
                fontSize: '14px',
                fontWeight: energyLevel === level.value ? 600 : 400,
                cursor: 'pointer',
                flex: '1 1 calc(33% - 8px)',
                minWidth: '80px',
              }}
            >
              <div style={{ fontSize: '20px', marginBottom: '4px' }}>{level.emoji}</div>
              <div>{level.label}</div>
              <div style={{ fontSize: '10px', opacity: 0.8, marginTop: '4px' }}>{level.value}/5</div>
            </button>
          ))}
        </div>
        <div style={{ marginTop: '12px', fontSize: '12px', color: 'rgba(255,255,255,0.6)', textAlign: 'center' }}>
          {ENERGY_LEVELS.find(e => e.value === energyLevel)?.desc}
        </div>
      </div>

      {/* 三层电路保护说明 */}
      <div style={sectionStyle}>
        <div style={sectionTitleStyle}>🛡️ 三层电路保护系统</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {Object.entries(TIER_INFO).map(([key, info]) => (
            <div key={key} style={{
              padding: '12px',
              borderRadius: '10px',
              background: 'rgba(255,255,255,0.05)',
              borderLeft: `3px solid ${info.color}`,
            }}>
              <div style={{ fontSize: '14px', fontWeight: 600, color: info.color }}>{info.label}</div>
              <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginTop: '4px' }}>{info.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )

  // 渲染习惯列表
  const renderHabits = () => (
    <div style={{ padding: '16px' }}>
      {habitsLoading ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'rgba(255,255,255,0.6)' }}>
          加载中...
        </div>
      ) : habits.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🌱</div>
          <div style={{ fontSize: '16px', color: 'rgba(255,255,255,0.8)', marginBottom: '8px' }}>
            还没有习惯
          </div>
          <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.5)', marginBottom: '20px' }}>
            创建一个习惯，开始你的人格塑造之旅
          </div>
          <button
            onClick={() => setActiveTab('create')}
            style={{
              padding: '12px 24px',
              borderRadius: '10px',
              border: 'none',
              background: '#007aff',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            ➕ 创建第一个习惯
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {habits.map(habit => (
            <div
              key={habit.id}
              style={{
                padding: '16px',
                borderRadius: '14px',
                background: 'rgba(255,255,255,0.08)',
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '4px' }}>
                    {habit.habit_name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
                    锚点: {habit.anchor || '未设置'}
                  </div>
                </div>
                {habit.current_streak > 0 && (
                  <div style={{
                    padding: '4px 10px',
                    borderRadius: '12px',
                    background: 'rgba(255,107,53,0.2)',
                    color: '#ff6b35',
                    fontSize: '12px',
                    fontWeight: 600,
                  }}>
                    🔥 {habit.current_streak}
                  </div>
                )}
              </div>
              
              <div style={{ display: 'flex', gap: '8px', fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '12px' }}>
                <span>执行: {habit.total_executions || 0}次</span>
                {habit.last_execution && (
                  <span>上次: {new Date(habit.last_execution).toLocaleDateString('zh-CN')}</span>
                )}
              </div>
              
              <button
                onClick={() => handleExecuteHabit(habit)}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: '#34c759',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                ▶️ 执行习惯
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  // 渲染创建习惯表单
  const renderCreateForm = () => (
    <div style={{ padding: '16px' }}>
      <form onSubmit={handleCreateHabit}>
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '14px', color: 'rgba(255,255,255,0.8)', marginBottom: '8px' }}>
            习惯名称 *
          </label>
          <input
            type="text"
            value={newHabitName}
            onChange={(e) => setNewHabitName(e.target.value)}
            placeholder="例如：晨间祷告、阅读圣经、运动..."
            style={{
              width: '100%',
              padding: '14px 16px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.2)',
              background: 'rgba(255,255,255,0.05)',
              color: '#fff',
              fontSize: '16px',
              outline: 'none',
            }}
            required
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', fontSize: '14px', color: 'rgba(255,255,255,0.8)', marginBottom: '8px' }}>
            确定性锚点 (可选)
          </label>
          <input
            type="text"
            value={newHabitAnchor}
            onChange={(e) => setNewHabitAnchor(e.target.value)}
            placeholder="例如：早晨刷牙后、喝完咖啡后..."
            style={{
              width: '100%',
              padding: '14px 16px',
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.2)',
              background: 'rgba(255,255,255,0.05)',
              color: '#fff',
              fontSize: '16px',
              outline: 'none',
            }}
          />
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '8px' }}>
            锚点是你每天都会做的固定动作，用来触发新习惯
          </div>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{ display: 'block', fontSize: '14px', color: 'rgba(255,255,255,0.8)', marginBottom: '12px' }}>
            当前能量等级
          </label>
          <div style={{ display: 'flex', gap: '8px' }}>
            {ENERGY_LEVELS.map(level => (
              <button
                key={level.value}
                type="button"
                onClick={() => setEnergyLevel(level.value)}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: energyLevel === level.value ? level.color : 'rgba(120,120,128,0.2)',
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: energyLevel === level.value ? 600 : 400,
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: '18px' }}>{level.emoji}</div>
                <div style={{ fontSize: '11px', marginTop: '4px' }}>{level.label}</div>
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          disabled={!newHabitName.trim() || createHabitMutation.isLoading}
          style={{
            width: '100%',
            padding: '16px',
            borderRadius: '12px',
            border: 'none',
            background: createHabitMutation.isLoading ? 'rgba(120,120,128,0.4)' : '#007aff',
            color: '#fff',
            fontSize: '16px',
            fontWeight: 600,
            cursor: createHabitMutation.isLoading ? 'not-allowed' : 'pointer',
          }}
        >
          {createHabitMutation.isLoading ? '创建中...' : '✨ 创建习惯'}
        </button>
      </form>

      {/* 说明卡片 */}
      <div style={{ marginTop: '24px', padding: '16px', borderRadius: '12px', background: 'rgba(0,122,255,0.1)', border: '1px solid rgba(0,122,255,0.2)' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: '#007aff', marginBottom: '8px' }}>💡 基于 B.J. Fogg 行为模型</div>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
          系统会根据你的能量等级自动选择执行层级：<br/>
          <strong>Green (高能量)</strong> - 完整执行，获得10代币<br/>
          <strong>Yellow (中等)</strong> - 标准执行，获得5代币<br/>
          <strong>Red (低能量)</strong> - 60秒原子动作，获得1代币，防崩溃保护
        </div>
      </div>
    </div>
  )

  // 渲染执行界面
  const renderExecute = () => {
    if (!selectedHabit) return null

    return (
      <div style={{ padding: '16px' }}>
        {/* 防羞耻消息 */}
        {showAntiGuilt && (
          <div style={{
            padding: '16px',
            borderRadius: '12px',
            background: 'rgba(255,59,48,0.15)',
            border: '1px solid rgba(255,59,48,0.3)',
            marginBottom: '16px',
          }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#ff3b30', marginBottom: '8px' }}>
              🛡️ 系统状态通知
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.9)', lineHeight: 1.6 }}>
              系统状态：高负荷。执行已路由至 <strong>Red Tier</strong>。<br/>
              连胜保持。核心控制回路完整性：<strong>100%</strong>。<br/>
              这不是失败，是智能调节。
            </div>
          </div>
        )}

        {/* 习惯信息 */}
        <div style={{
          padding: '20px',
          borderRadius: '16px',
          background: 'linear-gradient(135deg, rgba(52,199,89,0.2) 0%, rgba(0,122,255,0.2) 100%)',
          marginBottom: '20px',
        }}>
          <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '4px' }}>正在执行</div>
          <div style={{ fontSize: '22px', fontWeight: 700, color: '#fff' }}>{selectedHabit.habit_name}</div>
          {selectedHabit.anchor && (
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginTop: '4px' }}>
              锚点: {selectedHabit.anchor}
            </div>
          )}
        </div>

        {/* 执行结果 */}
        {executionResult ? (
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              padding: '20px',
              borderRadius: '16px',
              background: 'rgba(255,255,255,0.08)',
              border: '2px solid ' + TIER_INFO[executionResult.selected_tier].color,
              marginBottom: '16px',
            }}>
              <div style={{
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: '12px',
                background: TIER_INFO[executionResult.selected_tier].color,
                color: '#fff',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '12px',
              }}>
                {TIER_INFO[executionResult.selected_tier].label}
              </div>
              
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '8px' }}>
                推荐行动
              </div>
              <div style={{ fontSize: '15px', color: 'rgba(255,255,255,0.9)', lineHeight: 1.5 }}>
                {executionResult.action_to_execute}
              </div>
              
              <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)' }}>代币奖励</span>
                  <span style={{ fontSize: '20px', fontWeight: 700, color: '#ffd700' }}>🪙 {executionResult.token_yield}</span>
                </div>
              </div>
            </div>

            {/* 心情记录 */}
            <div style={{ marginBottom: '20px' }}>
              <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.8)', marginBottom: '12px' }}>心情记录 (1-10)</div>
              <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>执行前</label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={moodBefore}
                    onChange={(e) => setMoodBefore(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                  <div style={{ textAlign: 'center', fontSize: '14px', color: '#fff', marginTop: '4px' }}>{moodBefore}</div>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ display: 'block', fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginBottom: '8px' }}>执行后</label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={moodAfter}
                    onChange={(e) => setMoodAfter(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                  <div style={{ textAlign: 'center', fontSize: '14px', color: '#fff', marginTop: '4px' }}>{moodAfter}</div>
                </div>
              </div>
            </div>

            {/* 完成按钮 */}
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => handleLogExecution(false)}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: '12px',
                  border: '1px solid rgba(255,255,255,0.2)',
                  background: 'transparent',
                  color: 'rgba(255,255,255,0.7)',
                  fontSize: '14px',
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                ⏸️ 未完成
              </button>
              <button
                onClick={() => handleLogExecution(true)}
                disabled={logHabitMutation.isLoading}
                style={{
                  flex: 2,
                  padding: '14px',
                  borderRadius: '12px',
                  border: 'none',
                  background: '#34c759',
                  color: '#fff',
                  fontSize: '14px',
                  fontWeight: 600,
                  cursor: logHabitMutation.isLoading ? 'not-allowed' : 'pointer',
                }}
              >
                {logHabitMutation.isLoading ? '记录中...' : '✅ 已完成'}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '40px', color: 'rgba(255,255,255,0.6)' }}>
            正在生成执行计划...
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ 
      flex: 1, 
      display: 'flex', 
      flexDirection: 'column',
      background: '#1c1c1e',
      minHeight: '100%',
    }}>
      {renderTabs()}
      
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'dashboard' && renderDashboard()}
        {activeTab === 'habits' && renderHabits()}
        {activeTab === 'create' && renderCreateForm()}
        {activeTab === 'execute' && renderExecute()}
      </div>
    </div>
  )
}

// 样式对象
const statCardStyle = {
  padding: '16px',
  borderRadius: '16px',
  background: 'rgba(255,255,255,0.08)',
  textAlign: 'center',
}

const sectionStyle = {
  padding: '16px',
  borderRadius: '14px',
  background: 'rgba(255,255,255,0.05)',
  marginBottom: '16px',
}

const sectionTitleStyle = {
  fontSize: '14px',
  fontWeight: 600,
  color: 'rgba(255,255,255,0.8)',
  marginBottom: '12px',
}
