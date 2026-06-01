/**
 * SoulDashboard — 今日心镜
 *
 * 重设计：以"今日心镜"为核心，呈现
 *   1. 一句属灵洞见
 *   2. 三个信号（情绪 / 形成方向 / 操练连续）
 *   3. 今日操练建议
 *   4. 八维性格概览（top-3 成长 + top-2 需关注）
 *   5. 灵镜观心 — MVFE 人格动态观测
 */

import { useEffect, useState } from 'react'
import { API_BASE, fetchFormationProfile, fetchWeeklyPastoral } from '../api'
import { getToken } from '../auth'
import IdolatryMonitorPage from '../IdolatryMonitorPage'
import WaitingPathPage from '../WaitingPathPage'
import ExamenPage from '../ExamenPage'
import ReminderSettings from '../ReminderSettings'
import PracticeHubPage from '../PracticeHubPage'
import PlanetHome from '../PlanetHome'
import PilgrimJourneyPage from '../PilgrimJourneyPage'
import FaithHopeLovePage from '../FaithHopeLovePage'
import DecisionDiscernmentPage from '../DecisionDiscernmentPage'
import FuelLibraryPage from '../FuelLibraryPage'
import AgentChatPage from '../AgentChatPage'
import GospelDiagnosticPage from '../GospelDiagnosticPage'
import SpiritualCheckupPage from '../SpiritualCheckupPage'

const MVFE_BASE = API_BASE + '/mvfe'

const DIMS = [
  { key: 'humility',           name: '谦逊',    color: '#4ade80', icon: '🌿', good: true  },
  { key: 'emotional_stability',name: '情绪稳定', color: '#60a5fa', icon: '🌊', good: true  },
  { key: 'truth_alignment',    name: '真理对齐', color: '#a78bfa', icon: '📖', good: true  },
  { key: 'relational_health',  name: '关系健康', color: '#f472b6', icon: '❤️',  good: true  },
  { key: 'resilience',         name: '韧性',    color: '#2dd4bf', icon: '🌳', good: true  },
  { key: 'spiritual_clarity',  name: '灵性清晰', color: '#fbbf24', icon: '✨', good: true  },
  { key: 'fear_tendency',      name: '恐惧倾向', color: '#f87171', icon: '😨', good: false },
  { key: 'pride_tendency',     name: '骄傲倾向', color: '#fb923c', icon: '🦅', good: false },
]

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
  connection:'连接', safety:'安全', control:'掌控', validation:'认可',
  recognition:'被看见', hiding:'隐藏', approval:'被接纳',
  '麻木':'麻木', '寻求解脱':'寻求解脱', '隐藏':'隐藏', '寻求认可':'寻求认可',
}
const BELIEF_LABELS = {
  pursuit_brings_fulfillment:'追求带来满足', avoidance_prevents_harm:'回避避免伤害',
  self_worth_requires_achievement:'自我价值需要成就', i_am_not_enough:'我做得不够好',
  connection_is_impossible:'连接是不可能的', '我做得不够好':'我做得不够好',
  '连接是不可能的':'连接是不可能的',
}

function deriveInsight({ formation, mvfeLastResult, habits }) {
  const sv = formation?.state_vector || {}
  const arc = formation?.formation_arc || ''
  const traj = formation?.trajectory_direction || ''
  const streak = habits?.current_streak || 0
  const lastEmo = mvfeLastResult?.emotion?.primary_emotion
  const drift = mvfeLastResult?.formation?.drift_score || 0
  const loopDetected = mvfeLastResult?.graph_insight?.loop_detected

  if (loopDetected) {
    const loopType = mvfeLastResult?.graph_insight?.loop_type || '形成回路'
    return `灵镜检测到「${loopType}」的存在——这是成长的邀请，不是定罪。`
  }
  if (drift > 0.35) return '今日内心有些漂移，这或许是一个安静下来、重新锚定的好时机。'
  if (lastEmo === 'anxiety' || lastEmo === 'fear') return '恐惧不是你的身份。你被那位驱逐惧怕之人所爱。'
  if (lastEmo === 'peace' || lastEmo === 'gratitude') return '今日内心有平静的流动，这是圣灵同在的温柔印记。'
  if (lastEmo === 'joy' || lastEmo === 'hope') return '喜乐与盼望是信仰的果实——今天你正结出这样的果子。'
  if (lastEmo === 'sadness' || lastEmo === 'loneliness') return '悲伤是诚实的祷告。上帝不惧怕你的眼泪，祂与你同在幽谷中。'
  if ((sv.humility || 0.5) > 0.75 && (sv.spiritual_clarity || 0.5) > 0.7) return '谦逊与灵性清晰是今日你最明亮的属灵标记。'
  if ((sv.fear_tendency || 0.5) > 0.65) return '你的恐惧倾向正在呼唤更深的信任——祂掌管一切，包括你所惧怕的。'
  if ((sv.pride_tendency || 0.5) > 0.65) return '骄傲倾向是需要持续悔改的领域。谦卑是门，福音是钥匙。'
  if (streak >= 7) return `连续 ${streak} 天的操练是恩典的流动，而非成就的积累。继续走。`
  if (arc.includes('transform') || traj.includes('up')) return '你的人格弧线正向基督的样式靠近——这是圣灵真实做工的证据。'
  return '每一天的灵修都是将自己放在恩典中——今天也是。'
}

function derivePractice({ formation, mvfeLastResult, habits }) {
  const sv = formation?.state_vector || {}
  const lastEmo = mvfeLastResult?.emotion?.primary_emotion
  const drift = mvfeLastResult?.formation?.drift_score || 0
  const loopDetected = mvfeLastResult?.graph_insight?.loop_detected
  const streak = habits?.current_streak || 0

  if (loopDetected) return { icon: '🙏', title: '安静祷告', desc: '用10分钟安静在神面前，不求改变，只是告白：「我看见了，我愿意被你改变。」' }
  if (drift > 0.35) return { icon: '⚓', title: '真理默想', desc: '选一节经文（如诗篇 46:10），重复诵读三遍，让它成为今天的锚点。' }
  if (lastEmo === 'anxiety' || lastEmo === 'fear') return { icon: '🌬️', title: '呼吸祷告', desc: '吸气时默想「祢是我的神」，呼气时默想「我不惧怕」，重复五次。' }
  if (lastEmo === 'sadness' || lastEmo === 'loneliness') return { icon: '📝', title: '灵修日记', desc: '把今天的悲伤写成一段诚实的祷告，不需要解决，只是倾诉给那位听见的神。' }
  if (lastEmo === 'anger') return { icon: '🌿', title: '恩典省察', desc: '列出三件今天仍然存在的恩典，即使愤怒也遮不住的好事。' }
  if ((sv.humility || 0.5) < 0.4) return { icon: '🪞', title: '谦逊省察', desc: '今天你期待别人认可你的什么？把它带到神面前，问祂：「我的价值感建在哪里？」' }
  if ((sv.relational_health || 0.5) < 0.45) return { icon: '💌', title: '关系修复', desc: '今天主动给一位你疏离的人发一条简短的信息，表达关心或感谢。' }
  if ((sv.truth_alignment || 0.5) < 0.45) return { icon: '📖', title: '读经默想', desc: '从你当前的读经计划中选一段，用SOAP格式（观察/应用/祷告）默想。' }
  if (streak === 0) return { icon: '🌱', title: '重新开始', desc: '今天就是重新开始的最好时机。花五分钟完成一次晨祷，重启你的操练节奏。' }
  if (streak >= 14) return { icon: '🔥', title: '加深操练', desc: `你已连续操练 ${streak} 天，尝试今天加入代祷环节，为一位朋友祈祷。` }
  if (lastEmo === 'peace' || lastEmo === 'gratitude' || lastEmo === 'joy') return { icon: '🎵', title: '感恩颂赞', desc: '用一首诗歌表达你今天的感恩，让喜乐从心里流出来。' }
  return { icon: '🌅', title: '晨间静默', desc: '今天留出五分钟，关掉手机，安静地等候神，不带议程地坐在祂面前。' }
}

const WEEKDAYS = ['日','一','二','三','四','五','六']
function todayLabel() {
  const d = new Date()
  return `${d.getMonth()+1}月${d.getDate()}日 · 周${WEEKDAYS[d.getDay()]}`
}

export default function SoulDashboard({ user }) {
  const [dashData, setDashData]    = useState(null)
  const [overlay, setOverlay]      = useState(null) // 'idolatry' | 'waiting'
  const [pastoral, setPastoral]    = useState(null)
  const [mvfeData, setMvfeData]    = useState(null)
  const [mvfeLast, setMvfeLast]    = useState(null)
  const [selectedDec, setSelDec]   = useState(null)
  const [loading, setLoading]      = useState(true)

  useEffect(() => { const t = getToken(); if (!t) return; fetchWeeklyPastoral(t).then(setPastoral).catch(() => {}) }, [])

  useEffect(() => {
    async function load() {
      try {
        setLoading(true)
        const token = getToken()
        const uid = user?.id || user?.userId
        if (!uid) { setLoading(false); return }

        const [profileData, habitsDash, mvfeDash, mvfeLastRes] = await Promise.all([
          fetchFormationProfile(uid, token).catch(() => null),
          fetch(`${API_BASE}/habits/dashboard`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
            .then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${MVFE_BASE}/dashboard/state?user_id=${uid}&hours=168`)
            .then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${MVFE_BASE}/last-result/${encodeURIComponent(uid)}`)
            .then(r => r.ok ? r.json() : null).catch(() => null),
        ])
        const decisionsRes = await fetch(
          `${API_BASE}/sfds/decisions?user_id=${encodeURIComponent(uid)}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ).catch(() => null)
        const decisions = decisionsRes?.ok ? await decisionsRes.json() : []
        setDashData({ formation: profileData?.profile || null, habits: habitsDash, decisions: decisions.slice(0, 5) })
        setMvfeData(mvfeDash)
        setMvfeLast(mvfeLastRes?.result || null)
      } catch (err) {
        console.error('[SoulDashboard] load error:', err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [user])

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.4)' }}>
        <div style={{ fontSize: 36, marginBottom: 12 }}>🪞</div>
        <div>心镜观照中…</div>
      </div>
    )
  }

  const { formation, habits } = dashData || {}
  const sv        = formation?.state_vector || {}
  const arc       = formation?.formation_arc || ''
  const insight   = deriveInsight({ formation, mvfeLastResult: mvfeLast, habits })
  const practice  = derivePractice({ formation, mvfeLastResult: mvfeLast, habits })
  const streak    = habits?.current_streak || 0
  const lastEmo   = mvfeLast?.emotion?.primary_emotion
  const formScore = mvfeLast?.formation?.formation_score
  const driftScore= mvfeLast?.formation?.drift_score || 0

  const signals = [
    {
      icon: lastEmo ? '😌' : '💭',
      label: '今日情绪',
      value: lastEmo ? (EMOTION_NAMES[lastEmo] || lastEmo) : '暂无记录',
      color: lastEmo ? (C[lastEmo] || '#868e96') : 'rgba(255,255,255,0.3)',
      sub: mvfeLast?.attention?.focus ? `注意·${FOCUS_NAMES[mvfeLast.attention.focus] || mvfeLast.attention.focus}` : '',
    },
    {
      icon: '🧬',
      label: '形成度',
      value: formScore != null ? `${(formScore * 100).toFixed(0)}%` : (arc ? arc.replace(/_/g,' ') : '暂无数据'),
      color: driftScore > 0.3 ? '#ff6b6b' : driftScore > 0.15 ? '#ffa94d' : '#51cf66',
      sub: driftScore > 0.01 ? `漂移 ${(driftScore * 100).toFixed(0)}%` : '',
    },
    {
      icon: streak > 0 ? '🔥' : '🌱',
      label: '操练连续',
      value: streak > 0 ? `${streak} 天` : '今天开始',
      color: streak >= 7 ? '#ffd700' : streak > 0 ? '#34c759' : 'rgba(255,255,255,0.4)',
      sub: streak >= 7 ? '节奏保持中' : streak > 0 ? '你走在路上' : '每天一小步',
    },
  ]

  const hasFormation = Object.keys(sv).length > 0
  const dimScores = DIMS.map(d => ({
    ...d,
    score: d.good ? (sv[d.key] || 0.5) : (1 - (sv[d.key] || 0.5)),
    raw: sv[d.key] || 0.5,
  }))
  const topGrowth     = [...dimScores].filter(d => d.good).sort((a,b) => b.score - a.score).slice(0, 3)
  const needsAttention= dimScores.filter(d => !d.good && d.raw > 0.3).sort((a,b) => b.raw - a.raw).slice(0, 2)

  return (
    <div style={{ paddingBottom: 16 }}>

      {/* ── 属灵星球 · 成长地图（入口）── */}
      <button onClick={() => setOverlay('planet')} style={{ display: 'flex', alignItems: 'center', gap: 12, width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '12px 16px 4px', borderRadius: 16, padding: '14px 16px', background: 'radial-gradient(circle at 18% 30%, rgba(139,92,246,0.30), rgba(90,200,250,0.10))', border: '1px solid rgba(139,92,246,0.35)', color: '#fff' }}>
        <span style={{ fontSize: 26 }}>🪐</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14.5, fontWeight: 700 }}>属灵星球 · 成长地图</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.6)', marginTop: 2 }}>认识自己 · 回到福音 · 与神同行 · 等候上帝 · 人格塑造</div>
        </div>
        <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.45)' }}>›</span>
      </button>

      {/* ── 今日心镜 头部 ── */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(52,199,89,0.1) 0%, rgba(90,200,250,0.08) 100%)',
        borderRadius: '0 0 20px 20px',
        padding: '20px 16px 18px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        marginBottom: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', letterSpacing: 1 }}>今日心镜</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{todayLabel()}</div>
          </div>
          <span style={{ fontSize: 28 }}>🪞</span>
        </div>

        {/* 一句洞见 */}
        <div style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: 12,
          padding: '12px 14px',
          borderLeft: '3px solid rgba(52,199,89,0.5)',
          marginBottom: 14,
        }}>
          <div style={{ fontSize: 10, color: 'rgba(52,199,89,0.7)', fontWeight: 700, letterSpacing: 1, marginBottom: 6 }}>✦ 今日洞见</div>
          <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.88)', lineHeight: 1.65, fontStyle: 'italic' }}>{insight}</div>
        </div>

        {/* 3 信号 */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
          {signals.map((s, i) => (
            <div key={i} style={{
              background: 'rgba(0,0,0,0.25)', borderRadius: 12, padding: '10px 8px',
              textAlign: 'center', border: `1px solid ${s.color}25`,
            }}>
              <div style={{ fontSize: 18, marginBottom: 4 }}>{s.icon}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: s.color, marginBottom: 2 }}>{s.value}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.35)' }}>{s.label}</div>
              {s.sub && <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.22)', marginTop: 2 }}>{s.sub}</div>}
            </div>
          ))}
        </div>
      </div>

      {/* ── 今日省察 Examen ── */}
      <button onClick={() => setOverlay('examen')} style={{ display: 'block', width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '0 16px 12px', borderRadius: 14, padding: '14px 16px',
        background: 'linear-gradient(135deg, rgba(139,92,246,0.16), rgba(90,200,250,0.10))', border: '1px solid rgba(139,92,246,0.25)', color: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24 }}>🌗</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>今日省察 · 与神同回顾这一天</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', marginTop: 2 }}>安慰 / 枯涩 · 感恩 · 求恕 · 明日一个微顺服</div>
          </div>
          <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }}>›</span>
        </div>
      </button>

      {/* ── 福音诊断室（双引擎核心循环）── */}
      <button onClick={() => setOverlay('gospel')} style={{ display: 'block', width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '0 16px 12px', borderRadius: 14, padding: '14px 16px',
        background: 'linear-gradient(135deg, rgba(218,119,242,0.16), rgba(255,212,59,0.10))', border: '1px solid rgba(218,119,242,0.28)', color: '#fff' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 24 }}>🔬</span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>福音诊断室 · 从情绪挖到福音</div>
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', marginTop: 2 }}>钟马田挖到偶像与不信 · 司布真带你回到基督</div>
          </div>
          <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }}>›</span>
        </div>
      </button>

      {/* ── 属灵低潮体检 ── */}
      <button onClick={() => setOverlay('checkup')} style={{ display: 'flex', alignItems: 'center', gap: 10, width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '0 16px 12px', borderRadius: 14, padding: '12px 16px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff' }}>
        <span style={{ fontSize: 20 }}>🩺</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>属灵低潮体检</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>钟马田：不要听自己，要向自己传讲福音</div>
        </div>
        <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }}>›</span>
      </button>

      {/* ── 晨更/晚祷提醒 ── */}
      <button onClick={() => setOverlay('reminder')} style={{ display: 'flex', alignItems: 'center', gap: 10, width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '0 16px 12px', borderRadius: 14, padding: '12px 16px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff' }}>
        <span style={{ fontSize: 20 }}>🔔</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>晨更 · 晚祷提醒</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>让灵修有节奏——开启每日温柔提醒</div>
        </div>
        <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }}>›</span>
      </button>

      {/* ── 灵修操练 Hub ── */}
      <button onClick={() => setOverlay('hub')} style={{ display: 'flex', alignItems: 'center', gap: 10, width: 'calc(100% - 32px)', textAlign: 'left', cursor: 'pointer', margin: '0 16px 12px', borderRadius: 14, padding: '12px 16px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: '#fff' }}>
        <span style={{ fontSize: 20 }}>✦</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>灵修操练</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>感恩 · 认罪与赦免 · 教会历 · 灵修问责 · 我的数据</div>
        </div>
        <span style={{ fontSize: 18, color: 'rgba(255,255,255,0.4)' }}>›</span>
      </button>

      {/* ── 心镜入口：偶像监测 · 等候之路 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2,1fr)', gap: 10, margin: '0 16px 16px' }}>
        <button onClick={() => setOverlay('idolatry')} style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid rgba(139,92,246,0.25)', borderRadius: 14, padding: '14px', background: 'linear-gradient(135deg, rgba(139,92,246,0.16), rgba(236,72,153,0.10))', color: '#fff' }}>
          <div style={{ fontSize: 22, marginBottom: 6 }}>🧭</div>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>偶像监测</div>
          <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.5)', marginTop: 2, lineHeight: 1.5 }}>什么正在取代神成为内心中心？</div>
        </button>
        <button onClick={() => setOverlay('waiting')} style={{ textAlign: 'left', cursor: 'pointer', border: '1px solid rgba(52,199,89,0.25)', borderRadius: 14, padding: '14px', background: 'linear-gradient(135deg, rgba(52,199,89,0.14), rgba(90,200,250,0.10))', color: '#fff' }}>
          <div style={{ fontSize: 22, marginBottom: 6 }}>🕯️</div>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>等候之路</div>
          <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.5)', marginTop: 2, lineHeight: 1.5 }}>从等待戈多，到等候上帝</div>
        </button>
      </div>

      {/* ── 本周牧养小结 ── */}
      {pastoral && pastoral.title && (
        <div style={{ margin: '0 16px 16px', borderRadius: 14, padding: '16px',
          background: 'linear-gradient(135deg, rgba(255,212,59,0.10), rgba(139,92,246,0.08))',
          border: '1px solid rgba(255,212,59,0.20)' }}>
          <div style={{ fontSize: 10, color: 'rgba(255,212,59,0.8)', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>✦ {pastoral.title}</div>
          {pastoral.gods_work && <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.75 }}>{pastoral.gods_work}</div>}
          {pastoral.invitation && (
            <div style={{ marginTop: 10, fontSize: 12.5, color: '#5ac8fa', lineHeight: 1.7 }}>🕊 {pastoral.invitation}</div>
          )}
          {pastoral.scripture && (
            <div style={{ marginTop: 10, borderLeft: '3px solid rgba(167,139,250,0.5)', paddingLeft: 10, fontSize: 12, color: 'rgba(255,255,255,0.66)', fontStyle: 'italic' }}>
              「{pastoral.scripture.text}」<span style={{ color: 'rgba(167,139,250,0.8)', fontStyle: 'normal' }}> —— {pastoral.scripture.ref}</span>
            </div>
          )}
        </div>
      )}

      {/* ── 今日操练 ── */}
      <div style={{
        margin: '0 16px 16px',
        background: 'rgba(90,200,250,0.05)',
        border: '1px solid rgba(90,200,250,0.18)',
        borderRadius: 14,
        padding: '14px 16px',
      }}>
        <div style={{ fontSize: 10, color: 'rgba(90,200,250,0.7)', fontWeight: 700, letterSpacing: 1, marginBottom: 10 }}>今日操练建议</div>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
          <span style={{ fontSize: 28, flexShrink: 0 }}>{practice.icon}</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#5ac8fa', marginBottom: 5 }}>{practice.title}</div>
            <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.72)', lineHeight: 1.65 }}>{practice.desc}</div>
          </div>
        </div>
      </div>

      {/* ── 八维属灵概览 ── */}
      {hasFormation && (
        <div style={{
          margin: '0 16px 16px',
          background: 'rgba(255,255,255,0.04)',
          borderRadius: 14,
          padding: '14px 16px',
          border: '1px solid rgba(255,255,255,0.06)',
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'rgba(255,255,255,0.75)', marginBottom: 12 }}>✦ 八维属灵概览</div>

          <div style={{ fontSize: 10, color: 'rgba(52,199,89,0.6)', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>成长亮点</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: needsAttention.length ? 14 : 4 }}>
            {topGrowth.map(d => <DimRow key={d.key} dim={d} score={d.score} />)}
          </div>

          {needsAttention.length > 0 && (
            <>
              <div style={{ fontSize: 10, color: 'rgba(248,113,113,0.6)', fontWeight: 700, letterSpacing: 1, marginBottom: 8 }}>需要关注</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 4 }}>
                {needsAttention.map(d => <DimRow key={d.key} dim={d} score={d.score} />)}
              </div>
            </>
          )}

          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.2)', marginTop: 8 }}>
            轨迹方向: {(formation?.trajectory_direction || '—').replace(/_/g,' ')} · 数据点: {formation?.data_points || 0}
          </div>
        </div>
      )}

      {/* ── 灵镜观心 MVFE ── */}
      {(mvfeData || mvfeLast) && (
        <MvfeSection mvfeData={mvfeData} mvfeLast={mvfeLast} onSelectDecision={setSelDec} />
      )}
      {selectedDec && <DecisionDetailModal decision={selectedDec} onClose={() => setSelDec(null)} />}

      {overlay && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1200, background: '#000' }}>
          {overlay === 'idolatry' && <IdolatryMonitorPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'waiting' && <WaitingPathPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'examen' && <ExamenPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'reminder' && <ReminderSettings onBack={() => setOverlay(null)} />}
          {overlay === 'hub' && <PracticeHubPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'gospel' && <GospelDiagnosticPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'planet' && <PlanetHome onClose={() => setOverlay(null)} go={(t) => setOverlay(t)} />}
          {overlay === 'pilgrim' && <PilgrimJourneyPage onClose={() => setOverlay(null)} go={(t) => setOverlay(t)} />}
          {overlay === 'fhl' && <FaithHopeLovePage user={user} onClose={() => setOverlay(null)} />}
          {overlay === 'discern' && <DecisionDiscernmentPage user={user} onBack={() => setOverlay(null)} />}
          {overlay === 'fuel' && <FuelLibraryPage onClose={() => setOverlay(null)} />}
          {overlay === 'agent' && <AgentChatPage onBack={() => setOverlay(null)} />}
          {overlay === 'checkup' && <SpiritualCheckupPage user={user} onBack={() => setOverlay(null)} />}
        </div>
      )}
    </div>
  )
}

function DimRow({ dim, score }) {
  const pct = Math.max(0, Math.min(1, score)) * 100
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <span style={{ fontSize: 14, width: 20, textAlign: 'center', flexShrink: 0 }}>{dim.icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
          <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)' }}>{dim.name}</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: dim.color }}>{pct.toFixed(0)}%</span>
        </div>
        <div style={{ height: 5, background: 'rgba(255,255,255,0.07)', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ width: pct + '%', height: '100%', background: dim.color, borderRadius: 3, transition: 'width 0.8s' }} />
        </div>
      </div>
    </div>
  )
}

function MvfeSection({ mvfeData: d, mvfeLast: r, onSelectDecision }) {
  // 诚实空状态：后端无真实数据时不展示「假图表」，改为温柔引导
  if (d?.is_mock && !r?.formation) {
    return (
      <div style={{ margin: '0 16px', borderRadius: 16, padding: '20px 16px',
        background: 'linear-gradient(135deg, rgba(139,92,246,0.10), rgba(90,200,250,0.08))',
        border: '1px solid rgba(139,92,246,0.18)', textAlign: 'center' }}>
        <div style={{ fontSize: 26, marginBottom: 8 }}>🪞</div>
        <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 6 }}>灵镜尚未点亮</div>
        <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.6)', lineHeight: 1.7 }}>
          完成一次今日打卡或心迹省察，灵镜就会开始观测你的情绪、注意力与形成方向——
          这里呈现的将是<strong style={{ color: '#a78bfa' }}>你真实的</strong>属灵动态，而非示例。
        </div>
      </div>
    )
  }
  const latest = d?.formation_curve?.length
    ? d.formation_curve[d.formation_curve.length - 1]
    : r?.formation
      ? { formation_score: r.formation.formation_score, drift_score: r.formation.drift_score, stability_score: r.formation.stability_score }
      : null
  const drivers = r?.decision?.drivers || (d?.decision_flow?.length ? d.decision_flow[d.decision_flow.length-1].drivers : {}) || {}
  const decType = r?.decision?.type || (d?.decision_flow?.length ? d.decision_flow[d.decision_flow.length-1].type : 'avoidance') || 'avoidance'

  return (
    <div style={{
      margin: '0 16px',
      background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(236,72,153,0.12) 100%)',
      borderRadius: 16,
      padding: 16,
      border: '1px solid rgba(139,92,246,0.18)',
    }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
        <span>🔮</span><span>灵镜观心</span>
      </div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginBottom: 14 }}>
        HIDOS 人格形成动态观测仪
        {d?.is_mock && <span style={{ color: '#ffa94d', marginLeft: 8 }}>⚡ 预览数据</span>}
      </div>

      <div style={mvSt.grid4}>
        <Kpi icon="🎭" label="情绪"
          v={EMOTION_NAMES[r?.emotion?.primary_emotion] || r?.emotion?.primary_emotion || '—'}
          sub={(r?.emotion?.secondary_emotions || []).slice(0,2).map(e => EMOTION_NAMES[e]||e).join('，') || ''}
          color={C[r?.emotion?.primary_emotion] || '#868e96'} />
        <Kpi icon="👁" label="注意力"
          v={FOCUS_NAMES[r?.attention?.focus] || r?.attention?.focus || '—'}
          sub={'固化 ' + ((r?.attention?.fixation_score||0)*100).toFixed(1)+'%'}
          color="#4facfe" />
        <Kpi icon="⚖️" label="决策"
          v={decType==='approach'?'趋近':'回避'}
          sub={'恐惧 '+((drivers?.fear||0)*100).toFixed(1)+'%'}
          color={decType==='approach'?'#51cf66':'#ff6b6b'} />
        <Kpi icon="🧬" label="形成度"
          v={latest ? ((latest.formation_score*100).toFixed(1)+'%') : '—'}
          sub={'漂移 '+((latest?.drift_score||0)*100).toFixed(1)+'%'}
          color="#ffa94d" />
      </div>

      <div style={mvSt.grid2}>
        <Card t="形成度仪表盘" i="🧭"><Gauge score={latest?.formation_score||0} drift={latest?.drift_score||0} stab={latest?.stability_score||0}/></Card>
        <Card t="决策驱动" i="🔥"><Drivers d={drivers}/></Card>
      </div>
      <div style={mvSt.grid2}>
        <Card t="情绪时间线" i="📈"><EmoChart data={d?.emotion_series||[]}/></Card>
        <Card t="注意力分配" i="🎯"><AttBars data={d?.attention_map||(r?.attention?{[FOCUS_NAMES[r.attention.focus]||r.attention.focus]:r.attention.fixation_score}:{})}/></Card>
      </div>
      <Card t="实时因果链" i="🔗"><Chain r={r}/></Card>
      <div style={{ ...mvSt.grid2, marginTop: 12 }}>
        <Card t="灵镜洞察" i="💡"><Insight r={r}/></Card>
        <Card t="回路检测" i="🔄"><LoopCard g={r?.graph_insight} hasResult={!!r}/></Card>
      </div>
      <Card t="决策模式流" i="⚖️"><DecFlow data={d?.decision_flow||[]} onSelect={onSelectDecision}/></Card>
      <div style={{fontSize:9,color:'rgba(255,255,255,0.15)',textAlign:'center',padding:'8px 0 0',lineHeight:1.6}}>
        本仪表盘仅展示观测性模式，不构成心理诊断、人格评估或行为处方。
      </div>
    </div>
  )
}

function Card({t,i,children}){return <div style={mvSt.card}><div style={{display:'flex',alignItems:'center',gap:6,marginBottom:10}}><span style={{fontSize:14}}>{i}</span><span style={{fontSize:12,fontWeight:700,color:'rgba(255,255,255,0.85)'}}>{t}</span></div><div>{children}</div></div>}
function Kpi({icon,label,v,sub,color}){return <div style={mvSt.kpi}><div style={{fontSize:20,marginBottom:4}}>{icon}</div><div style={{fontSize:10,color:'rgba(255,255,255,0.35)',marginBottom:2}}>{label}</div><div style={{fontSize:14,fontWeight:700,color}}>{v}</div>{sub&&<div style={{fontSize:9,color:'rgba(255,255,255,0.3)',marginTop:2}}>{sub}</div>}</div>}
function Gauge({score,drift,stab}){
  const pct=Math.max(0,Math.min(1,score))*100
  const r=42,cx=56,cy=56,circ=2*Math.PI*r,off=circ*(1-pct/100)
  return <div style={{display:'flex',alignItems:'center',gap:14}}>
    <svg viewBox="0 0 112 80" style={{width:110,flexShrink:0}}>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" strokeLinecap="round"/>
      <path d={"M "+(cx-r)+" "+cy+" A "+r+" "+r+" 0 1 1 "+(cx+r)+" "+cy} fill="none" stroke="#4facfe" strokeWidth="8" strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={off}/>
      <text x={cx} y={cy+5} fill="#fff" fontSize="16" fontWeight="700" textAnchor="middle">{pct.toFixed(1)}</text>
      <text x={cx} y={cy+18} fill="rgba(255,255,255,0.3)" fontSize="7" textAnchor="middle">形成度</text>
    </svg>
    <div style={{flex:1,display:'flex',flexDirection:'column',gap:6}}>
      <MvBar l="形成度" v={pct} c="#4facfe"/>
      <MvBar l="漂移信号" v={drift*100} c={drift>0.3?'#ff6b6b':'#ffa94d'}/>
      <MvBar l="稳定性" v={stab*100} c="#51cf66"/>
    </div>
  </div>
}
function MvBar({l,v,c}){const pct=Math.max(0,Math.min(100,v));return <div><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:10,color:'rgba(255,255,255,0.4)'}}>{l}</span><span style={{fontSize:10,color:c,fontWeight:600}}>{pct.toFixed(1)}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:pct+'%',height:'100%',borderRadius:3,background:c,transition:'width 0.8s ease'}}/></div></div>}
function Drivers({d}){
  const items=[{k:'fear',l:'恐惧驱动',c:'#ff6b6b',e:'😨'},{k:'ego',l:'自我驱动',c:'#ffa94d',e:'🦅'},{k:'love',l:'关系驱动',c:'#ff8787',e:'❤️'}]
  return <div style={{display:'flex',flexDirection:'column',gap:10}}>{items.map(({k,l,c,e})=>{const v=(d[k]||0)*100;return <div key={k} style={{display:'flex',alignItems:'center',gap:8}}><span style={{fontSize:14,width:20,textAlign:'center'}}>{e}</span><div style={{flex:1}}><div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{l}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{v.toFixed(1)}%</span></div><div style={{height:8,borderRadius:4,background:'rgba(255,255,255,0.05)',overflow:'hidden'}}><div style={{width:v+'%',height:'100%',borderRadius:4,background:c,opacity:0.85,transition:'width 0.8s ease'}}/></div></div></div>})}</div>
}
function EmoChart({data}){
  if(!data||data.length<2)return <div style={mvSt.noData}>暂无历史数据</div>
  const w=280,h=100,pl=10,pr=10,pt=8,pb=18,cw=w-pl-pr,ch=h-pt-pb,n=data.length
  const x=i=>pl+(i/(n-1))*cw,y=v=>pt+(1-v)*ch
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
  if(e.length===0)return <div style={mvSt.noData}>暂无数据</div>
  const mx=Math.max(...e.map(x=>x[1]),0.01)
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>{e.slice(0,5).map(([focus,val])=>{const pct=(val/mx)*100,c=val>0.3?'#ff6b6b':val>0.15?'#ffa94d':'#4facfe';return <div key={focus}><div style={{display:'flex',justifyContent:'space-between',marginBottom:2}}><span style={{fontSize:11,color:'rgba(255,255,255,0.6)'}}>{FOCUS_NAMES[focus]||focus}</span><span style={{fontSize:11,color:c,fontWeight:600}}>{(val*100).toFixed(1)}%</span></div><div style={{height:5,borderRadius:3,background:'rgba(255,255,255,0.04)',overflow:'hidden'}}><div style={{width:pct+'%',height:'100%',borderRadius:3,background:c,opacity:0.8,transition:'width 0.6s'}}/></div></div>})}</div>
}
function Chain({r}){
  if(!r)return <div style={mvSt.noData}>提交分析后显示实时因果链</div>
  const em=r.emotion||{},at=r.attention||{},de=r.decision||{},fo=r.formation||{}
  const nodes=[
    {l:EMOTION_NAMES[em.primary_emotion]||em.primary_emotion||'情绪',v:((em.intensity||0)*100).toFixed(1)+'%',c:C[em.primary_emotion]||'#ffa94d',s:(em.secondary_emotions||[]).slice(0,2).map(e=>EMOTION_NAMES[e]||e).join('，')||''},
    {l:FOCUS_NAMES[at.focus]||at.focus||'注意力',v:((at.fixation_score||0)*100).toFixed(1)+'% 固化',c:'#4facfe',s:'漂移 '+((at.drift_risk||0)*100).toFixed(1)+'%'},
    {l:de.type==='approach'?'趋近':'回避',v:'恐惧 '+((de.drivers?.fear||0)*100).toFixed(1)+'%',c:de.type==='approach'?'#51cf66':'#ff6b6b',s:'自我 '+((de.drivers?.ego||0)*100).toFixed(1)+'%'},
    {l:'形成',v:((fo.formation_score||0)*100).toFixed(1)+'%',c:'#ffa94d',s:'漂移 '+((fo.drift_score||0)*100).toFixed(1)+'%'},
  ]
  return <div style={{display:'flex',alignItems:'center',gap:6,flexWrap:'wrap',justifyContent:'center',padding:'4px 0'}}>{nodes.map((n,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:6}}><div style={{padding:'8px 12px',borderRadius:10,background:n.c+'15',border:'1px solid '+n.c+'40',textAlign:'center',minWidth:72}}><div style={{fontSize:10,color:'rgba(255,255,255,0.4)',marginBottom:2}}>{n.l}</div><div style={{fontSize:12,fontWeight:700,color:n.c}}>{n.v}</div>{n.s&&<div style={{fontSize:8,color:'rgba(255,255,255,0.25)',marginTop:1}}>{n.s}</div>}</div>{i<nodes.length-1&&<span style={{fontSize:16,color:'rgba(255,255,255,0.1)'}}>→</span>}</div>)}</div>
}
function Insight({r}){
  if(!r)return <div style={mvSt.noData}>暂无洞察</div>
  const ref=r.reflection||{}
  const interpretation=ref.state_interpretation||(r.emotion?.primary_emotion&&r.attention?.focus?`系统检测到${EMOTION_NAMES[r.emotion.primary_emotion]||r.emotion.primary_emotion}情绪，注意力聚焦于${FOCUS_NAMES[r.attention.focus]||r.attention.focus}。`:null)||'暂无状态解读'
  const loopInfo=ref.loop_detection||(r.graph_insight?.loop_detected?`检测到${r.graph_insight.loop_type||'形成回路'}`:null)
  return <div style={{display:'flex',flexDirection:'column',gap:8}}>
    <div style={{fontSize:12,color:'rgba(255,255,255,0.75)',lineHeight:1.7}}>{interpretation}</div>
    {loopInfo&&!loopInfo.includes('未检测到明显回路')&&<div style={{fontSize:11,color:'#ffa94d',padding:'6px 10px',borderRadius:8,background:'rgba(255,169,77,0.06)',borderLeft:'2px solid rgba(255,169,77,0.4)'}}>🔄 {loopInfo}</div>}
    <div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(79,172,254,0.05)',borderLeft:'2px solid rgba(79,172,254,0.25)'}}>
      <span style={{fontSize:10,color:'#4facfe',fontWeight:600}}>💡 反射问题</span>
      <div style={{fontSize:13,color:'#a0d4f7',fontStyle:'italic',marginTop:5}}>{ref.reflective_question||'此刻，什么在你里面最活跃？'}</div>
    </div>
    {ref.bible_verse_hint&&<div style={{marginTop:2,padding:10,borderRadius:10,background:'rgba(255,193,7,0.05)',borderLeft:'2px solid rgba(255,193,7,0.25)'}}>
      <span style={{fontSize:10,color:'#ffc107',fontWeight:600}}>📖 应许锚点</span>
      <div style={{fontSize:12,color:'rgba(255,255,255,0.7)',marginTop:5,lineHeight:1.6}}>{ref.bible_verse_hint}</div>
    </div>}
  </div>
}
function LoopCard({g,hasResult}){
  if(!hasResult)return <div style={{textAlign:'center',padding:'20px 10px'}}><div style={{fontSize:24,marginBottom:8}}>🔬</div><div style={{fontSize:11,color:'rgba(255,255,255,0.3)'}}>完成一次灵镜分析后显示回路检测结果</div></div>
  if(!g||!g.loop_detected)return <div style={{textAlign:'center',padding:'20px 10px'}}><div style={{fontSize:28,marginBottom:8}}>✅</div><div style={{fontSize:12,color:'#51cf66',fontWeight:600}}>未检测到形成回路</div><div style={{fontSize:11,color:'rgba(255,255,255,0.3)',marginTop:4}}>当前状态相对开放，无明显闭环</div></div>
  const meta=LOOP_LABELS[g.loop_type]||{label:g.loop_type||'检测到形成回路',color:'#ffa94d',desc:''}
  const strength=parseFloat(((g.loop_strength||0)*100).toFixed(1))
  return <div style={{display:'flex',flexDirection:'column',gap:10}}>
    <div style={{display:'flex',alignItems:'center',gap:8}}><span style={{fontSize:16}}>⚠️</span><span style={{fontSize:13,color:meta.color,fontWeight:700}}>{meta.label}</span></div>
    {meta.desc&&<div style={{fontSize:11,color:'rgba(255,255,255,0.45)',lineHeight:1.6,padding:'6px 10px',borderRadius:8,background:`${meta.color}10`,borderLeft:`2px solid ${meta.color}40`}}>{meta.desc}</div>}
    <div><div style={{display:'flex',justifyContent:'space-between',fontSize:10,color:'rgba(255,255,255,0.4)',marginBottom:4}}><span>回路强度</span><span style={{color:meta.color,fontWeight:600}}>{strength}%</span></div><div style={{height:6,borderRadius:3,background:'rgba(255,255,255,0.07)',overflow:'hidden'}}><div style={{width:`${strength}%`,height:'100%',borderRadius:3,background:meta.color,transition:'width 0.8s ease'}}/></div></div>
    {g.dominant_desires?.length>0&&<div style={{fontSize:10,color:'rgba(255,255,255,0.35)'}}>核心渴望: {g.dominant_desires.map(d=>DESIRE_LABELS[d]||d).join(' · ')}</div>}
    {g.core_beliefs?.length>0&&<div style={{fontSize:10,color:'rgba(255,255,255,0.35)'}}>核心信念: {g.core_beliefs.map(b=>BELIEF_LABELS[b]||b).join(' · ')}</div>}
  </div>
}
function DecFlow({data,onSelect}){
  if(!data||data.length===0)return <div style={mvSt.noData}>暂无决策数据</div>
  const total=data.length,avoid=data.filter(d=>d.type==='avoidance').length,app=total-avoid,ar=total>0?avoid/total:0
  let lbl='平衡模式',col='#4facfe'
  if(ar>0.6){lbl='回避主导';col='#ff6b6b'}else if(ar<0.4){lbl='趋近主导';col='#51cf66'}
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
function DecisionDetailModal({decision,onClose}){
  return <div style={{position:'fixed',inset:0,background:'rgba(0,0,0,0.6)',backdropFilter:'blur(4px)',zIndex:1000,display:'flex',alignItems:'center',justifyContent:'center',padding:16}} onClick={onClose}>
    <div style={{background:'linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)',borderRadius:16,padding:20,maxWidth:400,width:'100%',border:'1px solid rgba(255,255,255,0.1)'}} onClick={e=>e.stopPropagation()}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16}}>
        <div style={{fontSize:16,fontWeight:700,color:'#fff'}}>决策详情</div>
        <button onClick={onClose} style={{background:'none',border:'none',color:'rgba(255,255,255,0.5)',fontSize:20,cursor:'pointer'}}>×</button>
      </div>
      <div style={{display:'flex',flexDirection:'column',gap:12}}>
        <div style={{display:'flex',alignItems:'center',gap:8}}><span style={{fontSize:24}}>{decision.type==='approach'?'🟢':'🔴'}</span>
          <div><div style={{fontSize:14,fontWeight:600,color:decision.type==='approach'?'#51cf66':'#ff6b6b'}}>{decision.type==='approach'?'趋近决策':'回避决策'}</div>
          <div style={{fontSize:11,color:'rgba(255,255,255,0.4)'}}>{decision.timestamp?new Date(decision.timestamp).toLocaleString('zh-CN'):''}</div></div></div>
        {decision.drivers&&<div style={{padding:12,borderRadius:8,background:'rgba(255,255,255,0.03)'}}>
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
}

const mvSt = {
  card:   { background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:12, padding:14, marginBottom:12 },
  kpi:    { background:'rgba(255,255,255,0.03)', border:'1px solid rgba(255,255,255,0.06)', borderRadius:10, padding:'12px 8px', textAlign:'center' },
  grid4:  { display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, marginBottom:12 },
  grid2:  { display:'grid', gridTemplateColumns:'1fr 1fr', gap:12 },
  noData: { textAlign:'center', padding:'20px 10px', color:'rgba(255,255,255,0.3)', fontSize:12 },
}
