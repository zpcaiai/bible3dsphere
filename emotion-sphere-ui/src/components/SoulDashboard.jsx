/**
 * SoulDashboard - 心迹仪表盘组件
 * 整合人格塑造、习惯养成、行为追踪、决策支持的全景视图
 * 提取自 DecisionSupportPage 的 renderDashboard 函数
 */

import { useEffect, useState } from 'react'
import { API_BASE, fetchFormationProfile } from '../api'
import { getToken } from '../auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`

const dimensionColors = {
  humility: '#4ade80',
  fear_tendency: '#f87171',
  pride_tendency: '#fb923c',
  emotional_stability: '#60a5fa',
  truth_alignment: '#a78bfa',
  relational_health: '#f472b6',
  resilience: '#2dd4bf',
  spiritual_clarity: '#fbbf24'
}

const dimensionNames = {
  humility: '谦逊',
  fear_tendency: '恐惧倾向',
  pride_tendency: '骄傲倾向',
  emotional_stability: '情绪稳定',
  truth_alignment: '真理对齐',
  relational_health: '关系健康',
  resilience: '韧性',
  spiritual_clarity: '灵性清晰'
}

export default function SoulDashboard({ user }) {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDashboardData() {
      try {
        setLoading(true)
        const token = getToken()
        const uid = user?.id || user?.userId
        if (!uid) {
          setLoading(false)
          return
        }

        // 并行加载所有数据
        const [profileData, habitsDash, behaviorHist] = await Promise.all([
          fetchFormationProfile(uid, token).catch(() => null),
          fetch(`${API_BASE}/habits/dashboard`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${API_BASE}/behavior/history?user_id=${uid}&limit=10`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then(r => r.ok ? r.json() : null).catch(() => null)
        ])

        // 加载近期决策历史
        const decisionsRes = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(uid), {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => null)
        const decisionsData = decisionsRes?.ok ? await decisionsRes.json() : []

        setDashboardData({
          formation: profileData?.profile || null,
          habits: habitsDash,
          behavior: behaviorHist?.items || [],
          decisions: decisionsData.slice(0, 5)
        })
      } catch (err) {
        console.error('[Dashboard] load error:', err)
      } finally {
        setLoading(false)
      }
    }

    loadDashboardData()
  }, [user])

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
        <div style={{ fontSize: '32px', marginBottom: '16px' }}>📊</div>
        <div>加载心迹仪表盘...</div>
      </div>
    )
  }

  const { formation, habits, behavior, decisions } = dashboardData || {}
  const stateVector = formation?.state_vector || {}
  const trajectory = formation?.trajectory_direction || 'unknown'
  const arc = formation?.formation_arc || 'unknown'

  return (
    <div style={{ padding: '16px' }}>
      {/* 头部概览 */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(59,130,246,0.2) 100%)',
        borderRadius: '16px',
        padding: '20px',
        marginBottom: '20px',
        border: '1px solid rgba(139,92,246,0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <span style={{ fontSize: '36px' }}>📊</span>
          <div>
            <div style={{ fontSize: '18px', fontWeight: 600, color: '#fff' }}>心迹仪表盘</div>
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.5)' }}>人格 · 习惯 · 行为 · 决策 全景视图</div>
          </div>
        </div>

        {/* 核心指标卡片 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
          {/* 人格塑造 */}
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>🔮</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#c4b5fd' }}>
              {formation ? arc.replace(/_/g, ' ') : '暂无数据'}
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>形成弧线</div>
          </div>

          {/* 习惯养成 */}
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>🪙</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#ffd700' }}>
              {habits?.token_balance || 0}
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>代币余额</div>
          </div>

          {/* 行为追踪 */}
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>🔥</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#ff6b35' }}>
              {habits?.current_streak || 0}天
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>当前连胜</div>
          </div>

          {/* 决策支持 */}
          <div style={{
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '12px',
            padding: '16px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>⚖️</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: '#60a5fa' }}>
              {decisions?.length || 0}
            </div>
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>近期决策</div>
          </div>
        </div>
      </div>

      {/* 8维性格轨迹 */}
      {formation && (
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '20px'
        }}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>
            🎯 八维性格轨迹
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
            {Object.entries(dimensionNames).map(([key, name]) => {
              const score = stateVector[key] || 0.5
              const color = dimensionColors[key]
              return (
                <div key={key} style={{
                  background: 'rgba(0,0,0,0.2)',
                  borderRadius: '10px',
                  padding: '12px',
                  borderLeft: `3px solid ${color}`
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>{name}</span>
                    <span style={{ fontSize: '13px', fontWeight: 600, color }}>{(score * 100).toFixed(0)}%</span>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${score * 100}%`, height: '100%', background: color, borderRadius: '3px' }} />
                  </div>
                </div>
              )
            })}
          </div>
          <div style={{ marginTop: '12px', fontSize: '11px', color: 'rgba(255,255,255,0.4)', textAlign: 'center' }}>
            轨迹方向: {trajectory.replace(/_/g, ' ')} · 数据点数: {formation?.data_points || 0}
          </div>
        </div>
      )}

      {/* 电路层级统计 */}
      {behavior && behavior.length > 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '20px'
        }}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>
            🎯 电路层级统计 (近10次)
          </div>
          {['Green', 'Yellow', 'Red'].map(tier => {
            const count = behavior.filter(b => b.tier_executed === tier).length
            const total = behavior.length
            const pct = total > 0 ? (count / total) * 100 : 0
            const colors = { Green: '#22c55e', Yellow: '#eab308', Red: '#ef4444' }
            return (
              <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                <div style={{ width: '80px', fontSize: '13px', color: colors[tier], fontWeight: 600 }}>{tier} 电路</div>
                <div style={{ flex: 1, height: '24px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: colors[tier], borderRadius: '4px' }} />
                </div>
                <div style={{ width: '60px', textAlign: 'right', fontSize: '13px', color: '#fff' }}>{count} ({pct.toFixed(0)}%)</div>
              </div>
            )
          })}
        </div>
      )}

      {/* 近期决策 */}
      {decisions && decisions.length > 0 && (
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '16px',
          padding: '20px'
        }}>
          <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '16px' }}>
            📜 近期决策记录
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {decisions.slice(0, 5).map((d, i) => (
              <div key={i} style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '8px',
                padding: '12px',
                borderLeft: `3px solid ${d.status === 'completed' ? '#22c55e' : '#3b82f6'}`
              }}>
                <div style={{ fontSize: '13px', color: '#fff', fontWeight: 500, marginBottom: '4px' }}>{d.title}</div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
                  {new Date(d.created_at).toLocaleDateString('zh-CN')} · {d.category}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
