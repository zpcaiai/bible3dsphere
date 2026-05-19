import { useEffect, useState } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'

const sfdsUrl = (path) => `${API_BASE}/sfds${path}`
const MVFE_BASE = API_BASE + '/mvfe'

const QUICK_PROMPTS = [
  {t:'最近工作压力很大，总是担心做不好，想逃避...',e:'😰',l:'焦虑逃避'},
  {t:'今天内心很平静，和家人一起很感恩...',e:'😌',l:'平静感恩'},
  {t:'感觉被忽视了，有点生气又不知道怎么表达...',e:'😤',l:'被忽视'},
  {t:'对未来充满期待，想尝试新的事情...',e:'✨',l:'充满期待'},
  {t:'一直在同一件事上反复纠结，走不出来...',e:'🔄',l:'反复纠结'},
]

// ==================== 现代生活决策类别（12大类，覆盖人生主要领域）====================
const decisionCategories = [
  // 职业与发展
  { value: 'career', label: '职业/工作', emoji: '💼', desc: '换工作、升职、创业、离职、职业规划' },
  { value: 'education', label: '教育/学习', emoji: '📚', desc: '升学、留学、进修、专业选择、技能学习' },
  { value: 'calling', label: '呼召/使命', emoji: '🎯', desc: '全职服事、跨文化宣教、蒙召确认' },
  
  // 人际关系
  { value: 'relationship', label: '人际关系', emoji: '💕', desc: '恋爱、婚姻、家庭、朋友、冲突处理' },
  { value: 'family', label: '家庭/亲子', emoji: '👨‍👩‍👧‍👦', desc: '育儿、夫妻关系、原生家庭、赡养老人' },
  { value: 'community', label: '社群/教会', emoji: '⛪', desc: '小组参与、教会选择、服事分工、人际边界' },
  
  // 资源管理
  { value: 'financial', label: '财务/金钱', emoji: '💰', desc: '投资、消费、债务、奉献、财务规划' },
  { value: 'housing', label: '居住/房产', emoji: '🏠', desc: '买房、租房、装修、搬家、选址' },
  { value: 'possessions', label: '物品/消费', emoji: '📱', desc: '大额消费、断舍离、购物诱惑、资产管理' },
  
  // 身心健康
  { value: 'health', label: '健康/身体', emoji: '🏥', desc: '就医、治疗、体检、生活方式改变' },
  { value: 'mental', label: '心理/情绪', emoji: '🧠', desc: '心理咨询、情绪管理、压力应对、休息安排' },
  
  // 灵性与道德
  { value: 'temptation', label: '试探/诱惑', emoji: '⚠️', desc: '道德抉择、犯罪边缘、成瘾行为、灰色地带' },
  { value: 'spiritual', label: '灵修/信仰', emoji: '🙏', desc: '灵修习惯、信仰怀疑、神学问题、属灵追求' },
  { value: 'ministry', label: '事工/服事', emoji: '🤝', desc: '服事平衡、领袖角色、团队冲突、禾场选择' },
  
  // 时间与生活方式
  { value: 'time', label: '时间/节奏', emoji: '⏰', desc: '工作与生活平衡、安息、优先级排序' },
  { value: 'lifestyle', label: '生活方式', emoji: '🌱', desc: '饮食习惯、运动、社交方式、数字健康' },
  { value: 'boundary', label: '边界/拒绝', emoji: '🚧', desc: '说"不"、设立界限、拒绝请求、保护自己' },
  
  // 危机与转变
  { value: 'crisis', label: '危机/急难', emoji: '🚨', desc: '突发事件、危机应对、紧急抉择' },
  { value: 'transition', label: '转变/过渡', emoji: '🌊', desc: '人生阶段转换、移民、退休、身份转变' },
  { value: 'loss', label: '失落/哀伤', emoji: '💔', desc: '分手、离婚、丧亲、失业、梦想破灭' },
  
  // 社会与文化
  { value: 'ethics', label: '伦理/正义', emoji: '⚖️', desc: '社会议题、公义行动、良心抉择、职场伦理' },
  { value: 'media', label: '媒体/信息', emoji: '📺', desc: '内容消费、社交媒体、新闻判断、网络行为' },
  { value: 'other', label: '其他/独特', emoji: '📝', desc: '无法归类、多重混合、独特处境' },
]

// ==================== 87个核心情绪（按情感星球分类）====================

// 正向情绪 — 渴望类 + 回忆类
const positiveEmotionsLonging = [
  { value: 'desire', label: '渴慕', emoji: '💧', category: '渴望类', en: 'desire' },
  { value: 'longing', label: '思念', emoji: '💌', category: '渴望类', en: 'longing' },
  { value: 'reminiscence', label: '怀旧', emoji: '📷', category: '回忆类', en: 'reminiscence' },
  { value: 'yearning', label: '渴盼', emoji: '🌅', category: '盼望类', en: 'yearning' },
  { value: 'anticipation', label: '期待', emoji: '🎁', category: '盼望类', en: 'anticipation' },
  { value: 'craving', label: '渴望', emoji: '🔥', category: '渴望类', en: 'craving' },
]

// 正向情绪 — 快乐类 + 感激类
const positiveEmotionsJoy = [
  { value: 'joy', label: '欣慰', emoji: '😊', category: '快乐类', en: 'joy' },
  { value: 'happiness', label: '愉快', emoji: '😄', category: '快乐类', en: 'happiness' },
  { value: 'pleasure', label: '愉悦', emoji: '😃', category: '快乐类', en: 'pleasure' },
  { value: 'gladness', label: '欣喜', emoji: '🙂', category: '快乐类', en: 'gladness' },
  { value: 'bliss', label: '幸福', emoji: '🥰', category: '快乐类', en: 'bliss' },
  { value: 'gratitude', label: '感恩', emoji: '🙏', category: '感激类', en: 'gratitude' },
  { value: 'thankfulness', label: '感念', emoji: '💝', category: '感激类', en: 'thankfulness' },
]

// 正向情绪 — 盼望类 + 热情类
const positiveEmotionsHope = [
  { value: 'hope', label: '希望', emoji: '�', category: '盼望类', en: 'hope' },
  { value: 'optimism', label: '乐观', emoji: '☀️', category: '盼望类', en: 'optimism' },
  { value: 'eagerness', label: '热切', emoji: '⚡', category: '热情类', en: 'eagerness' },
  { value: 'ardor', label: '热情', emoji: '🔥', category: '热情类', en: 'ardor' },
  { value: 'fervor', label: '热忱', emoji: '✨', category: '热情类', en: 'fervor' },
  { value: 'exuberance', label: '欢畅', emoji: '🎉', category: '热情类', en: 'exuberance' },
  { value: 'excitement', label: '兴奋', emoji: '🤩', category: '兴奋类', en: 'excitement' },
  { value: 'exhilaration', label: '激动', emoji: '🥳', category: '兴奋类', en: 'exhilaration' },
  { value: 'rapture', label: '陶醉', emoji: '😇', category: '陶醉类', en: 'rapture' },
]

// 正向情绪 — 喜爱类 + 好奇类
const positiveEmotionsLove = [
  { value: 'fascination', label: '着迷', emoji: '🤯', category: '喜爱类', en: 'fascination' },
  { value: 'infatuation', label: '痴迷', emoji: '💘', category: '喜爱类', en: 'infatuation' },
  { value: 'fondness', label: '喜爱', emoji: '🥺', category: '喜爱类', en: 'fondness' },
  { value: 'affection', label: '情愫', emoji: '💕', category: '喜爱类', en: 'affection' },
  { value: 'interest', label: '兴趣', emoji: '👀', category: '好奇类', en: 'interest' },
  { value: 'curiosity', label: '好奇', emoji: '🤔', category: '好奇类', en: 'curiosity' },
]

// 正向情绪 — 振奋类 + 平静类
const positiveEmotionsCalm = [
  { value: 'invigoration', label: '鼓舞', emoji: '💪', category: '振奋类', en: 'invigoration' },
  { value: 'encouragement', label: '振奋', emoji: '📈', category: '振奋类', en: 'encouragement' },
  { value: 'peace', label: '平静', emoji: '😌', category: '平静类', en: 'peace' },
  { value: 'tranquility', label: '宁静', emoji: '🧘', category: '平静类', en: 'tranquility' },
  { value: 'serenity', label: '安宁', emoji: '🕊️', category: '平静类', en: 'serenity' },
  { value: 'security', label: '安心', emoji: '🛡️', category: '平静类', en: 'security' },
]

// 正向情绪 — 释然类 + 放松类 + 满足类
const positiveEmotionsRelief = [
  { value: 'relief', label: '释然', emoji: '😮‍�', category: '释然类', en: 'relief' },
  { value: 'lightness', label: '轻松', emoji: '🎈', category: '放松类', en: 'lightness' },
  { value: 'comfort', label: '惬意', emoji: '🛋️', category: '舒适类', en: 'comfort' },
  { value: 'enjoyment', label: '享受', emoji: '😋', category: '满足类', en: 'enjoyment' },
  { value: 'fulfillment', label: '满足', emoji: '✅', category: '满足类', en: 'fulfillment' },
  { value: 'satisfaction', label: '满意', emoji: '👍', category: '满足类', en: 'satisfaction' },
]

// 负向情绪 — 孤独类 + 渴望类（负面）
const negativeEmotionsLonely = [
  { value: 'loneliness', label: '寂寥', emoji: '�', category: '孤独类', en: 'loneliness' },
  { value: 'solitude', label: '孤独', emoji: '🚶', category: '孤独类', en: 'solitude' },
  { value: 'isolation', label: '孤立', emoji: '🏝️', category: '孤独类', en: 'isolation' },
  { value: 'hunger', label: '饥渴', emoji: '😣', category: '渴望类', en: 'hunger' },
]

// 负向情绪 — 悲伤类 + 绝望类
const negativeEmotionsSad = [
  { value: 'sadness', label: '悲伤', emoji: '😢', category: '悲伤类', en: 'sadness' },
  { value: 'sorrow', label: '忧伤', emoji: '😞', category: '悲伤类', en: 'sorrow' },
  { value: 'grief', label: '愁苦', emoji: '😭', category: '悲伤类', en: 'grief' },
  { value: 'anguish', label: '哀痛', emoji: '💔', category: '悲伤类', en: 'anguish' },
  { value: 'despair', label: '绝望', emoji: '�', category: '绝望类', en: 'despair' },
  { value: 'hopelessness', label: '无望', emoji: '🌑', category: '绝望类', en: 'hopelessness' },
]

// 负向情绪 — 失落类 + 空虚类 + 遗憾类
const negativeEmotionsLoss = [
  { value: 'loss', label: '失落', emoji: '📉', category: '失落类', en: 'loss' },
  { value: 'emptiness', label: '空虚', emoji: '🕳️', category: '空虚类', en: 'emptiness' },
  { value: 'regret', label: '遗憾', emoji: '😔', category: '遗憾类', en: 'regret' },
  { value: 'remorse', label: '悔恨', emoji: '😖', category: '悔恨类', en: 'remorse' },
  { value: 'self_condemnation', label: '自责', emoji: '💢', category: '自责类', en: 'self-condemnation' },
]

// 负向情绪 — 羞愧类 + 内疚类
const negativeEmotionsShame = [
  { value: 'shame', label: '羞愧', emoji: '🔴', category: '羞愧类', en: 'shame' },
  { value: 'embarrassment', label: '难堪', emoji: '😳', category: '羞愧类', en: 'embarrassment' },
  { value: 'guilt', label: '内疚', emoji: '⛓️', category: '内疚类', en: 'guilt' },
]

// 负向情绪 — 恐惧类 + 焦虑类
const negativeEmotionsFear = [
  { value: 'fear', label: '恐惧', emoji: '😱', category: '恐惧类', en: 'fear' },
  { value: 'dread', label: '害怕', emoji: '😨', category: '恐惧类', en: 'dread' },
  { value: 'anxiety', label: '焦虑', emoji: '😰', category: '焦虑类', en: 'anxiety' },
  { value: 'worry', label: '担忧', emoji: '🤯', category: '焦虑类', en: 'worry' },
  { value: 'nervousness', label: '紧张', emoji: '😬', category: '紧张类', en: 'nervousness' },
  { value: 'panic', label: '恐慌', emoji: '�', category: '紧张类', en: 'panic' },
]

// 负向情绪 — 愤怒类 + 烦躁类
const negativeEmotionsAnger = [
  { value: 'anger', label: '愤怒', emoji: '😠', category: '愤怒类', en: 'anger' },
  { value: 'rage', label: '怒', emoji: '🤬', category: '愤怒类', en: 'rage' },
  { value: 'fury', label: '暴怒', emoji: '😡', category: '愤怒类', en: 'fury' },
  { value: 'irritation', label: '烦躁', emoji: '😤', category: '烦躁类', en: 'irritation' },
  { value: 'impatience', label: '不耐烦', emoji: '⏱️', category: '烦躁类', en: 'impatience' },
]

// 负向情绪 — 厌恶类 + 嫉妒类
const negativeEmotionsDisgust = [
  { value: 'disgust', label: '厌恶', emoji: '🤢', category: '厌恶类', en: 'disgust' },
  { value: 'contempt', label: '鄙视', emoji: '😒', category: '厌恶类', en: 'contempt' },
  { value: 'jealousy', label: '嫉妒', emoji: '😒', category: '嫉妒类', en: 'jealousy' },
  { value: 'envy', label: '羡慕', emoji: '👀', category: '嫉妒类', en: 'envy' },
]

// 复杂/关系情绪 — 同情类 + 理解类 + 宽恕类
const complexEmotionsCompassion = [
  { value: 'compassion', label: '悲悯', emoji: '�', category: '同情类', en: 'compassion' },
  { value: 'sympathy', label: '同情', emoji: '🤝', category: '同情类', en: 'sympathy' },
  { value: 'empathy', label: '共情', emoji: '�', category: '同情类', en: 'empathy' },
  { value: 'comprehension', label: '理解', emoji: '💡', category: '理解类', en: 'comprehension' },
  { value: 'forgiveness', label: '宽恕', emoji: '🕊️', category: '宽恕类', en: 'forgiveness' },
  { value: 'pardon', label: '饶恕', emoji: '✝️', category: '宽恕类', en: 'pardon' },
]

// 复杂/关系情绪 — 矛盾类 + 困惑类 + 怀疑类 + 戒备类 + 疏离类
const complexEmotionsAmbivalence = [
  { value: 'ambivalence', label: '矛盾', emoji: '⚖️', category: '矛盾类', en: 'ambivalence' },
  { value: 'confusion', label: '困惑', emoji: '�', category: '困惑类', en: 'confusion' },
  { value: 'uncertainty', label: '迷茫', emoji: '�️', category: '困惑类', en: 'uncertainty' },
  { value: 'doubt', label: '怀疑', emoji: '❓', category: '怀疑类', en: 'doubt' },
  { value: 'defensiveness', label: '戒备', emoji: '🛡️', category: '戒备类', en: 'defensiveness' },
  { value: 'alienation', label: '疏离', emoji: '🧱', category: '疏离类', en: 'alienation' },
]

// 完整情绪列表（87个）
const emotionTypes = [
  ...positiveEmotionsLonging,
  ...positiveEmotionsJoy,
  ...positiveEmotionsHope,
  ...positiveEmotionsLove,
  ...positiveEmotionsCalm,
  ...positiveEmotionsRelief,
  ...negativeEmotionsLonely,
  ...negativeEmotionsSad,
  ...negativeEmotionsLoss,
  ...negativeEmotionsShame,
  ...negativeEmotionsFear,
  ...negativeEmotionsAnger,
  ...negativeEmotionsDisgust,
  ...complexEmotionsCompassion,
  ...complexEmotionsAmbivalence,
]

// 情绪分类导航（用于UI展示）
const emotionCategories = [
  { key: 'longing', label: '渴望与盼望', emotions: [...positiveEmotionsLonging, ...positiveEmotionsHope.filter(e => e.category === '盼望类')] },
  { key: 'joy', label: '快乐与感激', emotions: positiveEmotionsJoy },
  { key: 'passion', label: '热情与兴奋', emotions: positiveEmotionsHope.filter(e => ['热情类', '兴奋类', '陶醉类'].includes(e.category)) },
  { key: 'love', label: '喜爱与好奇', emotions: positiveEmotionsLove },
  { key: 'calm', label: '平静与安宁', emotions: [...positiveEmotionsCalm, ...positiveEmotionsRelief] },
  { key: 'lonely', label: '孤独与失落', emotions: [...negativeEmotionsLonely, ...negativeEmotionsLoss] },
  { key: 'sad', label: '悲伤与绝望', emotions: negativeEmotionsSad },
  { key: 'shame', label: '羞愧与内疚', emotions: negativeEmotionsShame },
  { key: 'fear', label: '恐惧与焦虑', emotions: negativeEmotionsFear },
  { key: 'anger', label: '愤怒与厌恶', emotions: [...negativeEmotionsAnger, ...negativeEmotionsDisgust] },
  { key: 'complex', label: '复杂与关系', emotions: [...complexEmotionsCompassion, ...complexEmotionsAmbivalence] },
]

// 灵性原则
const spiritualPrinciples = [
  { id: '1', text: '凡事察验，善美的要持守', ref: '帖前5:21' },
  { id: '2', text: '你要保守你心，胜过保守一切', ref: '箴4:23' },
  { id: '3', text: '不要恐惧，因为我与你同在', ref: '赛41:10' },
  { id: '4', text: '看别人比自己强', ref: '腓2:3' },
  { id: '5', text: '凭果子认出他们来', ref: '太7:20' },
  { id: '6', text: '爱比成功更高', ref: '林前13:1-3' },
  { id: '7', text: '真理比舒适更重要', ref: '约8:32' },
  { id: '8', text: '谦卑在智慧以先', ref: '箴11:2' },
  { id: '9', text: '安息是属灵操练', ref: '可6:31' },
  { id: '10', text: '顺服神，不顺从人', ref: '徒5:29' },
  { id: '11', text: '愿意受苦而不愿犯罪', ref: '来11:25' },
  { id: '12', text: '患难生忍耐，忍耐生老练', ref: '罗5:3-4' },
]

export default function DecisionSupportPage({ user, onBack, onDashboard, embedded = false }) {
  const [activeTab, setActiveTab] = useState('new') // new, history, principles
  const [loading, setLoading] = useState(false)
  const [decisions, setDecisions] = useState([])
  const [selectedDecision, setSelectedDecision] = useState(null)

  // ==================== 扩展状态快照（12维度，覆盖身心灵社智财道）====================
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    category: '',
    urgency: 3,
    importance: 3,
    // 原始5维度（保留兼容）
    stressLevel: 5,          // 压力水平
    anxietyLevel: 5,         // 焦虑水平
    fatigueLevel: 5,         // 疲劳程度
    spiritualDryness: 5,     // 灵性干涸
    emotionalStability: 5,   // 情绪稳定
    // 扩展7维度（现代生活完整画像）
    physicalHealth: 5,       // 身体健康
    sleepQuality: 5,         // 睡眠质量
    socialConnection: 5,     // 社交连接
    financialPressure: 5,    // 财务压力
    cognitiveClarity: 5,      // 认知清晰度
    identityConfusion: 5,    // 身份困惑
    moralTension: 5,         // 道德张力
    emotions: [],
  })

  // 灵镜分析 + 结果展示
  const [analysisResult, setAnalysisResult] = useState(null)
  const [mvfeResult, setMvfeResult] = useState(null)
  const [mvfeProcessing, setMvfeProcessing] = useState(false)
  const [mvfeError, setMvfeError] = useState('')
  const userId = String(user?.id || user?.email || 'default_user')

  // 加载决策历史
  useEffect(() => {
    if (activeTab === 'history') {
      loadDecisions()
    }
  }, [activeTab])

  const loadDecisions = async () => {
    try {
      const token = getToken()
      const res = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(userId), {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('加载失败')
      const data = await res.json()
      setDecisions(data)
    } catch (err) {
      console.error('加载决策历史失败:', err)
    }
  }

  // 灵镜分析 — 调用 MVFE /process, 返回结果以便同步使用
  const handleMvfeAnalysis = async (text) => {
    const t = text || formData.description
    if (!t.trim()) return null
    setMvfeProcessing(true); setMvfeError('')
    try {
      const r = await fetch(MVFE_BASE + '/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: t, user_id: userId }),
      })
      const respText = await r.text()
      if (!r.ok) {
        let msg = '灵镜分析失败'
        try {
          const j = JSON.parse(respText)
          msg = j.detail || j.error || msg
        } catch {}
        throw new Error(msg)
      }
      const d = JSON.parse(respText)
      setMvfeResult(d)
      // Auto-map MVFE results to decision form emotion/state fields
      autoMapMvfeToForm(d)
      return d
    } catch (err) {
      setMvfeError(err.message)
      return null
    } finally {
      setMvfeProcessing(false)
    }
  }

  // 自动从 MVFE 分析结果映射到决策表单
  const autoMapMvfeToForm = (mvfe) => {
    if (!mvfe) return
    const em = mvfe.emotion || {}
    const at = mvfe.attention || {}
    const fo = mvfe.formation || {}

    const emotionToStress = { anxiety:8, fear:7, anger:7, sadness:6, guilt:6, shame:6, joy:2, peace:1, hope:2, love:2, gratitude:1, envy:5, loneliness:6, disgust:4, surprise:3 }
    const emotionToAnxiety = { anxiety:9, fear:8, anger:5, sadness:5, guilt:6, shame:6, joy:1, peace:1, hope:2, love:2, gratitude:1, envy:4, loneliness:5, disgust:3, surprise:4 }
    const emotionToSpiritual = { anxiety:6, fear:5, anger:5, sadness:7, guilt:8, shame:8, joy:2, peace:1, hope:2, love:2, gratitude:1, envy:5, loneliness:6, disgust:4, surprise:3 }

    const primary = em.primary_emotion || 'unknown'
    const intensity = em.intensity || 0.5
    const stress = Math.round((emotionToStress[primary] || 5) * intensity + 5 * (1 - intensity))
    const anxiety = Math.round((emotionToAnxiety[primary] || 5) * intensity + 5 * (1 - intensity))
    const spiritualDry = Math.round((emotionToSpiritual[primary] || 5) * intensity + 5 * (1 - intensity))
    const stability = Math.round((fo.stability_score || 0.5) * 10)
    const fatigue = Math.round((at.fixation_score || 0.5) * 8 + 1)

    const emotions = [{ type: primary, intensity: Math.round(intensity * 10), trigger: at.anchor_object || '' }]
    if (em.secondary_emotions?.length > 0) {
      em.secondary_emotions.slice(0, 2).forEach(sec => {
        emotions.push({ type: sec, intensity: Math.round(intensity * 10 * 0.6), trigger: '' })
      })
    }

    setFormData(prev => ({
      ...prev,
      // 基础维度映射
      stressLevel: stress,
      anxietyLevel: anxiety,
      fatigueLevel: fatigue,
      spiritualDryness: spiritualDry,
      emotionalStability: stability,
      // 扩展维度映射（从MVFE formation和context推断）
      physicalHealth: Math.round(10 - (fo.formation_score ? (1 - fo.formation_score) * 5 : 2.5)),
      sleepQuality: Math.round(10 - fatigue * 0.6 - stress * 0.3),
      socialConnection: at.social_context === 'isolated' ? 3 : (at.social_context === 'supportive' ? 8 : 5),
      financialPressure: dc.drivers?.ego > 0.6 ? 7 : (dc.drivers?.fear > 0.6 ? 6 : 4),
      cognitiveClarity: 10 - Math.round((em.uncertainty || 0.3) * 10),
      identityConfusion: em.secondary_emotions?.includes('confusion') ? 7 : (at.fixation_score > 0.7 ? 6 : 4),
      moralTension: dc.drivers?.love < 0.3 && dc.drivers?.ego > 0.5 ? 6 : 4,
      emotions,
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      const token = getToken()

      // 如果还没有进行灵镜分析，先执行一次并等待映射完成
      let currentMvfe = mvfeResult
      if (!currentMvfe && formData.description.trim()) {
        currentMvfe = await handleMvfeAnalysis(formData.description)
      }

      // 使用已映射的 formData（autoMapMvfeToForm 已更新），或读取最新 state
      // 注意：autoMapMvfeToForm 通过 setFormData 更新，此处需要用回调读取最新值
      const latestForm = await new Promise(resolve => {
        setFormData(prev => { resolve(prev); return prev })
      })

      // 构建提交数据
      const payload = {
        title: latestForm.title,
        description: latestForm.description,
        category: latestForm.category,
        urgency: latestForm.urgency,
        importance: latestForm.importance,
        state_snapshot: {
          // 原始5维度
          stress_level: latestForm.stressLevel,
          anxiety_level: latestForm.anxietyLevel,
          fatigue_level: latestForm.fatigueLevel,
          spiritual_dryness: latestForm.spiritualDryness,
          emotional_stability: latestForm.emotionalStability,
          // 扩展7维度
          physical_health: latestForm.physicalHealth,
          sleep_quality: latestForm.sleepQuality,
          social_connection: latestForm.socialConnection,
          financial_pressure: latestForm.financialPressure,
          cognitive_clarity: latestForm.cognitiveClarity,
          identity_confusion: latestForm.identityConfusion,
          moral_tension: latestForm.moralTension,
        },
        emotion_logs: latestForm.emotions.map((e, i) => ({
          emotion_type: e.type,
          intensity: e.intensity,
          trigger: e.trigger,
          timestamp: new Date(Date.now() - i * 60000).toISOString(),
        })),
        context_factors: {
          user_note: latestForm.description,
          mvfe_event_id: currentMvfe?.event_id || null,
        },
      }

      const res = await fetch(sfdsUrl('/decisions') + '?user_id=' + encodeURIComponent(userId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || '提交失败')
      }

      const result = await res.json()
      
      // 等待分析完成（轮询）
      await pollForAnalysis(result.id)
      
    } catch (err) {
      alert(err.message)
    } finally {
      setLoading(false)
    }
  }

  const pollForAnalysis = async (decisionId) => {
    const token = getToken()
    let attempts = 0
    const maxAttempts = 30 // 最多等待30秒

    while (attempts < maxAttempts) {
      const res = await fetch(sfdsUrl(`/decisions/${decisionId}`) + '?user_id=' + encodeURIComponent(userId), {
        headers: { Authorization: `Bearer ${token}` },
      })
      
      if (res.ok) {
        const data = await res.json()
        
        if (data.status === 'guided' && data.guidance) {
          setAnalysisResult(data)
          return
        }
        
        if (data.status === 'analyzing') {
          await new Promise(r => setTimeout(r, 1000))
          attempts++
          continue
        }
      }
      
      break
    }
  }

  const addEmotion = () => {
    setFormData(prev => ({
      ...prev,
      emotions: [...prev.emotions, { type: '', intensity: 5, trigger: '' }],
    }))
  }

  const updateEmotion = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.map((e, i) => 
        i === index ? { ...e, [field]: value } : e
      ),
    }))
  }

  const removeEmotion = (index) => {
    setFormData(prev => ({
      ...prev,
      emotions: prev.emotions.filter((_, i) => i !== index),
    }))
  }

  // 渲染导航标签
  const renderTabs = () => (
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
      {[
        { key: 'new', label: '新决策', emoji: '🆕' },
        { key: 'history', label: '历史', emoji: '📜' },
        { key: 'principles', label: '原则', emoji: '📖' },
      ].map(tab => (
        <button
          key={tab.key}
          onClick={() => {
            setActiveTab(tab.key)
            setAnalysisResult(null)
          }}
          style={{
            flex: 1,
            padding: '10px 12px',
            borderRadius: '10px',
            border: 'none',
            background: activeTab === tab.key ? '#007aff' : 'rgba(120,120,128,0.2)',
            color: activeTab === tab.key ? '#fff' : 'rgba(255,255,255,0.6)',
            fontSize: '14px',
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

  // 渲染新决策表单
  const renderNewDecisionForm = () => (
    <>
    <form id="decision-form" onSubmit={handleSubmit} style={{ padding: '16px' }}>
      {/* 决策标题 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策标题 *</label>
        <input
          type="text"
          value={formData.title}
          onChange={e => setFormData(prev => ({ ...prev, title: e.target.value }))}
          placeholder="例如：是否应该接受这份工作邀请？"
          style={inputStyle}
          required
        />
      </div>

      {/* 决策类别 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>决策类别 *</label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {decisionCategories.map(cat => (
            <button
              key={cat.value}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, category: cat.value }))}
              style={{
                padding: '8px 12px',
                borderRadius: '20px',
                border: formData.category === cat.value ? '2px solid #007aff' : '1px solid rgba(255,255,255,0.2)',
                background: formData.category === cat.value ? 'rgba(0,122,255,0.2)' : 'rgba(255,255,255,0.05)',
                color: '#fff',
                fontSize: '13px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* 紧急与重要程度 */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>紧急程度: {formData.urgency}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.urgency}
            onChange={e => setFormData(prev => ({ ...prev, urgency: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <label style={labelStyle}>重要程度: {formData.importance}/5</label>
          <input
            type="range"
            min="1"
            max="5"
            value={formData.importance}
            onChange={e => setFormData(prev => ({ ...prev, importance: parseInt(e.target.value) }))}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* 当前状态快照 */}
      <div style={{ 
        background: 'rgba(0,122,255,0.1)', 
        borderRadius: '12px', 
        padding: '16px',
        marginBottom: '16px',
      }}>
        <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px', color: '#007aff' }}>
          🔍 当前状态快照
        </div>
        
        {/* 原始5维度 — 基础身心灵状态 */}
        <div style={{ fontSize: '12px', color: '#007aff', marginBottom: '8px', fontWeight: 500 }}>
          📊 基础维度（身心灵核心）
        </div>
        {[
          { key: 'stressLevel', label: '压力水平', icon: '😰', desc: '外部要求与内部资源的差距' },
          { key: 'anxietyLevel', label: '焦虑水平', icon: '😨', desc: '对未来不确定的担忧程度' },
          { key: 'fatigueLevel', label: '疲劳程度', icon: '😴', desc: '身心能量耗竭的感受' },
          { key: 'spiritualDryness', label: '灵性干涸', icon: '🏜️', desc: '与神连接的感受减弱' },
          { key: 'emotionalStability', label: '情绪稳定', icon: '😌', desc: '情绪波动的可控程度' },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: '10px' }}>
            <label style={{ ...labelStyle, fontSize: '13px' }}>
              {item.icon} {item.label}: {formData[item.key]}/10
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginLeft: '8px' }}>
                {item.desc}
              </span>
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={formData[item.key]}
              onChange={e => setFormData(prev => ({ ...prev, [item.key]: parseInt(e.target.value) }))}
              style={{ width: '100%' }}
            />
          </div>
        ))}
        
        {/* 扩展7维度 — 现代生活完整画像 */}
        <div style={{ fontSize: '12px', color: '#34c759', margin: '16px 0 8px', fontWeight: 500 }}>
          🌐 扩展维度（现代生活全景）
        </div>
        {[
          { key: 'physicalHealth', label: '身体健康', icon: '💪', desc: '身体状况与精力水平', color: '#34c759' },
          { key: 'sleepQuality', label: '睡眠质量', icon: '🌙', desc: '休息恢复与睡眠满意度', color: '#af52de' },
          { key: 'socialConnection', label: '社交连接', icon: '🤝', desc: '关系网络与支持系统', color: '#007aff' },
          { key: 'financialPressure', label: '财务压力', icon: '💰', desc: '经济焦虑与资源担忧', color: '#ff9500' },
          { key: 'cognitiveClarity', label: '认知清晰', icon: '🧠', desc: '思维清晰度与专注力', color: '#5ac8fa' },
          { key: 'identityConfusion', label: '身份困惑', icon: '❓', desc: '自我认知与定位迷茫', color: '#ff3b30' },
          { key: 'moralTension', label: '道德张力', icon: '⚖️', desc: '价值观冲突与良心挣扎', color: '#ffcc00' },
        ].map(item => (
          <div key={item.key} style={{ marginBottom: '10px' }}>
            <label style={{ ...labelStyle, fontSize: '13px' }}>
              <span style={{ color: item.color }}>{item.icon}</span> {item.label}: {formData[item.key]}/10
              <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginLeft: '8px' }}>
                {item.desc}
              </span>
            </label>
            <input
              type="range"
              min="0"
              max="10"
              value={formData[item.key]}
              onChange={e => setFormData(prev => ({ ...prev, [item.key]: parseInt(e.target.value) }))}
              style={{ width: '100%', accentColor: item.color }}
            />
          </div>
        ))}
      </div>

      {/* ==================== 多选情绪选择器（87个情绪）==================== */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>🎭 选择你此刻的情绪（可多选）</label>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '10px' }}>
          点击选择多个情绪，系统将综合分析你的情绪状态
        </div>
        
        {/* 已选情绪标签 */}
        {formData.emotions.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
            {formData.emotions.map((emo, idx) => {
              const emotionDef = emotionTypes.find(e => e.value === emo.type)
              return (
                <span key={idx} style={{
                  padding: '4px 10px',
                  borderRadius: '12px',
                  background: 'rgba(0,122,255,0.2)',
                  border: '1px solid rgba(0,122,255,0.3)',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}>
                  {emotionDef?.emoji || '🎭'} {emotionDef?.label || emo.type}
                  <button
                    type="button"
                    onClick={() => removeEmotion(idx)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ff3b30',
                      cursor: 'pointer',
                      fontSize: '14px',
                      padding: '0 2px',
                    }}
                  >×</button>
                </span>
              )
            })}
          </div>
        )}
        
        {/* 情绪分类折叠面板 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {emotionCategories.map(cat => (
            <details key={cat.key} style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.08)',
            }}>
              <summary style={{
                padding: '10px 14px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500,
                color: 'rgba(255,255,255,0.9)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                listStyle: 'none',
              }}>
                <span style={{ transform: 'rotate(-90deg)', fontSize: '10px' }}>▼</span>
                {cat.label} ({cat.emotions.length}个)
              </summary>
              <div style={{
                padding: '10px 14px',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px',
                borderTop: '1px solid rgba(255,255,255,0.05)',
              }}>
                {cat.emotions.map(emo => {
                  const isSelected = formData.emotions.some(e => e.type === emo.value)
                  return (
                    <button
                      key={emo.value}
                      type="button"
                      onClick={() => {
                        if (isSelected) {
                          setFormData(prev => ({
                            ...prev,
                            emotions: prev.emotions.filter(e => e.type !== emo.value)
                          }))
                        } else {
                          setFormData(prev => ({
                            ...prev,
                            emotions: [...prev.emotions, { type: emo.value, intensity: 5, trigger: '' }]
                          }))
                        }
                      }}
                      style={{
                        padding: '6px 10px',
                        borderRadius: '16px',
                        border: isSelected ? '1px solid #007aff' : '1px solid rgba(255,255,255,0.15)',
                        background: isSelected ? 'rgba(0,122,255,0.25)' : 'rgba(255,255,255,0.05)',
                        color: isSelected ? '#fff' : 'rgba(255,255,255,0.7)',
                        fontSize: '12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        transition: 'all 0.2s',
                      }}
                    >
                      <span>{emo.emoji}</span>
                      <span>{emo.label}</span>
                    </button>
                  )
                })}
              </div>
            </details>
          ))}
        </div>
      </div>

      {/* 内心状态描述 — 灵镜分析输入 */}
      <div style={{ marginBottom: '16px' }}>
        <label style={labelStyle}>描述此刻的内心状态 *</label>
        <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)', marginBottom: '10px', lineHeight: 1.6 }}>
          描述此刻的内心状态、正在思考的事情、或面临的选择。<br/>
          系统将自动提取情绪、注意力、决策驱动，并进行灵性辨识。
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
          {QUICK_PROMPTS.map((q, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setFormData(prev => ({ ...prev, description: q.t }))
                handleMvfeAnalysis(q.t)
              }}
              style={{
                padding: '6px 12px',
                borderRadius: '20px',
                border: '1px solid rgba(255,255,255,0.08)',
                background: 'rgba(255,255,255,0.03)',
                color: 'rgba(255,255,255,0.7)',
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <span>{q.e}</span>
              <span>{q.l}</span>
            </button>
          ))}
        </div>
        <textarea
          value={formData.description}
          onChange={e => setFormData(prev => ({ ...prev, description: e.target.value }))}
          placeholder="或者，在这里自由写下你的感受..."
          style={{ ...inputStyle, minHeight: '100px', resize: 'vertical', lineHeight: 1.7 }}
          required
        />

        {/* 灵镜分析按钮 */}
        <button
          type="button"
          onClick={() => handleMvfeAnalysis()}
          disabled={mvfeProcessing || !formData.description.trim()}
          style={{
            width: '100%',
            marginTop: '10px',
            padding: '12px',
            borderRadius: '12px',
            border: 'none',
            background: mvfeProcessing ? 'rgba(79,172,254,0.15)' : 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            color: '#fff',
            fontSize: '14px',
            fontWeight: 700,
            cursor: mvfeProcessing ? 'wait' : 'pointer',
            transition: 'all 0.3s',
          }}
        >
          {mvfeProcessing ? '⏳ 灵镜分析中...' : '🔬 灵镜分析'}
        </button>
        {mvfeError && <div style={{ marginTop: '8px', padding: '8px 12px', borderRadius: '8px', background: 'rgba(255,50,50,0.06)', color: '#ff6b6b', fontSize: '12px', borderLeft: '3px solid #ff6b6b' }}>{mvfeError}</div>}

        {/* 灵镜分析结果摘要 */}
        {mvfeResult && (
          <div style={{
            marginTop: '12px',
            padding: '12px',
            borderRadius: '10px',
            background: 'rgba(79,172,254,0.06)',
            border: '1px solid rgba(79,172,254,0.15)',
          }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#4facfe', marginBottom: '8px' }}>✅ 灵镜分析完成 — 已自动填充状态快照</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', fontSize: '11px' }}>
              {mvfeResult.emotion?.primary_emotion && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: 'rgba(255,169,77,0.12)', color: '#ffa94d' }}>
                  🎭 {mvfeResult.emotion.primary_emotion} ({Math.round((mvfeResult.emotion.intensity||0)*100)}%)
                </span>
              )}
              {mvfeResult.attention?.focus && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: 'rgba(79,172,254,0.12)', color: '#4facfe' }}>
                  👁 {mvfeResult.attention.focus}
                </span>
              )}
              {mvfeResult.decision?.type && (
                <span style={{ padding: '3px 8px', borderRadius: '10px', background: mvfeResult.decision.type === 'approach' ? 'rgba(81,207,102,0.12)' : 'rgba(255,107,107,0.12)', color: mvfeResult.decision.type === 'approach' ? '#51cf66' : '#ff6b6b' }}>
                  ⚖️ {mvfeResult.decision.type === 'approach' ? '趋近' : '回避'}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 提交按钮 — 开始辨识 */}
      <button
        type="submit"
        disabled={loading || !formData.title || !formData.category || !formData.description.trim()}
        style={{
          width: '100%',
          padding: '14px',
          borderRadius: '12px',
          border: 'none',
          background: loading ? 'rgba(120,120,128,0.3)' : '#007aff',
          color: '#fff',
          fontSize: '16px',
          fontWeight: 600,
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
        }}
      >
      {loading ? (
        <>
          <span className="spinner" style={{ 
            width: '18px', 
            height: '18px', 
            border: '2px solid rgba(255,255,255,0.3)',
            borderTopColor: '#fff',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }} />
          <span>辨识中…</span>
        </>
      ) : (
        <>
          <span>🔍</span>
          <span>开始属灵辨识</span>
        </>
      )}
      </button>
    </form>
    </>
  )

  // 渲染分析结果
  const renderAnalysisResult = () => {
    if (!analysisResult) return null
    
    const { motive_analysis, discernment_result, guidance } = analysisResult
    
    return (
      <div style={{ padding: '16px' }}>
        <div style={{
          background: 'linear-gradient(135deg, #007aff, #5e5ce6)',
          borderRadius: '16px',
          padding: '20px',
          marginBottom: '20px',
          color: '#fff',
        }}>
          <div style={{ fontSize: '20px', fontWeight: 700, marginBottom: '8px' }}>
            ✨ 辨识分析完成
          </div>
          <div style={{ fontSize: '14px', opacity: 0.9 }}>
            基于当前状态，系统已完成动机分析与来源辨识
          </div>
        </div>

        {/* 动机分析 */}
        {motive_analysis && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>🧠 动机分析</div>
            <div style={{ marginBottom: '12px' }}>
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>😨 恐惧驱动</span>
                  <span>{Math.round(motive_analysis.fear_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.fear_driven_score * 100}%`, background: '#ff3b30' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>😤 骄傲驱动</span>
                  <span>{Math.round(motive_analysis.pride_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.pride_driven_score * 100}%`, background: '#ff9500' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>❤️ 爱驱动</span>
                  <span>{Math.round(motive_analysis.love_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.love_driven_score * 100}%`, background: '#34c759' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>🔥 欲望驱动</span>
                  <span>{Math.round(motive_analysis.desire_driven_score * 100)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.desire_driven_score * 100}%`, background: '#af52de' }} />
                </div>
              </div>
            </div>
            
            <div style={{ 
              background: 'rgba(0,122,255,0.15)', 
              borderRadius: '8px', 
              padding: '12px',
              fontSize: '13px',
            }}>
              <strong>主导动机：</strong>
              <span style={{ color: '#007aff', fontWeight: 600 }}>
                {motive_analysis.dominant_motive === 'fear' && '😨 恐惧'}
                {motive_analysis.dominant_motive === 'pride' && '😤 骄傲'}
                {motive_analysis.dominant_motive === 'love' && '❤️ 爱'}
                {motive_analysis.dominant_motive === 'desire' && '🔥 欲望'}
                {motive_analysis.dominant_motive === 'duty' && '📋 责任'}
                {motive_analysis.dominant_motive === 'ambition' && '🎯 雄心'}
              </span>
            </div>
          </div>
        )}

        {/* 来源辨识 */}
        {discernment_result && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>🔮 来源辨识</div>
            
            <div style={{ 
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '10px',
              padding: '12px',
              marginBottom: '12px',
            }}>
              <div style={{ 
                display: 'inline-block',
                padding: '4px 12px',
                borderRadius: '16px',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '8px',
                ...getSourceStyle(discernment_result.primary_source),
              }}>
                {discernment_result.primary_source === 'holy_spirit' && '✨ 圣灵感动'}
                {discernment_result.primary_source === 'conscience' && '🤔 良心/理性'}
                {discernment_result.primary_source === 'fear_response' && '😨 恐惧反应'}
                {discernment_result.primary_source === 'pride_response' && '😤 骄傲反应'}
                {discernment_result.primary_source === 'trauma_response' && '💔 创伤反应'}
                {discernment_result.primary_source === 'worldly_value' && '🌍 世俗价值观'}
                {discernment_result.primary_source === 'flesh_desire' && '🔥 肉体欲望'}
                {discernment_result.primary_source === 'uncertain' && '❓ 不确定'}
              </div>
              
              <div style={{ fontSize: '13px', lineHeight: 1.5, marginBottom: '8px' }}>
                {discernment_result.explanation}
              </div>
              
              <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
                <span>置信度: {Math.round(discernment_result.confidence * 100)}%</span>
                <span>长期果实: {discernment_result.long_term_fruit_score > 0 ? '+' : ''}{discernment_result.long_term_fruit_score}</span>
              </div>
            </div>
          </div>
        )}

        {/* 指导建议 */}
        {guidance && (
          <div style={resultCardStyle}>
            <div style={resultTitleStyle}>📖 指导建议</div>
            
            <div style={{ 
              background: 'rgba(52,199,89,0.15)',
              borderRadius: '10px',
              padding: '12px',
              marginBottom: '16px',
              fontSize: '13px',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}>
              {guidance.structured_advice}
            </div>
            
            {/* 风险 */}
            {guidance.risks && guidance.risks.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#ff3b30' }}>
                  ⚠️ 潜在风险
                </div>
                {guidance.risks.map((risk, i) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    background: 'rgba(255,59,48,0.1)',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    fontSize: '13px',
                  }}>
                    • {risk}
                  </div>
                ))}
              </div>
            )}
            
            {/* 替代解释 */}
            {guidance.alternative_interpretations && guidance.alternative_interpretations.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#ff9500' }}>
                  💭 替代视角
                </div>
                {guidance.alternative_interpretations.map((alt, i) => (
                  <div key={i} style={{
                    padding: '8px 12px',
                    background: 'rgba(255,149,0,0.1)',
                    borderRadius: '8px',
                    marginBottom: '6px',
                    fontSize: '13px',
                  }}>
                    • {alt}
                  </div>
                ))}
              </div>
            )}
            
            {/* 建议行动 */}
            {guidance.recommended_actions && guidance.recommended_actions.length > 0 && (
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px', color: '#007aff' }}>
                  ✅ 建议行动
                </div>
                {guidance.recommended_actions.map((action, i) => (
                  <div key={i} style={{
                    padding: '10px 12px',
                    background: 'rgba(0,122,255,0.1)',
                    borderRadius: '8px',
                    marginBottom: '8px',
                    fontSize: '13px',
                    borderLeft: '3px solid #007aff',
                  }}>
                    {i + 1}. {action}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 灵性原则引用 */}
        <div style={resultCardStyle}>
          <div style={resultTitleStyle}>📜 相关灵性原则</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {spiritualPrinciples.slice(0, 5).map(p => (
              <div key={p.id} style={{
                padding: '8px 12px',
                background: 'rgba(255,255,255,0.05)',
                borderRadius: '8px',
                fontSize: '12px',
                flex: '1 1 calc(50% - 8px)',
                minWidth: '140px',
              }}>
                <div>{p.text}</div>
                <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', marginTop: '4px' }}>
                  {p.ref}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 免责声明 */}
        <div style={{
          background: 'rgba(255,149,0,0.1)',
          borderRadius: '10px',
          padding: '12px',
          marginTop: '16px',
          fontSize: '12px',
          color: 'rgba(255,255,255,0.7)',
          textAlign: 'center',
        }}>
          ⚠️ 本分析仅供参考，不构成权威属灵指导。请寻求属灵导师、牧师或专业辅导的意见。
        </div>

        {/* 返回按钮 */}
        <button
          onClick={() => {
            setAnalysisResult(null)
            setMvfeResult(null)
            setMvfeError('')
            setFormData({
              title: '',
              description: '',
              category: '',
              urgency: 3,
              importance: 3,
              // 基础5维度
              stressLevel: 5,
              anxietyLevel: 5,
              fatigueLevel: 5,
              spiritualDryness: 5,
              emotionalStability: 5,
              // 扩展7维度
              physicalHealth: 5,
              sleepQuality: 5,
              socialConnection: 5,
              financialPressure: 5,
              cognitiveClarity: 5,
              identityConfusion: 5,
              moralTension: 5,
              emotions: [],
            })
          }}
          style={{
            width: '100%',
            padding: '12px',
            marginTop: '16px',
            borderRadius: '10px',
            border: '1px solid rgba(255,255,255,0.2)',
            background: 'transparent',
            color: '#fff',
            fontSize: '14px',
            cursor: 'pointer',
          }}
        >
          🔄 新辨识
        </button>
      </div>
    )
  }

  // 渲染历史记录
  const renderHistory = () => (
    <div style={{ padding: '16px' }}>
      {decisions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px', color: 'rgba(255,255,255,0.5)' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📭</div>
          <div>暂无决策记录</div>
        </div>
      ) : (
        decisions.map((d, i) => (
          <div 
            key={d.id || i}
            onClick={() => setSelectedDecision(d)}
            style={{
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '12px',
              padding: '16px',
              marginBottom: '12px',
              cursor: 'pointer',
              borderLeft: `4px solid ${getCategoryColor(d.category)}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <div style={{ fontWeight: 600, fontSize: '15px', flex: 1, marginRight: '8px' }}>
                {d.title}
              </div>
              <span style={{
                padding: '2px 8px',
                borderRadius: '12px',
                fontSize: '11px',
                background: d.status === 'guided' ? 'rgba(52,199,89,0.2)' : 'rgba(255,149,0,0.2)',
                color: d.status === 'guided' ? '#34c759' : '#ff9500',
              }}>
                {d.status === 'guided' ? '已完成' : '分析中'}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px' }}>
              {formatDate(d.created_at)}
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)' }}>
                {decisionCategories.find(c => c.value === d.category)?.emoji} {decisionCategories.find(c => c.value === d.category)?.label}
              </span>
              <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.4)' }}>
                紧急{d.urgency} • 重要{d.importance}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  )

  // 渲染灵性原则
  const renderPrinciples = () => (
    <div style={{ padding: '16px' }}>
      <div style={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)', marginBottom: '16px', textAlign: 'center' }}>
        在决策中默想这些原则，帮助辨识真伪
      </div>
      
      {spiritualPrinciples.map(p => (
        <div key={p.id} style={{
          background: 'rgba(255,255,255,0.05)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '12px',
        }}>
          <div style={{ fontSize: '15px', fontWeight: 500, marginBottom: '8px', lineHeight: 1.5 }}>
            "{p.text}"
          </div>
          <div style={{ fontSize: '12px', color: '#007aff' }}>
            — {p.ref}
          </div>
        </div>
      ))}
    </div>
  )

  // 工具函数
  const getSourceStyle = (source) => {
    const styles = {
      holy_spirit: { background: 'rgba(52,199,89,0.2)', color: '#34c759' },
      conscience: { background: 'rgba(0,122,255,0.2)', color: '#007aff' },
      fear_response: { background: 'rgba(255,59,48,0.2)', color: '#ff3b30' },
      pride_response: { background: 'rgba(255,149,0,0.2)', color: '#ff9500' },
      trauma_response: { background: 'rgba(175,82,222,0.2)', color: '#af52de' },
      worldly_value: { background: 'rgba(120,120,128,0.2)', color: '#8e8e93' },
      flesh_desire: { background: 'rgba(255,59,48,0.2)', color: '#ff3b30' },
      uncertain: { background: 'rgba(255,204,0,0.2)', color: '#ffcc00' },
    }
    return styles[source] || styles.uncertain
  }

  const getCategoryColor = (category) => {
    const colors = {
      career: '#007aff',
      relationship: '#ff2d55',
      temptation: '#ff3b30',
      calling: '#af52de',
      financial: '#34c759',
      health: '#5ac8fa',
      ministry: '#ff9500',
      other: '#8e8e93',
    }
    return colors[category] || '#8e8e93'
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return ''
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  // 样式常量
  const labelStyle = {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
    color: 'rgba(255,255,255,0.8)',
  }

  const inputStyle = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.15)',
    background: 'rgba(120,120,128,0.18)',
    color: '#fff',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
  }

  const resultCardStyle = {
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '14px',
    padding: '16px',
    marginBottom: '16px',
  }

  const resultTitleStyle = {
    fontSize: '16px',
    fontWeight: 600,
    marginBottom: '12px',
    color: '#fff',
  }

  const progressBarContainer = {
    marginBottom: '12px',
  }

  const progressBarBg = {
    height: '6px',
    background: 'rgba(255,255,255,0.1)',
    borderRadius: '3px',
    overflow: 'hidden',
  }

  const progressBarFill = {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s ease',
  }

  const content = (
    <>
      {/* 标签导航 */}
      {renderTabs()}

      {/* 内容区域 */}
      <div style={{ paddingBottom: embedded ? '0' : '80px' }}>
        {analysisResult ? renderAnalysisResult() : (
          <>
            {activeTab === 'new' && renderNewDecisionForm()}
            {activeTab === 'history' && renderHistory()}
            {activeTab === 'principles' && renderPrinciples()}
          </>
        )}
      </div>
    </>
  )

  if (embedded) {
    return (
      <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
        {content}
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: '#000',
      color: '#fff',
      overflowY: 'auto',
      overflowX: 'hidden',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    }}>
      {/* 顶部栏 */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'rgba(28,28,30,0.9)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(120,120,128,0.2)',
              border: 'none',
              borderRadius: '50%',
              width: '36px',
              height: '36px',
              color: '#fff',
              fontSize: '20px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            ‹
          </button>
          <div>
            <div style={{ fontSize: '17px', fontWeight: 600 }}>属灵辨识</div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>灵镜分析 · 决策辨识</div>
          </div>
        </div>

        {onDashboard ? (
          <button
            onClick={onDashboard}
            style={{
              padding: '7px 14px',
              borderRadius: '10px',
              border: '1px solid rgba(79,172,254,0.25)',
              background: 'rgba(79,172,254,0.08)',
              color: '#4facfe',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            📊 仪表盘
          </button>
        ) : (
          <div style={{
            width: '36px',
            height: '36px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #007aff, #5e5ce6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '18px',
          }}>
            ⚖️
          </div>
        )}
      </div>

      {content}

      {/* 底部提示 */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '12px 16px',
        background: 'rgba(28,28,30,0.95)',
        borderTop: '1px solid rgba(255,255,255,0.1)',
        textAlign: 'center',
        fontSize: '11px',
        color: 'rgba(255,255,255,0.5)',
      }}>
        本系统旨在辅助属灵辨识，不取代个人自由意志或权威属灵指导
      </div>

      {/* 添加CSS动画 */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
