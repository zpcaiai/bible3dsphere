import { useEffect, useState, useRef, useCallback } from 'react'
import { fetchFormationProfile, fetchFormationDimensions, saveReflectionAnswers, fetchReflectionAnswers, createHabitsFromFormationPlan } from './api'
import { getToken } from './auth'

const REFLECTION_CATEGORIES = [
  {
    key: 'god_relationship',
    label: '第一类：与神的关系（核心根基）',
    emoji: '🙏',
    color: '#fbbf24',
    lesson: '信靠、亲近神、听从圣灵',
    questions: [
      '我每天/每周与神亲密相交（读经+祷告）的时间和品质如何？是否流于形式？',
      '当我遇到困难时，第一反应是倚靠神、还是先靠自己或他人？',
      '我最近在读经或听道时，神最常感动或责备我的经文或主题是什么？',
      '我是否真正相信神在我生命中掌权，并为我有美好的计划？（有没有隐藏的不信或埋怨？）',
    ]
  },
  {
    key: 'character',
    label: '第二类：品格与内心（圣灵果子）',
    emoji: '🌿',
    color: '#4ade80',
    lesson: '忍耐、谦卑、饶恕、节制',
    questions: [
      '在压力、委屈或被批评时，我最常表现出什么情绪或行为？（如愤怒、退缩、控诉）',
      '我生命中缺少圣灵果子（加拉太书5:22-23）最明显的是哪一项？（仁爱、喜乐、和平、忍耐、恩慈、良善、信实、温柔、节制）',
      '我是否容易嫉妒、比较、或在意他人对我的看法？',
      '我在小事上是否诚实、守时、尽责？有哪些「小罪」我常常轻忽？',
    ]
  },
  {
    key: 'relationships',
    label: '第三类：人际关系与团契',
    emoji: '🤝',
    color: '#f472b6',
    lesson: '爱人如己、饶恕、谦卑服事',
    questions: [
      '我与最亲近的人（配偶、家人、朋友）最近最常发生的冲突是什么？背后的原因是？',
      '我是否主动关心他人、饶恕他人，还是容易记恨或论断？',
      '在教会或小组中，我是积极建造他人，还是比较被动或只索取？',
      '我是否害怕被拒绝，而不敢真实敞开自己的软弱？',
    ]
  },
  {
    key: 'trials',
    label: '第四类：试炼与试探（神常用的「教室」）',
    emoji: '🔥',
    color: '#f87171',
    lesson: '顺服、放下偶像、在患难中喜乐',
    questions: [
      '过去半年到一年，我最常重复遇到的试炼或挫折是什么？',
      '在这些试炼中，我最常问神「为什么」，还是问「你要教导我什么」？',
      '我有哪些反复的试探或老我习惯（例如懒惰、贪婪、色欲、忧虑）？',
      '如果神现在要我「放下」某样东西（人、事、物、习惯），我最舍不得的是什么？',
    ]
  },
  {
    key: 'calling',
    label: '第五类：事奉、呼召与果子',
    emoji: '🎯',
    color: '#60a5fa',
    lesson: '忠心、传福音、结果子',
    questions: [
      '我如何使用神给我的时间、金钱、恩赐？是否以神国为优先？',
      '我在职场、家庭或教会中的见证，是否让人看见基督的不同？',
      '我是否清楚自己目前的呼召？有没有在逃避或拖延？',
      '身边的人（包括未信者）因为我的生命而更靠近神了吗？',
    ]
  }
]

const FREQUENCY_OPTIONS = [
  { value: 9, label: '🌳稳定操练', color: '#4ade80', desc: '稳定活出' },
  { value: 5, label: '🌿成长中', color: '#fbbf24', desc: '有所意识' },
  { value: 2, label: '🌱盲点', color: '#f87171', desc: '尚需成长' },
]

export default function PersonalityPage({ user, embedded = false, onSyncToHabits }) {
  const [profile, setProfile] = useState(null)
  const [dimensions, setDimensions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('reflection')
  const [reflectionAnswers, setReflectionAnswers] = useState({})
  const [saveStatus, setSaveStatus] = useState(null)
  const [syncStatus, setSyncStatus] = useState(null) // 'syncing' | 'synced' | 'error' | null
  const saveTimerRef = useRef(null)

  const debouncedSave = useCallback((answers) => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(async () => {
      try {
        const token = getToken()
        await saveReflectionAnswers(user?.id || 'demo', answers, token)
        setSaveStatus('saved')
        setTimeout(() => setSaveStatus(null), 2000)
      } catch (e) {
        setSaveStatus('error')
        setTimeout(() => setSaveStatus(null), 3000)
      }
    }, 800)
  }, [user])

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        const token = getToken()
        
        // 并行加载数据
        const [profileData, dimsData, reflectionData] = await Promise.all([
          fetchFormationProfile(user?.id || 'demo', token).catch(() => null),
          fetchFormationDimensions(token).catch(() => null),
          fetchReflectionAnswers(user?.id || 'demo', token).catch(() => null)
        ])
        
        setProfile(profileData)
        setDimensions(dimsData?.dimensions || [])
        if (reflectionData?.answers) setReflectionAnswers(reflectionData.answers)
      } catch (err) {
        console.error('[PersonalityPage] Load error:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [user])

  if (loading) {
    return (
      <div style={{ 
        padding: '40px 20px', 
        textAlign: 'center',
        color: 'rgba(255,255,255,0.6)'
      }}>
        <div style={{ fontSize: '32px', marginBottom: '16px' }}>🔮</div>
        <div>加载人格塑造档案...</div>
      </div>
    )
  }

  // 获取性格维度分数
  const getDimensionScore = (key) => {
    if (!profile?.profile?.state_vector) return 0.5
    return profile.profile.state_vector[key] || 0.5
  }

  // 获取形成弧线
  const getFormationArc = () => {
    return profile?.profile?.formation_arc || 'unknown'
  }

  // 获取轨迹方向
  const getTrajectoryDirection = () => {
    return profile?.profile?.trajectory_direction || 'unknown'
  }

  // 获取主导循环
  const getDominantLoop = () => {
    return profile?.profile?.dominant_loop || '暂无数据'
  }

  // 维度颜色映射
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

  // 维度中文名称
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

  // 弧线描述
  const arcDescriptions = {
    breaking_through: { emoji: '🌅', text: '突破期', desc: '健康的维度正在增强' },
    deepening_loops: { emoji: '🔄', text: '循环深化', desc: '需要注意的行为模式' },
    stabilizing: { emoji: '⚖️', text: '稳定期', desc: '整体趋于平衡' },
    unknown: { emoji: '❓', text: '未知', desc: '数据不足' }
  }

  // 轨迹方向描述
  const trajectoryDescriptions = {
    stabilizing: { emoji: '📈', text: '趋于稳定', color: '#4ade80' },
    fragmenting: { emoji: '⚠️', text: '趋于分散', color: '#f87171' },
    improving_clarity: { emoji: '✨', text: '清晰度提升', color: '#60a5fa' },
    increasing_volatility: { emoji: '📉', text: '波动性增加', color: '#fb923c' },
    cyclical: { emoji: '🔄', text: '周期性', color: '#fbbf24' },
    unknown: { emoji: '❓', text: '未知', color: '#9ca3af' }
  }

  const arc = arcDescriptions[getFormationArc()] || arcDescriptions.unknown
  const trajectory = trajectoryDescriptions[getTrajectoryDirection()] || trajectoryDescriptions.unknown

  // ── 从反思问卷分数推导生命成熟度与功课 ──
  const computeFormationAnalysis = () => {
    const catScores = REFLECTION_CATEGORIES.map(cat => {
      const scores = cat.questions.map((_, qi) => reflectionAnswers[`${cat.key}_${qi}`] ?? 0)
      const answered = scores.filter(s => s > 0)
      const avg = answered.length > 0 ? answered.reduce((a, b) => a + b, 0) / answered.length : 0
      return { key: cat.key, label: cat.label, emoji: cat.emoji, color: cat.color, lesson: cat.lesson, avg, answered: answered.length, total: cat.questions.length }
    })
    const answeredCats = catScores.filter(c => c.answered > 0)
    if (answeredCats.length === 0) return null

    const overallAvg = answeredCats.reduce((s, c) => s + c.avg, 0) / answeredCats.length
    // 成熟度 = 答题平均分 / 10，映射到 5 个阶段
    const maturityPct = Math.round((overallAvg / 10) * 100)
    const maturityStage = overallAvg >= 8 ? { label: '成熟稳固期', color: '#4ade80', emoji: '🌳', desc: '生命根基稳固，持续结出果子' }
      : overallAvg >= 6 ? { label: '成长深化期', color: '#60a5fa', emoji: '🌿', desc: '正在深化，需持续操练' }
      : overallAvg >= 4 ? { label: '挣扎突破期', color: '#fbbf24', emoji: '🌱', desc: '已有意识，仍需神的工作' }
      : { label: '起步觉醒期', color: '#f87171', emoji: '🌰', desc: '正在被唤醒，神要开始塑造工作' }

    // 最弱的类别 = 主要生命功课
    const sorted = [...catScores].filter(c => c.answered > 0).sort((a, b) => a.avg - b.avg)
    const topLessons = sorted.slice(0, 2)
    const strongCats = [...catScores].filter(c => c.answered > 0).sort((a, b) => b.avg - a.avg).slice(0, 2)

    // 基于最弱类别生成灵修计划
    const planMap = {
      god_relationship: {
        short: ['每天固定时间读经30分钟，用SOAP方法（观察、应用、祷告）', '每周写一篇与神相遇的日记', '用诗篇139:23-24开始每天的祷告'],
        mid: ['完成一套系统读经计划（如一年读完圣经）', '学习默观祷告或安静等候神', '寻找属灵导师，每月分享灵性状况']
      },
      character: {
        short: ['每天睡前记录一件"圣灵果子"表现和一件失败的事', '当感到愤怒时，用10秒暂停法并默祷腓4:7', '选一项最弱的圣灵果子专项操练（如节制）'],
        mid: ['研读登山宝训（马太福音5-7章），每章写应用', '加入读书小组共同研读品格塑造资料', '邀请3位亲密朋友给你品格上的诚实反馈']
      },
      relationships: {
        short: ['本周主动联系一位许久未联系的人，不带目的关心', '练习"先聆听后说话"：本周开口前先问一个问题', '写下需要饶恕的人，用祷告交托'],
        mid: ['系统学习非暴力沟通（NVC）或圣经中的和好原则', '与配偶/家人建立每周固定的深度对话时间', '在小组中担任服事职责，操练委身与舍己']
      },
      trials: {
        short: ['每天感恩日记：写3件患难中仍感恩的事', '遇到试炼时，先问"神要教我什么"再求解脱', '找出一个反复出现的老我习惯，每周记录一次进展'],
        mid: ['研读约伯记或罗马书8章，记录对苦难的理解变化', '识别生命中的"偶像"：将神以外的依靠列出来一一交托', '与辅导者共同探索试炼背后的根源模式']
      },
      calling: {
        short: ['写下自己认为神给的3个恩赐，并找本周用上的机会', '向一位未信友分享近期的生命见证', '检视时间/金钱分配：记录本周用在神国上的比例'],
        mid: ['完成恩赐评估测试并与小组讨论', '制定"事奉地图"：在家庭、教会、职场各一项具体服事', '设立传福音目标：为身边3位未信者持续代祷并寻求机会']
      }
    }

    const shortPlan = topLessons.flatMap(c => (planMap[c.key]?.short || []).slice(0, 2))
    const midPlan = topLessons.flatMap(c => (planMap[c.key]?.mid || []).slice(0, 2))

    // 基于8维分数生成"今日可行一步"
    const DIM_ACTIONS = {
      humility:            { name:'谦逊',    icon:'🌿', threshold:0.5, action:'今天遇到被否定的时刻，练习在心里先说：「我不需要被证明是对的。」' },
      emotional_stability: { name:'情绪稳定', icon:'🌊', threshold:0.5, action:'设置一个"情绪暂停"提醒——每天下午3点用3分钟做一次自我觉察：此刻我的内心在哪里？' },
      truth_alignment:     { name:'真理对齐', icon:'📖', threshold:0.5, action:'今天读一段经文，把它写在手机备忘录里，下班前回顾一次它如何影响了今天的决定。' },
      relational_health:   { name:'关系健康', icon:'❤️',  threshold:0.5, action:'今天主动给一位关系有些疏远的人发一条简短消息，不带目的，只是关心。' },
      resilience:          { name:'韧性',    icon:'🌳', threshold:0.5, action:'找出本月一件让你感到气馁的事，写一句话：「神在这件事上想教我……」' },
      spiritual_clarity:   { name:'灵性清晰', icon:'✨', threshold:0.5, action:'今天安静10分钟，不读书不听音频，只问神：「祢今天最想对我说什么？」然后写下来。' },
      fear_tendency:       { name:'恐惧倾向', icon:'😨', threshold:0.4, action:'识别今天让你焦虑的一件具体事，写下：「最坏的结果是什么？神在最坏的结果里仍然是谁？」', inverse:true },
      pride_tendency:      { name:'骄傲倾向', icon:'🦅', threshold:0.4, action:'今天找一个机会主动赞美他人的优点，不加任何"但是"，看自己内心的感受。', inverse:true },
    }
    const sv2 = profile?.profile?.state_vector || {}
    const dimActions = Object.entries(DIM_ACTIONS)
      .filter(([key, cfg]) => {
        const score = sv2[key] ?? 0.5
        return cfg.inverse ? score > cfg.threshold : score < cfg.threshold
      })
      .slice(0, 3)
      .map(([key, cfg]) => ({ key, ...cfg }))

    return { catScores, overallAvg, maturityPct, maturityStage, topLessons, strongCats, shortPlan, midPlan, dimActions }
  }

  const formationAnalysis = computeFormationAnalysis()

  // 同步灵修计划到习惯养成
  const syncToHabits = async (planType) => {
    if (!formationAnalysis || !user) return
    const { shortPlan, midPlan } = formationAnalysis
    const planItems = planType === 'short' ? shortPlan : midPlan
    if (planItems.length === 0) return

    setSyncStatus('syncing')
    try {
      const token = getToken()
      const result = await createHabitsFromFormationPlan(
        user?.id || 'demo',
        planItems,
        planType,
        token
      )
      setSyncStatus('synced')
      // 调用父组件回调，通知切换到习惯页面
      onSyncToHabits?.()
      setTimeout(() => setSyncStatus(null), 3000)
    } catch (err) {
      console.error('[PersonalityPage] syncToHabits error:', err)
      setSyncStatus('error')
      setTimeout(() => setSyncStatus(null), 3000)
    }
  }

  // 生命分析面板组件（复用于三个tab）
  const FormationInsightPanel = () => {
    if (!formationAnalysis) return (
      <div style={{ background: 'rgba(255,255,255,0.04)', borderRadius: '14px', padding: '20px', marginBottom: '24px', textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: '14px' }}>
        📋 请先在「反思问题」标签完成问卷，此处将自动生成生命成熟度分析与灵修计划
      </div>
    )
    const { catScores, maturityPct, maturityStage, topLessons, strongCats, shortPlan, midPlan, dimActions } = formationAnalysis
    return (
      <div style={{ marginBottom: '28px' }}>
        {/* 成熟度总览 */}
        <div style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(59,130,246,0.12) 100%)', borderRadius: '16px', padding: '22px', marginBottom: '16px', border: '1px solid rgba(139,92,246,0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '28px' }}>{maturityStage.emoji}</span>
              <div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginBottom: '2px' }}>生命成熟度阶段</div>
                <div style={{ fontSize: '18px', fontWeight: 700, color: maturityStage.color }}>{maturityStage.label}</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>{maturityStage.desc}</div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '36px', fontWeight: 800, color: maturityStage.color, lineHeight: 1 }}>{maturityPct}%</div>
              <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginTop: '4px' }}>综合得分</div>
            </div>
          </div>
          {/* 成熟度条 */}
          <div style={{ height: '10px', background: 'rgba(255,255,255,0.08)', borderRadius: '5px', overflow: 'hidden', marginBottom: '16px' }}>
            <div style={{ height: '100%', width: `${maturityPct}%`, background: `linear-gradient(90deg, #8b5cf6, ${maturityStage.color})`, borderRadius: '5px', transition: 'width 0.8s ease' }} />
          </div>
          {/* 各类别得分条 */}
          <div style={{ display: 'grid', gap: '8px' }}>
            {catScores.map(c => (
              <div key={c.key} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '14px', width: '20px', flexShrink: 0 }}>{c.emoji}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.07)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: c.answered > 0 ? `${(c.avg / 10) * 100}%` : '0%', background: c.color, borderRadius: '3px', transition: 'width 0.6s ease' }} />
                  </div>
                </div>
                <span style={{ fontSize: '12px', color: c.color, fontWeight: 600, width: '30px', textAlign: 'right', flexShrink: 0 }}>
                  {c.answered > 0 ? `${c.avg.toFixed(1)}` : '—'}
                </span>
                <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', width: '70px', flexShrink: 0 }}>
                  {c.label.split('：')[0]}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 当前生命功课 */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
          <div style={{ background: 'rgba(248,113,113,0.08)', borderRadius: '14px', padding: '18px', border: '1px solid rgba(248,113,113,0.25)' }}>
            <div style={{ fontSize: '13px', color: '#f87171', fontWeight: 700, marginBottom: '10px' }}>🎯 当前生命功课</div>
            {topLessons.map(c => (
              <div key={c.key} style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '14px' }}>{c.emoji}</span>
                  <span style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>{c.lesson}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', paddingLeft: '20px' }}>{c.label.replace(/第.类：/, '')}</div>
              </div>
            ))}
          </div>
          <div style={{ background: 'rgba(74,222,128,0.08)', borderRadius: '14px', padding: '18px', border: '1px solid rgba(74,222,128,0.25)' }}>
            <div style={{ fontSize: '13px', color: '#4ade80', fontWeight: 700, marginBottom: '10px' }}>💪 生命强项</div>
            {strongCats.map(c => (
              <div key={c.key} style={{ marginBottom: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <span style={{ fontSize: '14px' }}>{c.emoji}</span>
                  <span style={{ fontSize: '13px', color: '#fff', fontWeight: 600 }}>{c.lesson}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', paddingLeft: '20px' }}>{c.avg.toFixed(1)} / 10分</div>
              </div>
            ))}
          </div>
        </div>

        {/* 今日可行一步 — 基于属灵维度 */}
        {dimActions && dimActions.length > 0 && (
          <div style={{ background: 'rgba(52,199,89,0.06)', borderRadius: '14px', padding: '18px 20px', marginBottom: '16px', border: '1px solid rgba(52,199,89,0.18)' }}>
            <div style={{ fontSize: '13px', color: '#34c759', fontWeight: 700, marginBottom: '12px' }}>🌿 今日可行一步 — 成长软肋行动</div>
            <div style={{ display: 'grid', gap: '10px' }}>
              {dimActions.map((d, i) => (
                <div key={d.key} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', padding: '10px 12px', background: 'rgba(0,0,0,0.18)', borderRadius: '10px', borderLeft: '3px solid rgba(52,199,89,0.4)' }}>
                  <span style={{ fontSize: '18px', flexShrink: 0 }}>{d.icon}</span>
                  <div>
                    <div style={{ fontSize: '11px', color: 'rgba(52,199,89,0.7)', fontWeight: 700, marginBottom: '3px' }}>{d.name}</div>
                    <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.78)', lineHeight: 1.6 }}>{d.action}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 灵修计划 */}
        <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '14px', padding: '20px', border: '1px solid rgba(255,255,255,0.08)' }}>
          <div style={{ fontSize: '14px', color: '#c4b5fd', fontWeight: 700, marginBottom: '16px' }}>📅 个人灵修操练计划</div>
          <div style={{ display: 'grid', gap: '16px' }}>
            {/* 短期 */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '10px', background: 'rgba(96,165,250,0.2)', color: '#60a5fa', fontWeight: 700 }}>短期 · 一个月</span>
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {shortPlan.map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                    <span style={{ flexShrink: 0, width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(96,165,250,0.2)', color: '#60a5fa', fontWeight: 700, fontSize: '11px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{i + 1}</span>
                    <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.6 }}>{item}</span>
                  </div>
                ))}
              </div>
            </div>
            {/* 中期 */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                <span style={{ fontSize: '11px', padding: '3px 10px', borderRadius: '10px', background: 'rgba(167,139,250,0.2)', color: '#a78bfa', fontWeight: 700 }}>中期 · 3–6个月</span>
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {midPlan.map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                    <span style={{ flexShrink: 0, width: '20px', height: '20px', borderRadius: '50%', background: 'rgba(167,139,250,0.2)', color: '#a78bfa', fontWeight: 700, fontSize: '11px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{i + 1}</span>
                    <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.6 }}>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          {/* 同步按钮 */}
          <div style={{ marginTop: '16px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              onClick={() => syncToHabits('short')}
              disabled={syncStatus === 'syncing' || shortPlan.length === 0}
              style={{
                flex: 1,
                minWidth: '140px',
                padding: '10px 16px',
                borderRadius: '10px',
                border: 'none',
                background: syncStatus === 'syncing' ? 'rgba(120,120,128,0.3)' : 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
                color: '#fff',
                fontSize: '13px',
                fontWeight: 600,
                cursor: syncStatus === 'syncing' || shortPlan.length === 0 ? 'not-allowed' : 'pointer',
                opacity: shortPlan.length === 0 ? 0.5 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              {syncStatus === 'syncing' ? '⏳ 同步中...' : '🌱 同步短期计划到习惯'}
            </button>
            <button
              onClick={() => syncToHabits('mid')}
              disabled={syncStatus === 'syncing' || midPlan.length === 0}
              style={{
                flex: 1,
                minWidth: '140px',
                padding: '10px 16px',
                borderRadius: '10px',
                border: '1px solid rgba(139,92,246,0.5)',
                background: syncStatus === 'syncing' ? 'rgba(120,120,128,0.3)' : 'rgba(139,92,246,0.15)',
                color: '#c4b5fd',
                fontSize: '13px',
                fontWeight: 600,
                cursor: syncStatus === 'syncing' || midPlan.length === 0 ? 'not-allowed' : 'pointer',
                opacity: midPlan.length === 0 ? 0.5 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
              }}
            >
              {syncStatus === 'syncing' ? '⏳ 同步中...' : '📅 同步中期计划到习惯'}
            </button>
          </div>

          {/* 同步状态提示 */}
          {syncStatus === 'synced' && (
            <div style={{ marginTop: '10px', padding: '8px 12px', background: 'rgba(34,197,94,0.15)', borderRadius: '8px', color: '#4ade80', fontSize: '12px', textAlign: 'center' }}>
              ✅ 已成功同步到习惯养成！请在习惯页面查看并执行。
            </div>
          )}
          {syncStatus === 'error' && (
            <div style={{ marginTop: '10px', padding: '8px 12px', background: 'rgba(239,68,68,0.15)', borderRadius: '8px', color: '#f87171', fontSize: '12px', textAlign: 'center' }}>
              ⚠️ 同步失败，请检查网络或登录状态后重试。
            </div>
          )}

          <div style={{ marginTop: '12px', fontSize: '11px', color: 'rgba(255,255,255,0.3)', borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '12px' }}>
            💡 计划基于你的反思问卷得分自动生成。每3–6个月重做问卷，计划将随生命成长自动更新。
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ 
      padding: embedded ? '0' : '20px',
      maxWidth: '1200px',
      margin: '0 auto'
    }}>
      {/* 头部 */}
      <div style={{ 
        background: 'linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(59,130,246,0.2) 100%)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        border: '1px solid rgba(139,92,246,0.3)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <div style={{ fontSize: '48px' }}>🔮</div>
          <div>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 600, color: '#fff' }}>
              人格塑造
            </h2>
            <p style={{ margin: '4px 0 0 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              性格轨迹分析 · 不是静态分数，而是动态信号
            </p>
          </div>
        </div>

        {/* 核心指标卡片 */}
        {(() => {
          const dataPoints = profile?.profile?.data_points || 0
          const hasData = dataPoints > 0
          if (!hasData) {
            return (
              <div style={{
                marginTop: '20px',
                padding: '20px',
                background: 'rgba(139,92,246,0.08)',
                borderRadius: '14px',
                border: '1px dashed rgba(139,92,246,0.35)',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '10px' }}>🌱</div>
                <div style={{ color: '#c4b5fd', fontWeight: 600, fontSize: '15px', marginBottom: '8px' }}>
                  尚无人格塑造数据
                </div>
                <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px', lineHeight: 1.7 }}>
                  形成弧线、轨迹方向、主导循环等指标需要通过<strong style={{ color: 'rgba(255,255,255,0.75)' }}>情感打卡</strong>或<strong style={{ color: 'rgba(255,255,255,0.75)' }}>决策分析</strong>积累数据后自动生成。<br/>
                  每次打卡都会写入一条成长记录，积累足够数据后此处将显示你的性格轨迹。
                </div>
              </div>
            )
          }
          return (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px',
              marginTop: '20px'
            }}>
              <div style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '12px',
                padding: '16px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>{arc.emoji}</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>形成弧线</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>{arc.text}</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>{arc.desc}</div>
              </div>

              <div style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '12px',
                padding: '16px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>{trajectory.emoji}</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>轨迹方向</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: trajectory.color }}>{trajectory.text}</div>
              </div>

              <div style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '12px',
                padding: '16px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔄</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>主导循环</div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
                  {getDominantLoop() === 'none' ? '积累中...' : getDominantLoop()}
                </div>
              </div>

              <div style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '12px',
                padding: '16px',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '32px', marginBottom: '8px' }}>📊</div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '4px' }}>数据点数</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>
                  {dataPoints}
                </div>
              </div>
            </div>
          )
        })()}
      </div>

      {/* 子标签页 */}
      <div style={{ 
        display: 'flex', 
        gap: '8px', 
        marginBottom: '24px',
        flexWrap: 'wrap'
      }}>
        {[
          { key: 'reflection', label: '反思问题', emoji: '�' },
          { key: 'dimensions', label: '维度分析', emoji: '🎯' },
          { key: 'loops', label: '循环模式', emoji: '🔄' },
          { key: 'overview', label: '总览', emoji: '�' }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '10px 20px',
              borderRadius: '20px',
              border: 'none',
              background: activeTab === tab.key 
                ? 'linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%)' 
                : 'rgba(255,255,255,0.1)',
              color: '#fff',
              fontSize: '12px',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* 内容区域 */}
      {activeTab === 'overview' && (
        <div>
          <FormationInsightPanel />
          {/* 8维雷达图说明 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🎯 八维性格轨迹向量
            </h3>
            <p style={{ margin: '0 0 20px 0', color: 'rgba(255,255,255,0.6)', fontSize: '14px' }}>
              这些数值表示行为倾向（0.05-0.95），不是道德评分。0.5是基线，偏离表示倾向性。
            </p>

            <div style={{ 
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
              gap: '16px'
            }}>
              {Object.entries(dimensionNames).map(([key, name]) => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                
                return (
                  <div 
                    key={key}
                    style={{
                      background: 'rgba(0,0,0,0.2)',
                      borderRadius: '12px',
                      padding: '16px',
                      borderLeft: `4px solid ${color}`
                    }}
                  >
                    <div style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '8px'
                    }}>
                      <span style={{ color: '#fff', fontWeight: 500 }}>{name}</span>
                      <span style={{ 
                        color: color,
                        fontWeight: 600,
                        fontSize: '16px'
                      }}>
                        {(score * 100).toFixed(2)}%
                      </span>
                    </div>
                    
                    {/* 进度条 */}
                    <div style={{
                      height: '8px',
                      background: 'rgba(255,255,255,0.1)',
                      borderRadius: '4px',
                      overflow: 'hidden',
                      marginBottom: '8px'
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${score * 100}%`,
                        background: `linear-gradient(90deg, ${color}80, ${color})`,
                        borderRadius: '4px',
                        transition: 'width 0.5s ease'
                      }}/>
                    </div>

                    {/* 基线标记 */}
                    <div style={{ position: 'relative', height: '4px' }}>
                      <div style={{
                        position: 'absolute',
                        left: '50%',
                        top: '-6px',
                        width: '2px',
                        height: '10px',
                        background: 'rgba(255,255,255,0.3)',
                        transform: 'translateX(-50%)'
                      }}/>
                    </div>

                    {/* 变化指示 */}
                    {delta !== 0 && (
                      <div style={{ 
                        marginTop: '8px',
                        fontSize: '12px',
                        color: delta > 0 ? '#4ade80' : '#f87171'
                      }}>
                        {delta > 0 ? '↗' : '↘'} {Math.abs(delta * 100).toFixed(2)}%
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 免责声明 */}
          <div style={{
            background: 'rgba(251,191,36,0.1)',
            borderRadius: '12px',
            padding: '16px',
            border: '1px solid rgba(251,191,36,0.3)'
          }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
              <span style={{ fontSize: '20px' }}>⚠️</span>
              <div>
                <div style={{ fontWeight: 600, color: '#fbbf24', marginBottom: '4px' }}>重要声明</div>
                <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
                  人格塑造系统提供的是结构化的反思镜像，而非精神权威。所有洞察都是概率性的。
                  人类的自由、恩典和奥秘总是超越任何模型所能捕捉的。这不是道德评判，而是轨迹信号。
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'dimensions' && (
        <div>
          <FormationInsightPanel />
          {/* 分组说明 */}
          <div style={{
            background: 'rgba(99,102,241,0.12)',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '24px',
            border: '1px solid rgba(99,102,241,0.3)',
            fontSize: '13px',
            color: 'rgba(255,255,255,0.7)',
            lineHeight: 1.6
          }}>
            <strong style={{ color: '#818cf8' }}>📌 维度解读说明：</strong> 所有数值为行为倾向（0.05–0.95），<strong>0.5 是基线</strong>。健康维度越高越好；循环倾向维度越低越健康。变化方向（↗↘）反映近期趋势，不是终身标签。
          </div>

          {/* 健康维度组 */}
          <div style={{ marginBottom: '32px' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              marginBottom: '16px'
            }}>
              <span style={{ fontSize: '18px' }}>🌱</span>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#4ade80', fontWeight: 600 }}>健康成长维度</h3>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginLeft: '4px' }}>越高越好</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {['humility', 'emotional_stability', 'truth_alignment', 'relational_health', 'resilience', 'spiritual_clarity'].map(key => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                const dimInfo = dimensions.find(d => d.key === key) || {}
                const name = dimensionNames[key]
                const pct = Math.round(score * 100)
                const isHigh = score >= 0.65
                const isLow = score <= 0.35
                const statusLabel = isHigh ? { text: '强', color: '#4ade80' } : isLow ? { text: '待培育', color: '#f87171' } : { text: '基线', color: '#fbbf24' }
                return (
                  <div key={key} style={{
                    background: 'rgba(0,0,0,0.25)',
                    borderRadius: '14px',
                    padding: '18px',
                    borderLeft: `4px solid ${color}`,
                    position: 'relative'
                  }}>
                    {/* 标题行 */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color }} />
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '15px' }}>{name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {delta !== 0 && (
                          <span style={{ fontSize: '12px', color: delta > 0 ? '#4ade80' : '#f87171', fontWeight: 600 }}>
                            {delta > 0 ? '↗' : '↘'}{Math.abs(delta * 100).toFixed(2)}%
                          </span>
                        )}
                        <span style={{
                          fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
                          background: `${statusLabel.color}25`, color: statusLabel.color, fontWeight: 600
                        }}>{statusLabel.text}</span>
                        <span style={{ color: color, fontWeight: 700, fontSize: '18px' }}>{(score * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                    {/* 进度条 */}
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${color}70, ${color})`, borderRadius: '4px', transition: 'width 0.6s ease' }} />
                      {/* 基线标记 */}
                      <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: 'rgba(255,255,255,0.25)' }} />
                    </div>
                    {/* 描述 */}
                    {dimInfo.description && (
                      <p style={{ margin: '0 0 10px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: 1.5 }}>
                        {dimInfo.description}
                      </p>
                    )}
                    {/* 反思问题 */}
                    {dimInfo.reflective_question && (
                      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
                        💭 {dimInfo.reflective_question}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 循环倾向维度组 */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
              <span style={{ fontSize: '18px' }}>⚠️</span>
              <h3 style={{ margin: 0, fontSize: '16px', color: '#f87171', fontWeight: 600 }}>循环倾向维度</h3>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)', marginLeft: '4px' }}>越低越健康</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
              {['fear_tendency', 'pride_tendency'].map(key => {
                const score = getDimensionScore(key)
                const color = dimensionColors[key]
                const delta = profile?.profile?.deltas?.[key] || 0
                const dimInfo = dimensions.find(d => d.key === key) || {}
                const name = dimensionNames[key]
                const pct = Math.round(score * 100)
                const isHigh = score >= 0.65
                const isLow = score <= 0.35
                const statusLabel = isHigh ? { text: '活跃', color: '#f87171' } : isLow ? { text: '受控', color: '#4ade80' } : { text: '基线', color: '#fbbf24' }
                return (
                  <div key={key} style={{
                    background: 'rgba(0,0,0,0.25)',
                    borderRadius: '14px',
                    padding: '18px',
                    borderLeft: `4px solid ${color}`
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: color }} />
                        <span style={{ color: '#fff', fontWeight: 600, fontSize: '15px' }}>{name}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {delta !== 0 && (
                          <span style={{ fontSize: '12px', color: delta > 0 ? '#f87171' : '#4ade80', fontWeight: 600 }}>
                            {delta > 0 ? '↗' : '↘'}{Math.abs(delta * 100).toFixed(2)}%
                          </span>
                        )}
                        <span style={{
                          fontSize: '11px', padding: '2px 8px', borderRadius: '10px',
                          background: `${statusLabel.color}25`, color: statusLabel.color, fontWeight: 600
                        }}>{statusLabel.text}</span>
                        <span style={{ color: color, fontWeight: 700, fontSize: '18px' }}>{(score * 100).toFixed(2)}%</span>
                      </div>
                    </div>
                    <div style={{ height: '8px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '10px', position: 'relative' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: `linear-gradient(90deg, ${color}70, ${color})`, borderRadius: '4px', transition: 'width 0.6s ease' }} />
                      <div style={{ position: 'absolute', left: '50%', top: 0, width: '2px', height: '100%', background: 'rgba(255,255,255,0.25)' }} />
                    </div>
                    {dimInfo.description && (
                      <p style={{ margin: '0 0 10px 0', color: 'rgba(255,255,255,0.6)', fontSize: '13px', lineHeight: 1.5 }}>
                        {dimInfo.description}
                      </p>
                    )}
                    {dimInfo.reflective_question && (
                      <div style={{ background: 'rgba(255,255,255,0.05)', borderRadius: '8px', padding: '10px 12px', fontSize: '12px', color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>
                        💭 {dimInfo.reflective_question}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* 维度对比分析 */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.12) 100%)',
            borderRadius: '14px',
            padding: '20px',
            border: '1px solid rgba(139,92,246,0.25)'
          }}>
            <h4 style={{ margin: '0 0 12px 0', color: '#c4b5fd', fontSize: '15px' }}>� 维度对比分析</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
              {[
                { label: '最强维度', value: (() => { const entries = Object.entries(dimensionNames); const best = entries.filter(([k]) => !['fear_tendency','pride_tendency'].includes(k)).sort(([a],[b]) => getDimensionScore(b) - getDimensionScore(a))[0]; return best ? `${best[1]} (${(getDimensionScore(best[0])*100).toFixed(2)}%)` : '—' })(), color: '#4ade80' },
                { label: '最需培育', value: (() => { const entries = Object.entries(dimensionNames); const worst = entries.filter(([k]) => !['fear_tendency','pride_tendency'].includes(k)).sort(([a],[b]) => getDimensionScore(a) - getDimensionScore(b))[0]; return worst ? `${worst[1]} (${(getDimensionScore(worst[0])*100).toFixed(2)}%)` : '—' })(), color: '#f87171' },
                { label: '最活跃循环倾向', value: (() => { const fear = getDimensionScore('fear_tendency'); const pride = getDimensionScore('pride_tendency'); return fear > pride ? `恐惧倾向 (${(fear*100).toFixed(2)}%)` : `骄傲倾向 (${(pride*100).toFixed(2)}%)` })(), color: '#f87171' },
                { label: '健康维度平均', value: (() => { const healthy = ['humility','emotional_stability','truth_alignment','relational_health','resilience','spiritual_clarity']; const avg = healthy.reduce((s, k) => s + getDimensionScore(k), 0) / healthy.length; return `${(avg*100).toFixed(2)}%` })(), color: '#60a5fa' },
              ].map(item => (
                <div key={item.label} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '10px', padding: '12px' }}>
                  <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginBottom: '4px' }}>{item.label}</div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: item.color }}>{item.value}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'loops' && (
        <div>
          <FormationInsightPanel />

          {/* 轨迹状态解读 */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(59,130,246,0.15) 100%)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px',
            border: '1px solid rgba(139,92,246,0.3)'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🧭 当前轨迹状态
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>形成弧线</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '28px' }}>{arc.emoji}</span>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>{arc.text}</div>
                    <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginTop: '2px' }}>{arc.desc}</div>
                  </div>
                </div>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>轨迹方向</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '28px' }}>{trajectory.emoji}</span>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: 600, color: trajectory.color }}>{trajectory.text}</div>
                  </div>
                </div>
              </div>
              <div style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '12px', padding: '16px' }}>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>主导循环</div>
                <div style={{ fontSize: '16px', fontWeight: 600, color: getDominantLoop() === 'none' ? 'rgba(255,255,255,0.3)' : '#f6ad55' }}>
                  {getDominantLoop() === 'none' ? '数据积累中...' : getDominantLoop().replace(/_/g, ' ')}
                </div>
              </div>
            </div>
          </div>

          {/* 五种循环模式详解 */}
          <div style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '24px'
          }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '18px', color: '#fff' }}>
              🔄 五种行为循环模式
            </h3>

            <div style={{ display: 'grid', gap: '16px' }}>
              {[
                {
                  key: 'fear_control_loop',
                  name: '恐惧控制循环',
                  chain: ['恐惧', '控制', '过度工作', '燃尽', '恐惧'],
                  triggers: ['未知结果', '失去掌控感', '完美主义'],
                  response: '觉察恐惧源头，练习交托祷告，设定边界',
                  color: '#f87171'
                },
                {
                  key: 'shame_avoidance_loop',
                  name: '羞耻回避循环',
                  chain: ['羞耻', '回避', '拖延', '焦虑', '羞耻'],
                  triggers: ['失败经历', '被评价', '暴露脆弱'],
                  response: '在基督里领受完全接纳，小步面对而非逃避',
                  color: '#fb923c'
                },
                {
                  key: 'pride_comparison_loop',
                  name: '骄傲比较循环',
                  chain: ['骄傲', '比较', '焦虑', '不稳定', '骄傲'],
                  triggers: ['他人成功', '身份受威胁', '优越感受损'],
                  response: '默想十架谦卑，专注神眼中的价值',
                  color: '#fbbf24'
                },
                {
                  key: 'desire_impulse_loop',
                  name: '欲望冲动循环',
                  chain: ['欲望', '冲动行为', '后悔', '欲望'],
                  triggers: ['即时满足诱惑', '逃避痛苦', '习惯性渴求'],
                  response: '暂停10秒，默想永恒奖赏，寻求圣灵大能',
                  color: '#a78bfa'
                },
                {
                  key: 'truth_stability_loop',
                  name: '真理稳定循环',
                  chain: ['面对真理', '反思', '稳定', '成长', '面对真理'],
                  triggers: ['诚实面对自己', '接纳光照', '悔改更新'],
                  response: '保持透明，持续省察，在恩典中成长',
                  color: '#4ade80',
                  healthy: true
                }
              ].map(loop => (
                <div
                  key={loop.key}
                  style={{
                    background: getDominantLoop() === loop.key
                      ? `${loop.color}18`
                      : 'rgba(0,0,0,0.2)',
                    borderRadius: '14px',
                    padding: '20px',
                    border: getDominantLoop() === loop.key
                      ? `2px solid ${loop.color}`
                      : '1px solid rgba(255,255,255,0.08)'
                  }}
                >
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    marginBottom: '14px'
                  }}>
                    <span style={{
                      fontSize: '11px',
                      padding: '4px 10px',
                      borderRadius: '12px',
                      background: loop.color,
                      color: '#000',
                      fontWeight: 700
                    }}>
                      {getDominantLoop() === loop.key ? '● 当前主导' : loop.healthy ? '✓ 健康' : '循环'}
                    </span>
                    <span style={{ color: '#fff', fontWeight: 600, fontSize: '16px' }}>{loop.name}</span>
                  </div>

                  {/* 循环链条可视化 */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '14px' }}>
                    {loop.chain.map((step, i) => (
                      <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '12px',
                          padding: '6px 10px',
                          borderRadius: '8px',
                          background: i === loop.chain.length - 1 ? 'rgba(255,255,255,0.08)' : `${loop.color}25`,
                          color: i === loop.chain.length - 1 ? 'rgba(255,255,255,0.5)' : loop.color,
                          fontWeight: 500
                        }}>
                          {step}
                        </span>
                        {i < loop.chain.length - 1 && (
                          <span style={{ color: loop.color, fontSize: '14px' }}>→</span>
                        )}
                      </span>
                    ))}
                  </div>

                  {/* 触发条件与应对 */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
                    <div>
                      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '4px' }}>常见触发</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {loop.triggers.map((t, i) => (
                          <span key={i} style={{ fontSize: '11px', color: loop.color, background: `${loop.color}15`, padding: '3px 8px', borderRadius: '6px' }}>
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.4)', marginBottom: '4px' }}>应对方向</div>
                      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)' }}>{loop.response}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 个人循环记录区域 */}
          <div style={{
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '16px',
            padding: '24px',
            border: '1px dashed rgba(255,255,255,0.15)'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: 'rgba(255,255,255,0.7)' }}>
              📝 我的循环觉察记录
            </h3>
            <div style={{ textAlign: 'center', padding: '24px', color: 'rgba(255,255,255,0.4)', fontSize: '13px' }}>
              <div style={{ marginBottom: '8px' }}>💭</div>
              <div>循环觉察功能即将上线</div>
              <div style={{ fontSize: '11px', marginTop: '4px' }}>记录你观察到的循环模式，追踪突破进度</div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'reflection' && (
        <div>
          {/* 目的说明 */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(59,130,246,0.15) 100%)',
            borderRadius: '16px',
            padding: '24px',
            marginBottom: '20px',
            border: '1px solid rgba(139,92,246,0.3)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', color: '#fff' }}>
                💭 灵性塑造反思问卷
              </h3>
              {saveStatus === 'saved' && (
                <span style={{ fontSize: '12px', color: '#4ade80', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  ✓ 已保存
                </span>
              )}
              {saveStatus === 'error' && (
                <span style={{ fontSize: '12px', color: '#f87171', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  ✗ 保存失败
                </span>
              )}
            </div>
            <p style={{ margin: '0 0 16px 0', color: 'rgba(255,255,255,0.85)', fontSize: '14px', lineHeight: 1.8 }}>
              神在你生命中特别要塑造你成为耶稣基督那样慈爱怜悯、柔和谦卑、舍己爱人、俯就卑微的罪人，完全顺服天父的旨意这样的品格。要对付的根源问题，或要学习的功课（如信靠、饶恕、顺服、谦卑等）。透过一套有结构的自省题目，你可以系统地找出重复模式、试炼焦点与盲点，帮助你明白神目前的「功课」是什么。
            </p>

            {/* 操作指引 */}
            <div style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '12px',
              padding: '16px 18px',
              marginBottom: '16px'
            }}>
              <div style={{ fontSize: '13px', color: '#a78bfa', fontWeight: 600, marginBottom: '10px' }}>🙏 开始前</div>
              <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', lineHeight: 1.7 }}>
                用祷告开始（诗篇139:23-24），求圣灵光照。
              </div>
              <div style={{ marginTop: '12px', fontSize: '13px', color: '#a78bfa', fontWeight: 600, marginBottom: '10px' }}>📝 作答原则</div>
              <div style={{ display: 'grid', gap: '6px' }}>
                {[
                  '诚实回答，不急着写「正确答案」。',
                  '写下具体例子。',
                  '完成后找出共同主题（例如多次提到「愤怒」或「不信」），那很可能就是当前生命功课。',
                  '每3–6个月重做一次，观察变化。'
                ].map((tip, i) => (
                  <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '13px', color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                    <span style={{ color: '#a78bfa', flexShrink: 0 }}>·</span>
                    <span>{tip}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 重要提醒 */}
            <div style={{
              background: 'rgba(251,191,36,0.08)',
              borderRadius: '12px',
              padding: '16px 18px',
              border: '1px solid rgba(251,191,36,0.25)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <span style={{ fontSize: '16px' }}>⚠️</span>
                <span style={{ color: '#fbbf24', fontWeight: 700, fontSize: '13px' }}>重要提醒</span>
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {[
                  { ref: '罗马书12:2', text: '这不是为了自我定罪，而是邀请神来更新。' },
                  { ref: '希伯来书12:5-11', text: '生命功课常在重复的痛苦或试炼中显露，神是用爱来修剪。' },
                  { ref: '加拉太书5:16', text: '靠恩典而行：认清功课后，立刻认罪、接受赦免，并倚靠圣灵改变。' },
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'flex-start' }}>
                    <span style={{ flexShrink: 0, fontSize: '13px', color: '#fbbf24', marginTop: '1px' }}>·</span>
                    <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.75)', lineHeight: 1.65 }}>
                      {item.text}
                      <span style={{ marginLeft: '6px', fontSize: '12px', color: 'rgba(251,191,36,0.6)' }}>（{item.ref}）</span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* 分析与应用步骤 */}
            <div style={{
              background: 'rgba(0,0,0,0.2)',
              borderRadius: '12px',
              padding: '16px 18px'
            }}>
              <div style={{ fontSize: '13px', color: '#60a5fa', fontWeight: 600, marginBottom: '10px' }}>🔍 分析与应用步骤（逻辑归纳）</div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {[
                  { n: '1', text: '找出模式：哪些题目你的答案最负面或最常出现同一主题？' },
                  { n: '2', text: '连结圣经：针对该主题查考相关经文（例如若是不饶恕，就看马太福音6:14-15）。' },
                  { n: '3', text: '写下当前生命功课：例如「神要我学习在工作中信靠祂的供应，而不是忧虑」。' },
                  { n: '4', text: '制定行动：用生命之轮或之前的地图，设计具体操练（例如每日为该功课用ACTS祷告）。' },
                  { n: '5', text: '找人确认：与成熟基督徒或小组分享，让他们帮助你看见可能忽略的盲点。' },
                ].map(step => (
                  <div key={step.n} style={{ display: 'flex', gap: '10px', fontSize: '13px', color: 'rgba(255,255,255,0.65)', lineHeight: 1.6 }}>
                    <span style={{
                      flexShrink: 0,
                      width: '20px', height: '20px',
                      borderRadius: '50%',
                      background: 'rgba(96,165,250,0.25)',
                      color: '#60a5fa',
                      fontWeight: 700,
                      fontSize: '11px',
                      display: 'flex', alignItems: 'center', justifyContent: 'center'
                    }}>{step.n}</span>
                    <span>{step.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 频率说明 */}
          <div style={{
            display: 'flex', gap: '16px', flexWrap: 'wrap',
            padding: '12px 16px',
            background: 'rgba(255,255,255,0.04)',
            borderRadius: '10px',
            marginBottom: '20px'
          }}>
            <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.45)', alignSelf: 'center' }}>标记频率：</span>
            {FREQUENCY_OPTIONS.map(opt => (
              <div key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: opt.color }} />
                <span style={{ fontSize: '13px', color: opt.color, fontWeight: 600 }}>{opt.label}</span>
                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>{opt.desc}</span>
              </div>
            ))}
          </div>

          {REFLECTION_CATEGORIES.map((cat, catIdx) => {
            const catAnswered = cat.questions.filter((_, qi) => reflectionAnswers[`${cat.key}_${qi}`] !== undefined).length
            return (
              <div key={cat.key} style={{
                background: 'rgba(0,0,0,0.2)',
                borderRadius: '16px',
                padding: '24px',
                marginBottom: '20px',
                borderLeft: `4px solid ${cat.color}`
              }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '22px' }}>{cat.emoji}</span>
                    <span style={{ color: cat.color, fontWeight: 700, fontSize: '15px' }}>{cat.label}</span>
                  </div>
                  <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                    {catAnswered}/{cat.questions.length}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)', marginBottom: '18px', paddingLeft: '32px' }}>
                  可能功课：{cat.lesson}
                </div>

                <div style={{ display: 'grid', gap: '14px' }}>
                  {cat.questions.map((q, qi) => {
                    const ansKey = `${cat.key}_${qi}`
                    const chosen = reflectionAnswers[ansKey]
                    return (
                      <div key={qi} style={{
                        background: 'rgba(255,255,255,0.04)',
                        borderRadius: '12px',
                        padding: '16px 18px',
                        border: chosen !== undefined
                          ? `1px solid ${FREQUENCY_OPTIONS.find(o => o.value === chosen)?.color}60`
                          : '1px solid rgba(255,255,255,0.08)'
                      }}>
                        <div style={{
                          fontSize: '14px',
                          color: 'rgba(255,255,255,0.9)',
                          lineHeight: 1.65,
                          marginBottom: '14px'
                        }}>
                          <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: '12px', marginRight: '8px' }}>
                            Q{catIdx * 4 + qi + 1}
                          </span>
                          {q}
                        </div>
                        {(() => {
                          const sliderVal = chosen ?? 0
                          const activeOpt = sliderVal === 0 ? null
                            : sliderVal <= 3 ? FREQUENCY_OPTIONS[2]
                            : sliderVal <= 7 ? FREQUENCY_OPTIONS[1]
                            : FREQUENCY_OPTIONS[0]
                          const trackColor = activeOpt?.color ?? 'rgba(255,255,255,0.15)'
                          const pct = sliderVal === 0 ? 0 : ((sliderVal - 1) / 9) * 100
                          return (
                            <div>
                              {/* 区段标签 */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                {[
                                  { label: '🌱盲点', range: '1–3', color: '#f87171' },
                                  { label: '🌿成长中', range: '4–7', color: '#fbbf24' },
                                  { label: '🌳稳定操练', range: '8–10', color: '#4ade80' },
                                ].map(z => (
                                  <span key={z.label} style={{
                                    fontSize: '11px', color: z.color,
                                    opacity: activeOpt?.label === z.label ? 1 : 0.35,
                                    fontWeight: activeOpt?.label === z.label ? 700 : 400,
                                    transition: 'all 0.2s'
                                  }}>
                                    {z.label} <span style={{ color: 'rgba(255,255,255,0.3)', fontWeight: 400 }}>{z.range}</span>
                                  </span>
                                ))}
                              </div>
                              {/* 滑条 */}
                              <div style={{ position: 'relative', height: '36px', display: 'flex', alignItems: 'center' }}>
                                {/* 彩色背景轨道 */}
                                <div style={{
                                  position: 'absolute', left: 0, right: 0, height: '8px',
                                  borderRadius: '4px', overflow: 'hidden',
                                  background: 'linear-gradient(to right, #f87171 0%, #f87171 27%, #fbbf24 27%, #fbbf24 63%, #4ade80 63%, #4ade80 100%)',
                                  opacity: 0.35
                                }} />
                                {/* 已选填充 */}
                                {sliderVal > 0 && (
                                  <div style={{
                                    position: 'absolute', left: 0, height: '8px',
                                    width: `${pct}%`,
                                    borderRadius: '4px',
                                    background: trackColor,
                                    transition: 'width 0.15s, background 0.2s'
                                  }} />
                                )}
                                {/* 刻度点 */}
                                {[1,2,3,4,5,6,7,8,9,10].map(v => (
                                  <div key={v} style={{
                                    position: 'absolute',
                                    left: `${((v - 1) / 9) * 100}%`,
                                    transform: 'translateX(-50%)',
                                    width: '4px', height: '4px',
                                    borderRadius: '50%',
                                    background: sliderVal >= v
                                      ? trackColor
                                      : 'rgba(255,255,255,0.2)',
                                    transition: 'background 0.15s',
                                    pointerEvents: 'none'
                                  }} />
                                ))}
                                {/* range input (透明覆盖) */}
                                <input
                                  type="range"
                                  min="0"
                                  max="10"
                                  value={sliderVal}
                                  onChange={e => {
                                    const v = parseInt(e.target.value)
                                    const next = { ...reflectionAnswers, [ansKey]: v === 0 ? undefined : v }
                                    if (v === 0) delete next[ansKey]
                                    setReflectionAnswers(next)
                                    debouncedSave(next)
                                  }}
                                  style={{
                                    position: 'absolute', left: 0, right: 0,
                                    width: '100%', height: '36px',
                                    opacity: 0, cursor: 'pointer',
                                    margin: 0, padding: 0,
                                    WebkitAppearance: 'none'
                                  }}
                                />
                              </div>
                              {/* 当前值显示 */}
                              <div style={{ textAlign: 'right', marginTop: '4px', height: '18px' }}>
                                {activeOpt && (
                                  <span style={{ fontSize: '12px', color: trackColor, fontWeight: 600, transition: 'color 0.2s' }}>
                                    {activeOpt.label}　<span style={{ color: 'rgba(255,255,255,0.3)', fontWeight: 400 }}>{sliderVal}分</span>
                                  </span>
                                )}
                              </div>
                            </div>
                          )
                        })()}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* 答题进度汇总 */}
          {(() => {
            const total = REFLECTION_CATEGORIES.reduce((s, c) => s + c.questions.length, 0)
            const answered = Object.keys(reflectionAnswers).filter(k => reflectionAnswers[k] !== undefined).length
            const pct = Math.round((answered / total) * 100)
            if (answered === 0) return null
            const freqCounts = FREQUENCY_OPTIONS.reduce((acc, o) => {
              acc[o.label] = Object.values(reflectionAnswers).filter(v => v === o.value).length
              return acc
            }, {})
            return (
              <div style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.12) 0%, rgba(59,130,246,0.12) 100%)',
                borderRadius: '14px',
                padding: '20px',
                border: '1px solid rgba(139,92,246,0.25)'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span style={{ color: '#c4b5fd', fontWeight: 600, fontSize: '15px' }}>📋 答题汇总</span>
                  <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>{answered}/{total} 题</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
                  <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, #8b5cf6, #3b82f6)', borderRadius: '4px', transition: 'width 0.4s ease' }} />
                </div>
                <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  {FREQUENCY_OPTIONS.map(opt => (
                    <div key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: opt.color }} />
                      <span style={{ color: opt.color, fontWeight: 600, fontSize: '14px' }}>{opt.label}</span>
                      <span style={{ color: 'rgba(255,255,255,0.5)', fontSize: '14px' }}>{freqCounts[opt.label]} 题</span>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
