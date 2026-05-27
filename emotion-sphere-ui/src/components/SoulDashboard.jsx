/**
 * SoulDashboard - 心迹仪表盘组件
 * 整合人格塑造、习惯养成、行为追踪、决策支持的全景视图
 * 提取自 DecisionSupportPage 的 renderDashboard 函数
 */

import { useEffect, useState } from 'react'
import { API_BASE, fetchFormationProfile } from '../api'
import { getToken } from '../auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`
const MVFE_BASE = API_BASE + '/mvfe'

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

const EMOTION_NAMES = {
  anxiety:'焦虑', peace:'平静', hope:'盼望', sadness:'悲伤',
  anger:'愤怒', fear:'恐惧', joy:'喜乐', love:'爱',
  shame:'羞耻', guilt:'内疚', disgust:'厌恶', surprise:'惊讶',
  gratitude:'感恩', envy:'嫉妒', loneliness:'孤独', unknown:'未知',
}

const C = {
  anxiety:'#ffa94d', peace:'#4facfe', hope:'#51cf66', sadness:'#748ffc',
  anger:'#ff6b6b', fear:'#da77f2', joy:'#ffd43b', love:'#ff8787',
  shame:'#9775fa', guilt:'#63e6be', disgust:'#8ce99a', surprise:'#74c0fc',
  gratitude:'#ffec99', envy:'#ffa8a8', loneliness:'#bac8ff', unknown:'#868e96',
}

const FOCUS_NAMES = {
  work:'工作', career:'职业', relationship:'关系', self:'自我', future:'未来',
  money:'金钱', finance:'财务', health:'健康', family:'家庭', past:'过去',
  spirituality:'灵性', identity:'身份', other:'其他', unknown:'未知',
}

const LOOP_LABELS = {
  '恐惧-回避回路': {label:'恐惧-回避回路', color:'#ff6b6b', desc:'反复用逃避来应对恐惧，导致恐惧感不断加深'},
  '骄傲-认可回路': {label:'骄傲-认可回路', color:'#ffa94d', desc:'依赖外部认可强化自我价值，形成持续比较'},
  '羞耻-隐藏回路': {label:'羞耻-隐藏回路', color:'#da77f2', desc:'用隐藏和压抑来应对羞耻，导致自我认知扭曲'},
  '恐惧-控制回路': {label:'恐惧-控制回路', color:'#ff6b6b', desc:'通过控制周遭来缓解恐惧，但控制需求不断扩大'},
  '骄傲-比较回路': {label:'骄傲-比较回路', color:'#ffa94d', desc:'用与他人比较建立自我感，产生嫉妒或自大'},
  '羞耻-回避回路': {label:'羞耻-回避回路', color:'#da77f2', desc:'隐藏真实自我，越藏越孤立'},
  '欲望-冲动回路': {label:'欲望-冲动回路', color:'#ff3b30', desc:'短暂满足后欲望反弹，形成强迫性冲动'},
  '真理-稳定回路': {label:'真理-稳定回路', color:'#51cf66', desc:'以真理为锚，情绪趋于稳定和开放'},
}

const DESIRE_LABELS = {
  connection: '连接', safety: '安全', control: '掌控', validation: '认可',
  recognition: '被看见', hiding: '隐藏', approval: '被接纳', '麻木': '麻木',
  '寻求解脱': '寻求解脱', '隐藏': '隐藏', '寻求认可': '寻求认可',
}

const BELIEF_LABELS = {
  pursuit_brings_fulfillment: '追求带来满足', avoidance_prevents_harm: '回避避免伤害',
  self_worth_requires_achievement: '自我价值需要成就', i_am_not_enough: '我做得不够好',
  connection_is_impossible: '连接是不可能的', '我做得不够好': '我做得不够好',
  '连接是不可能的': '连接是不可能的',
}

export default function SoulDashboard({ user }) {
  const [dashboardData, setDashboardData] = useState(null)
  const [mvfeData, setMvfeData] = useState(null)
  const [mvfeLastResult, setMvfeLastResult] = useState(null)
  const [selectedDecision, setSelectedDecision] = useState(null)
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

        // 并行加载所有数据（包括 MVFE 灵镜数据）
        const [profileData, habitsDash, behaviorHist, mvfeDash, mvfeLast] = await Promise.all([
          fetchFormationProfile(uid, token).catch(() => null),
          fetch(`${API_BASE}/habits/dashboard`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${API_BASE}/behavior/history?user_id=${uid}&limit=10`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${MVFE_BASE}/dashboard/state?user_id=${uid}&hours=168`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${MVFE_BASE}/last-result/${encodeURIComponent(uid)}`).then(r => r.ok ? r.json() : null).catch(() => null)
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

        setMvfeData(mvfeDash)
        setMvfeLastResult(mvfeLast?.result || null)
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
          padding: '20px',
          marginBottom: '20px'
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

      {/* 灵镜观心 - HIDOS 人格形成动态观测仪 */}
      {(mvfeData || mvfeLastResult) && (() => {
        const d = mvfeData || {}
        const hasDashboardData = (d.data_points || 0) > 0
        const hasLastResult = !!mvfeLastResult
        const latest = hasDashboardData
          ? (d.formation_curve || [])[d.formation_curve.length - 1]
          : (hasLastResult ? {
              formation_score: mvfeLastResult?.formation?.formation_score || 0,
              drift_score: mvfeLastResult?.formation?.drift_score || 0,
              stability_score: mvfeLastResult?.formation?.stability_score || 0,
            } : null)
        const latestDrivers = mvfeLastResult?.decision?.drivers
          || (d.decision_flow?.length ? d.decision_flow[d.decision_flow.length - 1].drivers : {})
          || { fear: 0, ego: 0, love: 0 }
        const latestDecisionType = mvfeLastResult?.decision?.type
          || (d.decision_flow?.length ? d.decision_flow[d.decision_flow.length - 1].type : 'avoidance')
          || 'avoidance'

        return (
        <div style={{
          background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(236,72,153,0.15) 100%)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '20px',
          border: '1px solid rgba(139,92,246,0.2)'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>🔮</span>
              <span>灵镜观心</span>
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
              🧬 HIDOS 人格形成动态观测仪
              {d.is_mock && <span style={{ color: '#ffa94d', marginLeft: 8 }}>⚡ 预览数据</span>}
            </div>
          </div>

          <div style={mvfeStyles.grid4}>
            <Kpi icon="🎭" label="情绪" v={EMOTION_NAMES[mvfeLastResult?.emotion?.primary_emotion] || mvfeLastResult?.emotion?.primary_emotion || '—'}
              sub={(mvfeLastResult?.emotion?.secondary_emotions || []).slice(0,2).map(e => EMOTION_NAMES[e] || e).join('， ') || ''} color={C[mvfeLastResult?.emotion?.primary_emotion] || '#868e96'} />
            <Kpi icon="👁" label="注意力" v={FOCUS_NAMES[mvfeLastResult?.attention?.focus] || mvfeLastResult?.attention?.focus || '—'}
              sub={'固化 ' + ((mvfeLastResult?.attention?.fixation_score || 0) * 100).toFixed(2) + '%'} color="#4facfe" />
            <Kpi icon="⚖️" label="决策" v={latestDecisionType === 'approach' ? '趋近' : '回避'}
              sub={'恐惧 ' + ((latestDrivers?.fear || 0) * 100).toFixed(2) + '%'} color={latestDecisionType === 'approach' ? '#51cf66' : '#ff6b6b'} />
            <Kpi icon="🧬" label="形成度" v={latest ? (latest.formation_score * 100).toFixed(2) + '%' : '—'}
              sub={'漂移 ' + ((latest?.drift_score || 0) * 100).toFixed(2) + '%'} color="#ffa94d" />
          </div>

          <div style={mvfeStyles.grid2}>
            <Card t="形成度仪表盘" i="🧭"><Gauge score={latest?.formation_score || 0} drift={latest?.drift_score || 0} stab={latest?.stability_score || 0}/></Card>
            <Card t="决策驱动因素" i="🔥"><Drivers d={latestDrivers}/></Card>
          </div>
          <div style={mvfeStyles.grid2}>
            <Card t="情绪时间线" i="📈"><EmoChart data={d.emotion_series || []}/></Card>
            <Card t="注意力分配" i="🎯"><AttBars data={d.attention_map || (mvfeLastResult?.attention ? {[FOCUS_NAMES[mvfeLastResult.attention.focus] || mvfeLastResult.attention.focus]: mvfeLastResult.attention.fixation_score} : {})}/></Card>
          </div>
          <Card t="实时因果链" i="🔗"><Chain r={mvfeLastResult}/></Card>
          <div style={mvfeStyles.grid2}>
            <Card t="灵镜洞察" i="💡"><Insight r={mvfeLastResult}/></Card>
            <Card t="形成回路检测" i="🔄"><LoopCard g={mvfeLastResult?.graph_insight} hasResult={!!mvfeLastResult}/></Card>
          </div>
          <Card t="决策模式流" i="⚖️"><DecFlow data={d.decision_flow || []} onSelect={setSelectedDecision}/></Card>
          {selectedDecision && <DecisionDetailModal decision={selectedDecision} onClose={() => setSelectedDecision(null)}/>}
          <div style={{fontSize:9,color:'rgba(255,255,255,0.15)',textAlign:'center',padding:8,lineHeight:1.6}}>本仪表盘仅展示观测性模式，不构成心理诊断、人格评估或行为处方。</div>
        </div>
        )
      })()}
    </div>
  )
}

// ===== MVFE 子组件 =====
function Card({t,i,children}){
  return <div style={mvfeStyles.card}><div style={{display:'flex',alignItems:'center',gap:6,marginBottom:10}}><span style={{fontSize:14}}>{i}</span><span style={{fontSize:12,fontWeight:700,color:'rgba(255,255,255,0.85)'}}>{t}</span></div><div>{children}</div></div>
}
function Kpi({icon,label,v,sub,color}){
  return <div style={mvfeStyles.kpi}><div style={{fontSize:20,marginBottom:4}}>{icon}</div><div style={{fontSize:10,color:'rgba(255,255,255,0.35)',marginBottom:2}}>{label}</div><div style={{fontSize:14,fontWeight:700,color}}>{v}</div>{sub&&<div style={{fontSize:9,color:'rgba(255,255,255,0.3)',marginTop:2}}>{sub}</div>}</div>
}
function Gauge({score,drift,stab}){
  const pct=Math.max(0,Math.min(1,score))*100, dpct=Math.max(0,Math.min(1,drift))*100
  const r=42,cx=56,cy=56,circ=2*Math.PI*r,off=circ*(1-pct/100)
  return <div style={{display:'flex',alignItems:'center',gap:14}}>
    <svg viewBox="0 0 112 80" style={{width:110,flexShrink:0}}>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round"/>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="#4facfe" strokeWidth="8" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={off}/>
      <text x={cx} y={cy+5} fill="#fff" fontSize="16" fontWeight="700" textAnchor="middle">{pct.toFixed(2)}</text>
      <text x={cx} y={cy+18} fill="rgba(255,255,255,0.3)" fontSize="7" textAnchor="middle">形成度</text>
    </svg>
    <div style={{flex:1,display:'flex',flexDirection:'column',gap:6}}>
      <Bar l="形成度" v={pct} c="#4facfe"/>
      <Bar l="漂移信号" v={dpct} c={dpct>30?'#ff6b6b':'#ffa94d'}/>
      <Bar l="稳定性" v={(stab*100).toFixed(2)} c="#51cf66"/>
    </div>
  </div>
}
function Bar({l,v,c}){
  return <div><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:10,color:'rgba(255,255,255,0.4)'}}>{l}</span><span style={{fontSize:10,color:c,fontWeight:600}}>{v}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:Math.min(100,Math.max(0,v))+'%',height:'100%',borderRadius:3,background:c,transition:'width 0.8s ease'}}/></div></div>
}
function Drivers({d}){
  const items=[{k:'fear',l:'恐惧驱动',c:'#ff6b6b',e:'😨'},{k:'ego',l:'自我驱动',c:'#ffa94d',e:'🦅'},{k:'love',l:'关系驱动',c:'#ff8787',e:'❤️'}]
  return <div style={{display:'flex',flexDirection:'column',gap:10}}>{items.map(({k,l,c,e})=>{
    const v=(d[k]||0)*100
    return <div key={k} style={{display:'flex',alignItems:'center',gap:8}}><span style={{fontSize:14,width:20,textAlign:'center'}}>{e}</span><div style={{flex:1}}><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{l}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{v.toFixed(2)}%</span></div><div style={{height:8,borderRadius:4,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:v.toFixed(2)+'%',height:'100%',borderRadius:4,background:c,opacity:0.85,transition:'width 0.8s ease'}}/></div></div></div>
  })}</div>
}
function EmoChart({data}){
  if(!data||data.length<2) return <div style={mvfeStyles.noData}>暂无历史数据</div>
  const w=280,h=100,pl=10,pr=10,pt=8,pb=18,cw=w-pl-pr,ch=h-pt-pb,n=data.length
  const x=i=>pl+(i/(n-1))*cw, y=v=>pt+(1-v)*ch
  return <svg viewBox={"0 0 "+w+" "+h} style={{width:'100%',height:'auto'}}>
    {[0,0.5,1].map(t=><line key={t} x1={pl} y1={y(t)} x2={w-pr} y2={y(t)} stroke="rgba(255,255,255,0.05)" strokeWidth="1" strokeDasharray="2,2"/>)}
    {data.map((d,i)=><g key={i}><text x={x(i)} y={y(d.intensity||0.5)-8} fill={C[d.primary_emotion]||'#868e96'} fontSize="3.5" textAnchor="middle" opacity="0.9">{EMOTION_NAMES[d.primary_emotion]||d.primary_emotion||''}</text><circle cx={x(i)} cy={y(d.intensity||0.5)} r="4" fill={C[d.primary_emotion]||'#868e96'} opacity="0.9"/><circle cx={x(i)} cy={y(d.intensity||0.5)} r="7" fill="none" stroke={C[d.primary_emotion]||'#868e96'} opacity="0.25" strokeWidth="1"/></g>)}
    {data.slice(0,n-1).map((d,i)=><line key={i} x1={x(i)} y1={y(d.intensity||0.5)} x2={x(i+1)} y2={y(data[i+1].intensity||0.5)} stroke="rgba(255,255,255,0.1)" strokeWidth="1.5"/>)}
    <text x={pl} y={h-4} fill="rgba(255,255,255,0.2)" fontSize="7" textAnchor="start">{data[0].timestamp?new Date(data[0].timestamp).toLocaleDateString('zh-CN',{month:'short',day:'numeric'}):''}</text>
    <text x={w-pr} y={h-4} fill="rgba(255,255,255,0.2)" fontSize="7" textAnchor="end">{data[n-1].timestamp?new Date(data[n-1].timestamp).toLocaleDateString('zh-CN',{month:'short',day:'numeric'}):''}</text>
  </svg>
}
function AttBars({data}){
  const e=Object.entries(data).sort((a,b)=>b[1]-a[1])
  if(e.length===0) return <div style={mvfeStyles.noData}>暂无数据</div>
  const mx=Math.max(...e.map(x=>x[1]),0.01)
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>{e.slice(0,5).map(([focus,val])=>{
    const pct=(val/mx)*100, c=val>0.3?'#ff6b6b':val>0.15?'#ffa94d':'#4facfe'
    const label=FOCUS_NAMES[focus]||focus
    return <div key={focus}><div style={{display:'flex',justifyContent:'space-between',marginBottom:2}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{label}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{(val*100).toFixed(2)}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.04)',overflow:'hidden'}}><div style={{width:pct+'%',height:'100%',borderRadius:3,background:c,opacity:0.8,transition:'width 0.6s'}}/></div></div>
  })}</div>
}
function Chain({r}){
  if(!r) return <div style={mvfeStyles.noData}>提交分析后显示实时因果链</div>
  const em=r.emotion||{}, at=r.attention||{}, de=r.decision||{}, fo=r.formation||{}
  const nodes=[
    {l:EMOTION_NAMES[em.primary_emotion]||em.primary_emotion||'情绪',v:((em.intensity||0)*100).toFixed(2)+'%',c:C[em.primary_emotion]||'#ffa94d',s:(em.secondary_emotions||[]).slice(0,2).map(e=>EMOTION_NAMES[e]||e).join('， ')||''},
    {l:FOCUS_NAMES[at.focus]||at.focus||'注意力',v:((at.fixation_score||0)*100).toFixed(2)+'% 固化',c:'#4facfe',s:'漂移 '+((at.drift_risk||0)*100).toFixed(2)+'%'},
    {l:de.type==='approach'?'趋近':'回避',v:'恐惧 '+((de.drivers?.fear||0)*100).toFixed(2)+'%',c:de.type==='approach'?'#51cf66':'#ff6b6b',s:'自我 '+((de.drivers?.ego||0)*100).toFixed(2)+'%'},
    {l:'形成',v:((fo.formation_score||0)*100).toFixed(2)+'%',c:'#ffa94d',s:'漂移 '+((fo.drift_score||0)*100).toFixed(2)+'%'},
  ]
  return <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap',justifyContent:'center',padding:'4px 0'}}>{nodes.map((n,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:6}}><div style={{padding:'8px 12px',borderRadius:10,background:n.c+'15',border:'1px solid '+n.c+'40',textAlign:'center',minWidth:72}}><div style={{fontSize:10,color:'rgba(255,255,255,0.4)',marginBottom:2}}>{n.l}</div><div style={{fontSize:12,fontWeight:700,color:n.c}}>{n.v}</div>{n.s&&<div style={{fontSize:8,color:'rgba(255,255,255,0.25)',marginTop:1}}>{n.s}</div>}</div>{i<nodes.length-1&&<span style={{fontSize:16,color:'rgba(255,255,255,0.1)'}}>→</span>}</div>)}</div>
}
function Insight({r}){
  if(!r) return <div style={mvfeStyles.noData}>暂无洞察</div>
  const ref=r.reflection||{}
  
  const interpretation = ref.state_interpretation 
    || (r.emotion?.primary_emotion && r.attention?.focus 
      ? `系统检测到${EMOTION_NAMES[r.emotion.primary_emotion]||r.emotion.primary_emotion}情绪，注意力聚焦于${FOCUS_NAMES[r.attention.focus]||r.attention.focus}。`
      : null)
    || '暂无状态解读'
  
  const loopInfo = ref.loop_detection 
    || (r.graph_insight?.loop_detected 
      ? `检测到${r.graph_insight.loop_type||'形成回路'}` 
      : null)
  
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>
    <div style={{fontSize:12,color:'rgba(255,255,255,0.75)',lineHeight:1.7}}>{interpretation}</div>
    {loopInfo && !loopInfo.includes('未检测到明显回路') && <div style={{fontSize:11,color:'#ffa94d',padding:'6px 10px',borderRadius:8,background:'rgba(255,169,77,0.06)',borderLeft:'2px solid rgba(255,169,77,0.4)'}}>🔄 {loopInfo}</div>}
    <div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(79,172,254,0.05)',borderLeft:'2px solid rgba(79,172,254,0.25)'}}>
      <span style={{fontSize:10,color:'#4facfe',fontWeight:600}}>💡 反射问题</span>
      <div style={{fontSize:13,color:'#a0d4f7',fontStyle:'italic',marginTop:5}}>{ref.reflective_question||'此刻，什么在你里面最活跃？'}</div>
    </div>
    {ref.bible_verse_hint && <div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(255,193,7,0.05)',borderLeft:'2px solid rgba(255,193,7,0.25)'}}>
      <span style={{fontSize:10,color:'#ffc107',fontWeight:600}}>📖 应许锚点</span>
      <div style={{fontSize:12,color:'rgba(255,255,255,0.7)',marginTop:5,lineHeight:1.6}}>{ref.bible_verse_hint}</div>
    </div>}
  </div>
}
function LoopCard({g, hasResult}){
  if (!hasResult) return (
    <div style={{textAlign:'center',padding:'20px 10px'}}>
      <div style={{fontSize:24,marginBottom:8}}>🔬</div>
      <div style={{fontSize:11,color:'rgba(255,255,255,0.3)'}}>完成一次灵镜分析后显示回路检测结果</div>
    </div>
  )
  if(!g||!g.loop_detected) return (
    <div style={{textAlign:'center',padding:'20px 10px'}}>
      <div style={{fontSize:28,marginBottom:8}}>✅</div>
      <div style={{fontSize:12,color:'#51cf66',fontWeight:600}}>未检测到形成回路</div>
      <div style={{fontSize:11,color:'rgba(255,255,255,0.3)',marginTop:4}}>当前状态相对开放，无明显闭环</div>
    </div>
  )
  const meta = LOOP_LABELS[g.loop_type] || {label: g.loop_type || '检测到形成回路', color:'#ffa94d', desc:''}
  const strength = parseFloat(((g.loop_strength||0)*100).toFixed(2))
  return (
    <div style={{display:'flex',flexDirection:'column',gap:10}}>
      <div style={{display:'flex',alignItems:'center',gap:8}}>
        <span style={{fontSize:16}}>⚠️</span>
        <span style={{fontSize:13,color:meta.color,fontWeight:700}}>{meta.label}</span>
      </div>
      {meta.desc && <div style={{fontSize:11,color:'rgba(255,255,255,0.45)',lineHeight:1.6,padding:'6px 10px',borderRadius:8,background:`${meta.color}10`,borderLeft:`2px solid ${meta.color}40`}}>{meta.desc}</div>}
      <div>
        <div style={{display:'flex',justifyContent:'space-between',fontSize:10,color:'rgba(255,255,255,0.4)',marginBottom:4}}>
          <span>回路强度</span><span style={{color:meta.color,fontWeight:600}}>{strength}%</span>
        </div>
        <div style={{height:6,borderRadius:3,background:'rgba(255,255,255,0.07)',overflow:'hidden'}}>
          <div style={{width:`${strength}%`,height:'100%',borderRadius:3,background:meta.color,transition:'width 0.8s ease'}}/>
        </div>
      </div>
      {g.dominant_desires?.length>0 && <div style={{fontSize:10,color:'rgba(255,255,255,0.35)'}}>核心渴望: {g.dominant_desires.map(d => DESIRE_LABELS[d] || d).join(' · ')}</div>}
      {g.core_beliefs?.length>0 && <div style={{fontSize:10,color:'rgba(255,255,255,0.35)'}}>核心信念: {g.core_beliefs.map(b => BELIEF_LABELS[b] || b).join(' · ')}</div>}
    </div>
  )
}
function DecFlow({data, onSelect}){
  if(!data||data.length===0) return <div style={mvfeStyles.noData}>暂无决策数据</div>
  const total=data.length, avoid=data.filter(d=>d.type==='avoidance').length, app=total-avoid, ar=total>0?avoid/total:0
  let lbl='平衡模式', col='#4facfe'
  if(ar>0.6){lbl='回避主导';col='#ff6b6b'}
  else if(ar<0.4){lbl='趋近主导';col='#51cf66'}
  return <div style={{display:'flex',alignItems:'center',gap:14}}>
    <div style={{flex:1,display:'flex',flexDirection:'column',gap:6}}>
      <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>{[...data].reverse().slice(0,8).map((d,i)=><div key={i} onClick={()=>onSelect&&onSelect(d)} style={{padding:'3px 8px',borderRadius:8,fontSize:10,fontWeight:600,background:d.type==='approach'?'rgba(81,207,102,0.12)':'rgba(255,107,107,0.12)',color:d.type==='approach'?'#51cf66':'#ff6b6b',border:'1px solid '+(d.type==='approach'?'rgba(81,207,102,0.2)':'rgba(255,107,107,0.2)'),cursor:'pointer',transition:'all 0.2s'}} title="点击查看详情">{d.type==='approach'?'→':'↔'}</div>)}</div>
      <div style={{fontSize:11,color:col,fontWeight:600}}>{lbl} — {total} 次决策记录</div>
    </div>
    <div style={{width:80,textAlign:'center'}}>
      <svg viewBox="0 0 80 80" style={{width:70,height:70}}>
        <circle cx="40" cy="40" r="30" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="10"/>
        <circle cx="40" cy="40" r="30" fill="none" stroke="#51cf66" strokeWidth="10" strokeDasharray={2*Math.PI*30*app/total} strokeDashoffset={-2*Math.PI*30*avoid/total} transform="rotate(-90 40 40)"/>
        <circle cx="40" cy="40" r="30" fill="none" stroke="#ff6b6b" strokeWidth="10" strokeDasharray={2*Math.PI*30*avoid/total} transform="rotate(-90 40 40)"/>
        <text x="40" y="43" fill="#fff" fontSize="14" fontWeight="700" textAnchor="middle">{total}</text>
        <text x="40" y="54" fill="rgba(255,255,255,0.3)" fontSize="7" textAnchor="middle">决策</text>
      </svg>
    </div>
  </div>
}
function DecisionDetailModal({ decision, onClose }){
  return (
    <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.6)',backdropFilter:'blur(4px)',zIndex:1000,display:'flex',alignItems:'center',justifyContent:'center',padding:16}} onClick={onClose}>
      <div style={{background:'linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)',borderRadius:16,padding:20,maxWidth:400,width:'100%',border:'1px solid rgba(255,255,255,0.1)'}} onClick={e=>e.stopPropagation()}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
          <div style={{fontSize:16,fontWeight:700,color:'#fff'}}>决策详情</div>
          <button onClick={onClose} style={{background:'none',border:'none',color:'rgba(255,255,255,0.5)',fontSize:20,cursor:'pointer'}}>×</button>
        </div>
        <div style={{display:'flex',flexDirection:'column',gap:12}}>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            <span style={{fontSize:24}}>{decision.type==='approach'?'🟢':'🔴'}</span>
            <div>
              <div style={{fontSize:14,fontWeight:600,color:decision.type==='approach'?'#51cf66':'#ff6b6b'}}>{decision.type==='approach'?'趋近决策':'回避决策'}</div>
              <div style={{fontSize:11,color:'rgba(255,255,255,0.4)'}}>{decision.timestamp?new Date(decision.timestamp).toLocaleString('zh-CN'):''}</div>
            </div>
          </div>
          {decision.drivers && <div style={{padding:12,borderRadius:8,background:'rgba(255,255,255,0.03)'}}>
            <div style={{fontSize:11,color:'rgba(255,255,255,0.5)',marginBottom:8}}>决策驱动</div>
            <div style={{display:'flex',flexDirection:'column',gap:6}}>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:12}}><span style={{color:'#ff6b6b'}}>恐惧</span><span style={{color:'#fff'}}>{((decision.drivers.fear||0)*100).toFixed(1)}%</span></div>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:12}}><span style={{color:'#ffa94d'}}>自我</span><span style={{color:'#fff'}}>{((decision.drivers.ego||0)*100).toFixed(1)}%</span></div>
              <div style={{display:'flex',justifyContent:'space-between',fontSize:12}}><span style={{color:'#ff8787'}}>爱</span><span style={{color:'#fff'}}>{((decision.drivers.love||0)*100).toFixed(1)}%</span></div>
            </div>
          </div>}
        </div>
      </div>
    </div>
  )
}

// MVFE 样式
const mvfeStyles = {
  card: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 12,
    padding: 14,
  },
  kpi: {
    background: 'rgba(255,255,255,0.03)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 10,
    padding: '12px 8px',
    textAlign: 'center',
  },
  grid4: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 8,
    marginBottom: 12,
  },
  grid2: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 12,
    marginBottom: 12,
  },
  noData: {
    textAlign: 'center',
    padding: '20px 10px',
    color: 'rgba(255,255,255,0.3)',
    fontSize: 12,
  },
}
