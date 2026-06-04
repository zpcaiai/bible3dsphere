import { useEffect, useState } from 'react'
import { API_BASE, fetchFormationProfile } from './api'
import { getToken } from './auth'
import HabitsPage from './HabitsPage'
import PersonalityPage from './PersonalityPage'
import SoulTabs from './components/SoulTabs'
import SoulDashboard from './components/SoulDashboard'

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

// ==================== 87个核心情绪（按属灵星球分类）====================

// 正向情绪 — 渴望类
const positiveEmotionsLonging = [
  { value: 'desire', label: '渴望', emoji: '💧', category: '渴望', en: 'desire', scripture: '诗42:1' },
  { value: 'longing', label: '思念', emoji: '💌', category: '思念', en: 'longing', scripture: '诗63:1' },
  { value: 'reminiscence', label: '怀念', emoji: '📷', category: '怀念', en: 'reminiscence', scripture: '诗77:11' },
  { value: 'yearning', label: '向往', emoji: '🌅', category: '向往', en: 'yearning', scripture: '启22:20' },
  { value: 'anticipation', label: '期待', emoji: '🎁', category: '期待', en: 'anticipation', scripture: '赛40:31' },
  { value: 'craving', label: '强烈渴求', emoji: '🔥', category: '渴求', en: 'craving', scripture: '诗63:1' },
]

// 正向情绪 — 喜悦类
const positiveEmotionsJoy = [
  { value: 'joy', label: '喜悦', emoji: '😊', category: '喜悦', en: 'joy', scripture: '加5:22' },
  { value: 'happiness', label: '快乐', emoji: '😄', category: '快乐', en: 'happiness', scripture: '诗16:11' },
  { value: 'pleasure', label: '愉悦', emoji: '😃', category: '愉悦', en: 'pleasure', scripture: '诗1:2' },
  { value: 'gladness', label: '欣喜', emoji: '🙂', category: '欣喜', en: 'gladness', scripture: '诗30:5' },
  { value: 'bliss', label: '幸福', emoji: '🥰', category: '幸福', en: 'bliss', scripture: '太5:3-12' },
  { value: 'gratitude', label: '感激', emoji: '🙏', category: '感激', en: 'gratitude', scripture: '帖前5:18' },
  { value: 'thankfulness', label: '感恩', emoji: '💝', category: '感恩', en: 'thankfulness', scripture: '诗107:1' },
]

// 正向情绪 — 希望与热情类
const positiveEmotionsHope = [
  { value: 'hope', label: '希望', emoji: '🌟', category: '希望', en: 'hope', scripture: '罗15:13' },
  { value: 'optimism', label: '乐观', emoji: '☀️', category: '乐观', en: 'optimism', scripture: '箴3:5' },
  { value: 'eagerness', label: '热忱', emoji: '⚡', category: '热忱', en: 'eagerness', scripture: '罗12:11' },
  { value: 'ardor', label: '热情', emoji: '🔥', category: '热情', en: 'ardor', scripture: '启3:19' },
  { value: 'fervor', label: '激情', emoji: '✨', category: '激情', en: 'fervor', scripture: '徒18:25' },
  { value: 'exuberance', label: '活力充沛', emoji: '🎉', category: '活力', en: 'exuberance', scripture: '约10:10' },
  { value: 'excitement', label: '兴奋', emoji: '🤩', category: '兴奋', en: 'excitement', scripture: '徒2:46' },
  { value: 'exhilaration', label: '激动', emoji: '🥳', category: '激动', en: 'exhilaration', scripture: '诗51:12' },
  { value: 'rapture', label: '陶醉', emoji: '😇', category: '陶醉', en: 'rapture', scripture: '帖前4:17' },
]

// 正向情绪 — 喜爱与好奇类
const positiveEmotionsLove = [
  { value: 'fascination', label: '着迷', emoji: '🤯', category: '着迷', en: 'fascination', scripture: '雅歌 良人属我' },
  { value: 'infatuation', label: '迷恋', emoji: '💘', category: '迷恋', en: 'infatuation', scripture: '林后5:13' },
  { value: 'fondness', label: '喜爱', emoji: '🥺', category: '喜爱', en: 'fondness', scripture: '彼后1:7' },
  { value: 'affection', label: '情谊', emoji: '💕', category: '情谊', en: 'affection', scripture: '罗12:10' },
  { value: 'interest', label: '兴趣', emoji: '👀', category: '兴趣', en: 'interest', scripture: '彼前2:2' },
  { value: 'curiosity', label: '好奇', emoji: '🤔', category: '好奇', en: 'curiosity', scripture: '箴2:4' },
]

// 正向情绪 — 平静与安宁类
const positiveEmotionsCalm = [
  { value: 'invigoration', label: '振奋', emoji: '💪', category: '振奋', en: 'invigoration', scripture: '弗6:10' },
  { value: 'encouragement', label: '受到鼓励', emoji: '📈', category: '受鼓励', en: 'encouragement', scripture: '帖前5:11' },
  { value: 'peace', label: '平静', emoji: '😌', category: '平静', en: 'peace', scripture: '约14:27' },
  { value: 'tranquility', label: '宁静', emoji: '🧘', category: '宁静', en: 'tranquility', scripture: '诗23:2' },
  { value: 'serenity', label: '安宁', emoji: '🕊️', category: '安宁', en: 'serenity', scripture: '赛26:3' },
  { value: 'security', label: '安全感', emoji: '🛡️', category: '安全感', en: 'security', scripture: '彼前1:5' },
]

// 正向情绪 — 释然与满足类
const positiveEmotionsRelief = [
  { value: 'relief', label: '如释重负', emoji: '😮', category: '释然', en: 'relief', scripture: '诗32:1' },
  { value: 'lightness', label: '轻松', emoji: '🎈', category: '轻松', en: 'lightness', scripture: '太11:28' },
  { value: 'comfort', label: '慰藉', emoji: '🛋️', category: '慰藉', en: 'comfort', scripture: '约14:16' },
  { value: 'enjoyment', label: '享受', emoji: '😋', category: '享受', en: 'enjoyment', scripture: '诗34:8' },
  { value: 'fulfillment', label: '充实', emoji: '✅', category: '充实', en: 'fulfillment', scripture: '腓4:19' },
  { value: 'satisfaction', label: '满足', emoji: '👍', category: '满足', en: 'satisfaction', scripture: '太25:23' },
]

// 负向情绪 — 孤独类
const negativeEmotionsLonely = [
  { value: 'loneliness', label: '孤独', emoji: '💔', category: '孤独', en: 'loneliness', scripture: '诗22:1' },
  { value: 'solitude', label: '独处', emoji: '🚶', category: '独处', en: 'solitude', scripture: '路8:3' },
  { value: 'isolation', label: '被孤立', emoji: '🏝️', category: '被孤立', en: 'isolation', scripture: '加4:16' },
  { value: 'hunger', label: '内心空乏', emoji: '😣', category: '空乏', en: 'hunger', scripture: '太5:3' },
]

// 负向情绪 — 悲伤与绝望类
const negativeEmotionsSad = [
  { value: 'sadness', label: '悲伤', emoji: '😢', category: '悲伤', en: 'sadness', scripture: '太5:4' },
  { value: 'sorrow', label: '忧郁', emoji: '😞', category: '忧郁', en: 'sorrow', scripture: '诗51:17' },
  { value: 'grief', label: '哀痛', emoji: '😭', category: '哀痛', en: 'grief', scripture: '诗30:5' },
  { value: 'anguish', label: '痛苦', emoji: '💔', category: '痛苦', en: 'anguish', scripture: '罗9:2' },
  { value: 'despair', label: '绝望', emoji: '🌑', category: '绝望', en: 'despair', scripture: '伯3:20' },
  { value: 'hopelessness', label: '无望', emoji: '⚫', category: '无望', en: 'hopelessness', scripture: '箴13:12' },
]

// 负向情绪 — 失落与懊悔类
const negativeEmotionsLoss = [
  { value: 'loss', label: '失落', emoji: '📉', category: '失落', en: 'loss', scripture: '传1:2' },
  { value: 'emptiness', label: '空虚', emoji: '🕳️', category: '空虚', en: 'emptiness', scripture: '耶2:13' },
  { value: 'regret', label: '后悔', emoji: '😔', category: '后悔', en: 'regret', scripture: '太27:3' },
  { value: 'remorse', label: '懊悔', emoji: '😖', category: '懊悔', en: 'remorse', scripture: '林后7:10' },
  { value: 'self_condemnation', label: '自责', emoji: '💢', category: '自责', en: 'self-condemnation', scripture: '约壹3:20' },
]

// 负向情绪 — 羞耻类
const negativeEmotionsShame = [
  { value: 'shame', label: '羞耻', emoji: '🔴', category: '羞耻', en: 'shame', scripture: '创3:7' },
  { value: 'embarrassment', label: '尴尬', emoji: '😳', category: '尴尬', en: 'embarrassment', scripture: '来12:2' },
  { value: 'guilt', label: '愧疚', emoji: '⛓️', category: '愧疚', en: 'guilt', scripture: '罗8:1' },
]

// 负向情绪 — 恐惧与焦虑类
const negativeEmotionsFear = [
  { value: 'fear', label: '恐惧', emoji: '😱', category: '恐惧', en: 'fear', scripture: '箴9:10' },
  { value: 'dread', label: '害怕', emoji: '😨', category: '害怕', en: 'dread', scripture: '提后1:7' },
  { value: 'anxiety', label: '焦虑', emoji: '😰', category: '焦虑', en: 'anxiety', scripture: '腓4:6' },
  { value: 'worry', label: '担忧', emoji: '🤯', category: '担忧', en: 'worry', scripture: '太6:30' },
  { value: 'nervousness', label: '紧张', emoji: '😬', category: '紧张', en: 'nervousness', scripture: '彼前3:15' },
  { value: 'panic', label: '惊慌', emoji: '😵', category: '惊慌', en: 'panic', scripture: '诗46:1-2' },
]

// 负向情绪 — 愤怒类
const negativeEmotionsAnger = [
  { value: 'anger', label: '愤怒', emoji: '😠', category: '愤怒', en: 'anger', scripture: '弗4:26' },
  { value: 'rage', label: '愤恨', emoji: '🤬', category: '愤恨', en: 'rage', scripture: '雅1:20' },
  { value: 'fury', label: '暴怒', emoji: '😡', category: '暴怒', en: 'fury', scripture: '箴14:17' },
  { value: 'irritation', label: '烦躁', emoji: '😤', category: '烦躁', en: 'irritation', scripture: '箴14:29' },
  { value: 'impatience', label: '急躁', emoji: '⏱️', category: '急躁', en: 'impatience', scripture: '加5:22-23' },
]

// 负向情绪 — 厌恶类
const negativeEmotionsDisgust = [
  { value: 'disgust', label: '厌恶', emoji: '🤢', category: '厌恶', en: 'disgust', scripture: '诗97:10' },
  { value: 'contempt', label: '鄙视', emoji: '😒', category: '鄙视', en: 'contempt', scripture: '箴18:12' },
  { value: 'jealousy', label: '嫉妒', emoji: '😒', category: '嫉妒', en: 'jealousy', scripture: '加5:19-21' },
  { value: 'envy', label: '羡慕嫉妒', emoji: '👀', category: '羡慕', en: 'envy', scripture: '来13:5' },
]

// 复杂/关系情绪 — 同理心类
const complexEmotionsCompassion = [
  { value: 'compassion', label: '怜悯', emoji: '🧡', category: '怜悯', en: 'compassion', scripture: '腓1:8' },
  { value: 'sympathy', label: '同情', emoji: '🤝', category: '同情', en: 'sympathy', scripture: '罗12:15' },
  { value: 'empathy', label: '共情', emoji: '💜', category: '共情', en: 'empathy', scripture: '来4:15' },
  { value: 'comprehension', label: '豁然开朗', emoji: '💡', category: '领悟', en: 'comprehension', scripture: '弗1:18' },
  { value: 'forgiveness', label: '释怀', emoji: '🕊️', category: '释怀', en: 'forgiveness', scripture: '太6:14' },
  { value: 'pardon', label: '宽恕', emoji: '✝️', category: '宽恕', en: 'pardon', scripture: '诗103:3' },
]

// 复杂/关系情绪 — 矛盾与迷茫类
const complexEmotionsAmbivalence = [
  { value: 'ambivalence', label: '矛盾纠结', emoji: '⚖️', category: '矛盾', en: 'ambivalence', scripture: '加5:17' },
  { value: 'confusion', label: '迷茫', emoji: '🌫️', category: '迷茫', en: 'confusion', scripture: '彼后3:16' },
  { value: 'uncertainty', label: '不确定', emoji: '❓', category: '不确定', en: 'uncertainty', scripture: '箴3:5-6' },
  { value: 'doubt', label: '怀疑', emoji: '🤔', category: '怀疑', en: 'doubt', scripture: '太14:31' },
  { value: 'defensiveness', label: '防御', emoji: '🛡️', category: '防御', en: 'defensiveness', scripture: '林后10:5' },
  { value: 'alienation', label: '疏离', emoji: '🧱', category: '疏离', en: 'alienation', scripture: '西1:21' },
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

export default function DecisionSupportPage({ user, onBack, embedded = false, onNeedLogin }) {
  const [renderError, setRenderError] = useState(null)
  const [activeTab, setActiveTab] = useState('personality') // new, history, principles
  const [loading, setLoading] = useState(false)
  const [decisions, setDecisions] = useState([])
  const [selectedDecision, setSelectedDecision] = useState(null)
  
  // ==================== 用户个人标签系统 ====================
  const [userTags, setUserTags] = useState([])
  const [tagInsights, setTagInsights] = useState(null)
  const [tagsLoading, setTagsLoading] = useState(false)

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

  // ── 4步属灵分辨 state ──────────────────────────────────────────────────────
  const [discernStep,          setDiscernStep]          = useState(1)
  const [discernSituation,     setDiscernSituation]     = useState('')
  const [discernCategory,      setDiscernCategory]      = useState('')
  const [discernMovement,      setDiscernMovement]      = useState('') // consolation|desolation|uncertain
  const [discernMovementNote,  setDiscernMovementNote]  = useState('')
  const [discernKeyword,       setDiscernKeyword]       = useState('')
  const [discernVerses,        setDiscernVerses]        = useState([])
  const [discernVersesLoading, setDiscernVersesLoading] = useState(false)
  const [discernPrayer,        setDiscernPrayer]        = useState('')
  const [discernPrayerLoading, setDiscernPrayerLoading] = useState(false)
  const userId = String(user?.id || user?.email || 'default_user')

  // 加载决策历史
  useEffect(() => {
    if (activeTab === 'history') {
      loadDecisions()
    }
  }, [activeTab])
  
  // 加载用户标签
  useEffect(() => {
    if (user?.id || user?.userId) {
      loadUserTags()
    }
  }, [user])

  // 加载人格塑造档案和行为统计，预填充决策表单
  useEffect(() => {
    if ((user?.id || user?.userId) && activeTab === 'new') {
      loadProfileAndPreFillForm()
    }
  }, [user, activeTab])

  const loadProfileAndPreFillForm = async () => {
    const uid = user?.id || user?.userId
    if (!uid) return

    try {
      const token = getToken()
      const [profileData, behaviorStats] = await Promise.all([
        fetchFormationProfile(uid, token).catch(() => null),
        Promise.resolve(null)
      ])

      // 从人格塑造档案提取默认值
      const stateVector = profileData?.profile?.state_vector || {}
      const deltas = profileData?.profile?.deltas || {}

      // 将 0.05-0.95 范围的值映射到 1-10 整数
      const mapScore = (score) => Math.round(((score || 0.5) * 10))

      // 计算动态默认值（基于人格数据 + 近期趋势）
      const dynamicDefaults = {
        // 恐惧倾向越高，焦虑水平越高
        anxietyLevel: Math.min(10, Math.max(1, mapScore(stateVector.fear_tendency) + (deltas.fear_tendency > 0 ? 1 : 0))),
        // 情绪稳定性维度直接映射（越高越稳定，所以取反）
        emotionalStability: mapScore(stateVector.emotional_stability),
        // 灵性清晰度映射到灵性干涸（越清晰越不干涸）
        spiritualDryness: Math.min(10, Math.max(1, 11 - mapScore(stateVector.spiritual_clarity))),
        // 骄傲倾向越高，身份困惑可能越高
        identityConfusion: Math.min(10, Math.max(1, mapScore(stateVector.pride_tendency) - 2)),
        // 真理对齐度映射到道德张力（越对齐张力越低）
        moralTension: Math.min(10, Math.max(1, 11 - mapScore(stateVector.truth_alignment))),
        // 关系健康映射到社交连接
        socialConnection: mapScore(stateVector.relational_health),
        // 韧性映射到压力水平（韧性越低压力感受越高）
        stressLevel: Math.min(10, Math.max(1, 11 - mapScore(stateVector.resilience))),
      }

      // 从行为统计补充（如果有）
      if (behaviorStats?.avg_energy_level) {
        // 平均能量等级低可能表示疲劳
        dynamicDefaults.fatigueLevel = Math.min(10, Math.max(1, Math.round(11 - behaviorStats.avg_energy_level * 2)))
      }

      // 从疲劳趋势判断压力水平
      if (behaviorStats?.fatigue_trend) {
        if (behaviorStats.fatigue_trend === 'high') {
          dynamicDefaults.stressLevel = Math.min(10, dynamicDefaults.stressLevel + 2)
          dynamicDefaults.fatigueLevel = Math.min(10, dynamicDefaults.fatigueLevel + 1)
        } else if (behaviorStats.fatigue_trend === 'moderate') {
          dynamicDefaults.stressLevel = Math.min(10, dynamicDefaults.stressLevel + 1)
        }
      }

      // 从Red电路占比判断情绪稳定性
      if (behaviorStats?.red_tier_ratio > 30) {
        dynamicDefaults.emotionalStability = Math.max(1, dynamicDefaults.emotionalStability - 2)
      } else if (behaviorStats?.red_tier_ratio > 15) {
        dynamicDefaults.emotionalStability = Math.max(1, dynamicDefaults.emotionalStability - 1)
      }

      // 从睡眠质量推断（如果近期能量持续低，睡眠质量可能受影响）
      if (behaviorStats?.avg_energy_30d < 2.5) {
        dynamicDefaults.sleepQuality = Math.max(1, dynamicDefaults.sleepQuality - 2)
      } else if (behaviorStats?.avg_energy_30d < 3) {
        dynamicDefaults.sleepQuality = Math.max(1, dynamicDefaults.sleepQuality - 1)
      }

      // 计算轨迹方向影响
      const trajectory = profileData?.profile?.trajectory_direction || 'unknown'
      if (trajectory === 'increasing_volatility' || trajectory === 'fragmenting') {
        // 波动性增加时，稍微提高焦虑感知
        dynamicDefaults.anxietyLevel = Math.min(10, dynamicDefaults.anxietyLevel + 1)
        dynamicDefaults.sleepQuality = Math.max(1, (dynamicDefaults.sleepQuality || 5) - 1)
      } else if (trajectory === 'stabilizing' || trajectory === 'improving_clarity') {
        // 趋于稳定时，提高情绪稳定性默认值
        dynamicDefaults.emotionalStability = Math.min(10, (dynamicDefaults.emotionalStability || 5) + 1)
      }

      // 更新表单默认值（仅在用户未修改过对应字段时）
      setFormData(prev => ({
        ...prev,
        ...dynamicDefaults,
        // 保留用户已输入的内容
        title: prev.title || '',
        description: prev.description || '',
        category: prev.category || '',
        emotions: prev.emotions || [],
      }))

      console.log('[DecisionSupport] Pre-filled form from profile:', dynamicDefaults)
    } catch (err) {
      console.log('[DecisionSupport] loadProfileAndPreFillForm failed:', err)
      // 静默失败，不影响用户体验
    }
  }

  const loadUserTags = async () => {
    const userId = user?.id || user?.userId
    if (!userId) return
    
    setTagsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/user-tags/${userId}?include_insights=true&limit=20`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      })
      if (res.ok) {
        const data = await res.json()
        setUserTags(data.tags || [])
        setTagInsights(data.insights || null)
      }
    } catch (err) {
      console.log('[DecisionSupport] load user tags failed:', err)
    } finally {
      setTagsLoading(false)
    }
  }
  
  // 渲染用户标签组件
  const renderUserTags = () => {
    if (tagsLoading || userTags.length === 0) return null
    
    // 按分类分组
    const tagsByCategory = userTags.reduce((acc, tag) => {
      const cat = tag.tag_category || '其他'
      if (!acc[cat]) acc[cat] = []
      acc[cat].push(tag)
      return acc
    }, {})
    
    // 分类中文映射
    const categoryNames = {
      'emotion_type': '情绪特征',
      'life_domain': '生活领域',
      'behavior': '行为模式',
      'value': '价值观',
      'relationship': '关系模式',
      'spiritual': '灵性状态',
      'cognitive': '认知风格',
      'decision': '决策风格',
      'manual': '手动添加',
      'unknown': '其他'
    }
    
    // 分类颜色
    const categoryColors = {
      'emotion_type': '#ff6b6b',
      'life_domain': '#4ecdc4',
      'behavior': '#ffe66d',
      'value': '#95e1d3',
      'relationship': '#f38181',
      'spiritual': '#aa96da',
      'cognitive': '#fcbad3',
      'decision': '#ffffd2',
      'manual': '#a8e6cf',
      'unknown': '#aaa'
    }
    
    return (
      <div style={{
        margin: '16px',
        padding: '16px',
        borderRadius: '12px',
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '12px',
        }}>
          <div style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
            🏷️ 我的个人标签
          </div>
          {tagInsights && (
            <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)' }}>
              共 {tagInsights.total_tags} 个标签 · {tagInsights.total_categories} 个维度
            </div>
          )}
        </div>
        
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {userTags.slice(0, 15).map((tag, idx) => {
            const color = categoryColors[tag.tag_category] || '#aaa'
            const weight = tag.weight || 1
            const opacity = Math.min(0.3 + (weight * 0.15), 0.9)
            
            return (
              <div
                key={tag.id || idx}
                style={{
                  padding: '4px 10px',
                  borderRadius: '16px',
                  background: `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`,
                  color: '#fff',
                  fontSize: '12px',
                  border: `1px solid ${color}40`,
                  cursor: 'default',
                  transition: 'all 0.2s',
                }}
                title={`${categoryNames[tag.tag_category] || tag.tag_category} · 权重: ${tag.weight?.toFixed(2) || 1} · 出现: ${tag.occurrence_count || 1}次`}
              >
                {tag.tag_name}
              </div>
            )
          })}
        </div>
        
        {userTags.length > 15 && (
          <div style={{ 
            marginTop: '8px', 
            fontSize: '11px', 
            color: 'rgba(255,255,255,0.4)',
            textAlign: 'center'
          }}>
            +{userTags.length - 15} 更多标签
          </div>
        )}
      </div>
    )
  }

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

  // 灵镜分析 — 调用 MVFE /process, 并自动触发属灵辨识
  const handleMvfeAnalysis = async (text, autoSubmit = true) => {
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
      
      // 自动触发属灵辨识（如果表单已填写完整）
      if (autoSubmit) {
        // 使用 setTimeout 确保 state 更新完成
        setTimeout(() => {
          submitDiscernment(d)
        }, 100)
      }
      
      return d
    } catch (err) {
      setMvfeError(err.message)
      return null
    } finally {
      setMvfeProcessing(false)
    }
  }
  
  // 提交属灵辨识（从 handleSubmit 提取的独立函数）
  const submitDiscernment = async (mvfeData) => {
    // 检查必填字段
    if (!formData.title || !formData.category) {
      // 如果缺少必填字段，只显示分析结果，不自动提交
      console.log('[DecisionSupport] 缺少标题或类别，跳过自动提交')
      return
    }
    
    setLoading(true)
    try {
      const token = getToken()
      
      // 使用最新 formData 构建提交数据
      const latestForm = formData
      
      const payload = {
        title: latestForm.title,
        description: latestForm.description,
        category: latestForm.category,
        urgency: latestForm.urgency,
        importance: latestForm.importance,
        state_snapshot: {
          stress_level: latestForm.stressLevel,
          anxiety_level: latestForm.anxietyLevel,
          fatigue_level: latestForm.fatigueLevel,
          spiritual_dryness: latestForm.spiritualDryness,
          emotional_stability: latestForm.emotionalStability,
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
          mvfe_event_id: mvfeData?.event_id || null,
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
      // 静默失败，不打扰用户，只记录日志
      console.log('[DecisionSupport] 自动辨识未启动:', err.message)
    } finally {
      setLoading(false)
    }
  }

  // 自动从 MVFE 分析结果映射到决策表单
  const autoMapMvfeToForm = (mvfe) => {
    if (!mvfe) return
    const em = mvfe.emotion || {}
    const at = mvfe.attention || {}
    const fo = mvfe.formation || {}
    const dc = mvfe.decision || {}

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
      financialPressure: dc?.drivers?.ego > 0.6 ? 7 : (dc?.drivers?.fear > 0.6 ? 6 : 4),
      cognitiveClarity: 10 - Math.round((em.uncertainty || 0.3) * 10),
      identityConfusion: em.secondary_emotions?.includes('confusion') ? 7 : (at.fixation_score > 0.7 ? 6 : 4),
      moralTension: dc?.drivers?.love < 0.3 && dc?.drivers?.ego > 0.5 ? 6 : 4,
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

  // 渲染新决策表单
  const renderNewDecisionForm = () => {
    const DECISION_CATS = [
      { value:'career', emoji:'💼', label:'职业发展' },
      { value:'relationship', emoji:'💞', label:'关系婚姻' },
      { value:'family', emoji:'🏠', label:'家庭责任' },
      { value:'church', emoji:'⛪', label:'事奉职分' },
      { value:'financial', emoji:'💰', label:'财务奉献' },
      { value:'health', emoji:'🏃', label:'健康身体' },
      { value:'education', emoji:'🎓', label:'学习进修' },
      { value:'relocation', emoji:'✈️', label:'搬迁移居' },
      { value:'ministry', emoji:'🙏', label:'使命呼召' },
      { value:'conflict', emoji:'🤝', label:'人际冲突' },
      { value:'forgiveness', emoji:'💙', label:'饶恕和好' },
      { value:'other', emoji:'💡', label:'其他决策' },
    ]

    const MOVEMENT_OPTS = [
      { value:'consolation', emoji:'☀️', label:'神慰', color:'#34c759',
        desc:'感到平静、喜乐、信心加增、爱的流动，似乎与神更靠近' },
      { value:'desolation',  emoji:'🌧️', label:'神枯', color:'#f87171',
        desc:'感到黑暗、混乱、平静消失、拒绝神的冲动，似乎与神疏远' },
      { value:'uncertain',   emoji:'🌫️', label:'不确定', color:'#fbbf24',
        desc:'难以辨别，内心混合，需要更多等候和观察' },
    ]

    async function searchVerses() {
      if (!discernKeyword.trim()) return
      setDiscernVersesLoading(true)
      try {
        const res = await fetch(API_BASE + '/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: discernKeyword.trim(), topVerses: 5, topFeatures: 3 }),
        })
        const data = await res.json()
        setDiscernVerses(data.verses || data.results || [])
      } catch (err) {
        console.error('[Discern] verse search error:', err)
        setDiscernVerses([])
      } finally {
        setDiscernVersesLoading(false)
      }
    }

    async function generatePrayer() {
      setDiscernPrayerLoading(true)
      const mv = MOVEMENT_OPTS.find(o => o.value === discernMovement)
      const prompt = `我面临的处境：${discernSituation}\n内心感受（${mv?.label || ''}）：${discernMovementNote || '尚未填写'}\n相关经文：${discernVerses.slice(0,2).map(v => v.reference || v.text || '').join('；') || '暂无'}\n\n请为这个处境和心境，生成一段真诚的属灵祷告文（150-200字），用第一人称，融入经文，向神坦陈内心。`
      try {
        const res = await fetch(API_BASE + '/guidance', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: prompt }),
        })
        const data = await res.json()
        setDiscernPrayer(data.guidance || data.result || data.text || '祷告生成失败，请重试。')
      } catch (err) {
        console.error('[Discern] prayer gen error:', err)
        setDiscernPrayer('祷告生成失败，请检查网络连接后重试。')
      } finally {
        setDiscernPrayerLoading(false)
      }
    }

    const stepDone = [
      discernSituation.trim().length > 0 && discernCategory !== '',
      discernMovement !== '',
      true, // verse search optional
    ]
    const canNext = stepDone[discernStep - 1]

    return (
      <div style={{ padding: '0 16px 24px' }}>
        {/* 步骤进度条 */}
        <div style={{ display:'flex', alignItems:'center', gap:6, marginBottom:20, paddingTop:4 }}>
          {[1,2,3,4].map(n => (
            <div key={n} style={{ display:'flex', alignItems:'center', gap:6, flex: n < 4 ? 1 : 0 }}>
              <div style={{
                width:28, height:28, borderRadius:'50%', flexShrink:0,
                display:'flex', alignItems:'center', justifyContent:'center',
                background: discernStep > n ? 'rgba(52,199,89,0.25)'
                          : discernStep === n ? 'rgba(90,200,250,0.2)'
                          : 'rgba(255,255,255,0.07)',
                border: discernStep > n ? '1.5px solid rgba(52,199,89,0.6)'
                       : discernStep === n ? '1.5px solid rgba(90,200,250,0.6)'
                       : '1.5px solid rgba(255,255,255,0.12)',
                color: discernStep > n ? '#34c759' : discernStep === n ? '#5ac8fa' : 'rgba(255,255,255,0.3)',
                fontSize: 12, fontWeight:700,
              }}>{discernStep > n ? '✓' : n}</div>
              {n < 4 && <div style={{ flex:1, height:2, borderRadius:1, background: discernStep > n ? 'rgba(52,199,89,0.4)' : 'rgba(255,255,255,0.08)' }} />}
            </div>
          ))}
        </div>

        {/* ── 第一步：描述处境 ── */}
        {discernStep === 1 && (
          <div>
            <div style={{ fontSize:16, fontWeight:700, color:'#fff', marginBottom:6 }}>第一步：描述处境</div>
            <div style={{ fontSize:12, color:'rgba(255,255,255,0.4)', marginBottom:16 }}>用一两句话说出你正在面对的处境或决策</div>

            <textarea
              value={discernSituation}
              onChange={e => setDiscernSituation(e.target.value)}
              placeholder="例如：我收到了另一家公司的工作邀请，薪资更高但离家更远…"
              rows={4}
              style={{
                width:'100%', boxSizing:'border-box',
                background:'rgba(255,255,255,0.05)',
                border:'1px solid rgba(255,255,255,0.12)',
                borderRadius:10, padding:'12px 14px',
                color:'rgba(255,255,255,0.9)', fontSize:14,
                lineHeight:1.65, resize:'none', outline:'none',
                fontFamily:'inherit', marginBottom:16,
              }}
            />

            <div style={{ fontSize:12, fontWeight:700, color:'rgba(255,255,255,0.5)', marginBottom:10 }}>这属于哪类处境？</div>
            <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:8 }}>
              {DECISION_CATS.map(cat => (
                <button key={cat.value} onClick={() => setDiscernCategory(cat.value)} style={{
                  padding:'8px 6px', borderRadius:10,
                  border:`1px solid ${discernCategory === cat.value ? 'rgba(90,200,250,0.5)' : 'rgba(255,255,255,0.08)'}`,
                  background: discernCategory === cat.value ? 'rgba(90,200,250,0.12)' : 'rgba(255,255,255,0.04)',
                  color: discernCategory === cat.value ? '#5ac8fa' : 'rgba(255,255,255,0.6)',
                  fontSize:12, fontWeight: discernCategory === cat.value ? 700 : 400,
                  cursor:'pointer', textAlign:'center',
                }}>
                  <div style={{ fontSize:16, marginBottom:2 }}>{cat.emoji}</div>
                  {cat.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── 第二步：神慰/神枯 ── */}
        {discernStep === 2 && (
          <div>
            <div style={{ fontSize:16, fontWeight:700, color:'#fff', marginBottom:6 }}>第二步：内心感受</div>
            <div style={{ fontSize:12, color:'rgba(255,255,255,0.4)', marginBottom:4 }}>
              在这个处境中，你内心有什么样的属灵感受？
            </div>
            <div style={{ fontSize:11, color:'rgba(255,255,255,0.25)', marginBottom:16, fontStyle:'italic' }}>
              伊纳爵灵修传统：神慰指向神，神枯需分辨根源
            </div>

            <div style={{ display:'flex', flexDirection:'column', gap:10, marginBottom:16 }}>
              {MOVEMENT_OPTS.map(opt => (
                <button key={opt.value} onClick={() => setDiscernMovement(opt.value)} style={{
                  padding:'14px 16px', borderRadius:14, textAlign:'left',
                  border:`1px solid ${discernMovement === opt.value ? opt.color + '60' : 'rgba(255,255,255,0.08)'}`,
                  background: discernMovement === opt.value ? opt.color + '12' : 'rgba(255,255,255,0.04)',
                  cursor:'pointer',
                }}>
                  <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:4 }}>
                    <span style={{ fontSize:20 }}>{opt.emoji}</span>
                    <span style={{ fontSize:14, fontWeight:700, color: discernMovement === opt.value ? opt.color : '#fff' }}>{opt.label}</span>
                  </div>
                  <div style={{ fontSize:12, color:'rgba(255,255,255,0.45)', paddingLeft:30, lineHeight:1.5 }}>{opt.desc}</div>
                </button>
              ))}
            </div>

            {discernMovement && (
              <div>
                <div style={{ fontSize:12, fontWeight:700, color:'rgba(255,255,255,0.5)', marginBottom:8 }}>
                  简短描述你的感受原因（可选）
                </div>
                <textarea
                  value={discernMovementNote}
                  onChange={e => setDiscernMovementNote(e.target.value)}
                  placeholder="例如：每次想到这个方向，内心就感到平安和兴奋；但想到另一个方向，就感到焦虑…"
                  rows={3}
                  style={{
                    width:'100%', boxSizing:'border-box',
                    background:'rgba(255,255,255,0.05)',
                    border:'1px solid rgba(255,255,255,0.1)',
                    borderRadius:10, padding:'10px 12px',
                    color:'rgba(255,255,255,0.85)', fontSize:13,
                    lineHeight:1.6, resize:'none', outline:'none',
                    fontFamily:'inherit',
                  }}
                />
              </div>
            )}
          </div>
        )}

        {/* ── 第三步：经文检索 ── */}
        {discernStep === 3 && (
          <div>
            <div style={{ fontSize:16, fontWeight:700, color:'#fff', marginBottom:6 }}>第三步：相关经文</div>
            <div style={{ fontSize:12, color:'rgba(255,255,255,0.4)', marginBottom:16 }}>
              输入一个关键词，检索与你处境相关的圣经经文（可跳过）
            </div>

            <div style={{ display:'flex', gap:8, marginBottom:14 }}>
              <input
                value={discernKeyword}
                onChange={e => setDiscernKeyword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && searchVerses()}
                placeholder="如：工作、等候、恐惧、信靠、呼召…"
                style={{
                  flex:1, background:'rgba(255,255,255,0.06)',
                  border:'1px solid rgba(255,255,255,0.12)',
                  borderRadius:8, padding:'10px 12px',
                  color:'#fff', fontSize:13, outline:'none', fontFamily:'inherit',
                }}
              />
              <button onClick={searchVerses} disabled={!discernKeyword.trim() || discernVersesLoading} style={{
                padding:'10px 16px', borderRadius:8, border:'none',
                background: discernKeyword.trim() ? 'rgba(90,200,250,0.2)' : 'rgba(255,255,255,0.07)',
                color: discernKeyword.trim() ? '#5ac8fa' : 'rgba(255,255,255,0.3)',
                fontSize:13, fontWeight:600, cursor:'pointer', flexShrink:0,
              }}>
                {discernVersesLoading ? '⏳' : '检索'}
              </button>
            </div>

            {discernVerses.length > 0 && (
              <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
                {discernVerses.slice(0, 5).map((v, i) => (
                  <div key={i} style={{
                    background:'rgba(255,215,0,0.05)',
                    borderLeft:'3px solid rgba(255,215,0,0.35)',
                    borderRadius:'0 8px 8px 0',
                    padding:'10px 12px',
                  }}>
                    {v.reference && <div style={{ fontSize:11, color:'rgba(255,215,0,0.7)', fontWeight:700, marginBottom:4 }}>{v.reference}</div>}
                    <div style={{ fontSize:13, color:'rgba(255,255,255,0.82)', lineHeight:1.65 }}>{v.text || v.verse || v.content || JSON.stringify(v)}</div>
                  </div>
                ))}
              </div>
            )}

            {discernVerses.length === 0 && !discernVersesLoading && discernKeyword && (
              <div style={{ textAlign:'center', padding:'20px', color:'rgba(255,255,255,0.3)', fontSize:13 }}>
                未找到相关经文，尝试其他关键词
              </div>
            )}

            <div style={{ marginTop:16, padding:'10px 14px', background:'rgba(255,255,255,0.04)', borderRadius:10 }}>
              <div style={{ fontSize:11, color:'rgba(255,255,255,0.3)' }}>
                💡 你也可以直接跳到第四步生成祷告文
              </div>
            </div>
          </div>
        )}

        {/* ── 第四步：祷告文 ── */}
        {discernStep === 4 && (
          <div>
            <div style={{ fontSize:16, fontWeight:700, color:'#fff', marginBottom:6 }}>第四步：属灵祷告</div>
            <div style={{ fontSize:12, color:'rgba(255,255,255,0.4)', marginBottom:16 }}>
              基于你的处境和内心感受，生成一段属灵祷告文
            </div>

            {/* 分辨摘要 */}
            <div style={{ background:'rgba(255,255,255,0.04)', borderRadius:12, padding:'12px 14px', marginBottom:16 }}>
              <div style={{ fontSize:11, color:'rgba(255,255,255,0.35)', marginBottom:6 }}>分辨摘要</div>
              <div style={{ fontSize:13, color:'rgba(255,255,255,0.75)', lineHeight:1.6, marginBottom:6 }}>
                {discernSituation || '（未填写处境）'}
              </div>
              {discernMovement && (
                <div style={{ fontSize:12, color: MOVEMENT_OPTS.find(o => o.value === discernMovement)?.color || '#fff' }}>
                  {MOVEMENT_OPTS.find(o => o.value === discernMovement)?.emoji} {MOVEMENT_OPTS.find(o => o.value === discernMovement)?.label}
                  {discernMovementNote && `：${discernMovementNote.slice(0, 60)}${discernMovementNote.length > 60 ? '…' : ''}`}
                </div>
              )}
            </div>

            {!discernPrayer ? (
              <button onClick={generatePrayer} disabled={discernPrayerLoading} style={{
                width:'100%', padding:'14px',
                borderRadius:12, border:'none',
                background: discernPrayerLoading ? 'rgba(120,120,128,0.2)' : 'rgba(52,199,89,0.2)',
                color: discernPrayerLoading ? 'rgba(255,255,255,0.4)' : '#34c759',
                fontSize:14, fontWeight:700, cursor:'pointer',
                display:'flex', alignItems:'center', justifyContent:'center', gap:8,
              }}>
                {discernPrayerLoading ? (
                  <><span>⏳</span><span>祷告文生成中…</span></>
                ) : (
                  <><span>🙏</span><span>生成属灵祷告文</span></>
                )}
              </button>
            ) : (
              <div>
                <div style={{
                  background:'rgba(52,199,89,0.06)',
                  border:'1px solid rgba(52,199,89,0.2)',
                  borderRadius:14, padding:'16px',
                  marginBottom:12,
                }}>
                  <div style={{ fontSize:11, color:'rgba(52,199,89,0.7)', fontWeight:700, marginBottom:10 }}>🙏 属灵祷告</div>
                  <div style={{ fontSize:14, color:'rgba(255,255,255,0.88)', lineHeight:1.85, whiteSpace:'pre-wrap' }}>{discernPrayer}</div>
                </div>
                <button onClick={() => { setDiscernPrayer(''); generatePrayer() }} style={{
                  width:'100%', padding:'10px',
                  borderRadius:10, border:'1px solid rgba(255,255,255,0.12)',
                  background:'transparent', color:'rgba(255,255,255,0.5)',
                  fontSize:12, cursor:'pointer',
                }}>重新生成</button>
              </div>
            )}

            {/* 重新开始 */}
            <button onClick={() => {
              setDiscernStep(1); setDiscernSituation(''); setDiscernCategory('');
              setDiscernMovement(''); setDiscernMovementNote('');
              setDiscernKeyword(''); setDiscernVerses([]); setDiscernPrayer('');
            }} style={{
              width:'100%', marginTop:12, padding:'8px',
              borderRadius:8, border:'none',
              background:'transparent', color:'rgba(255,255,255,0.25)',
              fontSize:11, cursor:'pointer',
            }}>↩ 重新开始分辨</button>
          </div>
        )}

        {/* 上一步 / 下一步 按钮 */}
        <div style={{ display:'flex', gap:10, marginTop:24 }}>
          {discernStep > 1 && (
            <button onClick={() => setDiscernStep(s => s - 1)} style={{
              flex:1, padding:'12px', borderRadius:12, border:'1px solid rgba(255,255,255,0.12)',
              background:'transparent', color:'rgba(255,255,255,0.55)',
              fontSize:14, fontWeight:600, cursor:'pointer',
            }}>← 上一步</button>
          )}
          {discernStep < 4 && (
            <button onClick={() => canNext && setDiscernStep(s => s + 1)} disabled={!canNext} style={{
              flex:2, padding:'12px', borderRadius:12, border:'none',
              background: canNext ? 'rgba(90,200,250,0.2)' : 'rgba(255,255,255,0.06)',
              color: canNext ? '#5ac8fa' : 'rgba(255,255,255,0.25)',
              fontSize:14, fontWeight:700, cursor: canNext ? 'pointer' : 'default',
            }}>下一步 →</button>
          )}
        </div>
      </div>
    )
  }


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
                  <span>{(motive_analysis.fear_driven_score * 100).toFixed(2)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.fear_driven_score * 100}%`, background: '#ff3b30' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>😤 骄傲驱动</span>
                  <span>{(motive_analysis.pride_driven_score * 100).toFixed(2)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.pride_driven_score * 100}%`, background: '#ff9500' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>❤️ 爱驱动</span>
                  <span>{(motive_analysis.love_driven_score * 100).toFixed(2)}%</span>
                </div>
                <div style={progressBarBg}>
                  <div style={{ ...progressBarFill, width: `${motive_analysis.love_driven_score * 100}%`, background: '#34c759' }} />
                </div>
              </div>
              
              <div style={progressBarContainer}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                  <span>🔥 欲望驱动</span>
                  <span>{(motive_analysis.desire_driven_score * 100).toFixed(2)}%</span>
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
                <span>置信度: {(discernment_result.confidence * 100).toFixed(2)}%</span>
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

        {/* SFDS → 习惯行动链路 */}
        {guidance && (guidance.recommended_actions?.length > 0 || discernment_result) && (
          <div style={{ ...resultCardStyle, background: 'rgba(52,199,89,0.07)', border: '1px solid rgba(52,199,89,0.2)' }}>
            <div style={{ ...resultTitleStyle, color: '#34c759' }}>🌱 本周属灵操练建议</div>
            <div style={{ fontSize: '13px', color: 'rgba(255,255,255,0.7)', marginBottom: '12px', lineHeight: 1.6 }}>
              根据辨识结果，建议本周将以下操练设为习惯：
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
              {[
                discernment_result?.dominant_source === 'fear' && '每日5分钟：写下一件神过去信实的事（感恩日记）',
                discernment_result?.dominant_source === 'pride' && '每日晨祷：「神啊，今天让我在谦卑中事奉」',
                guidance.recommended_actions?.[0] && `行动操练：${guidance.recommended_actions[0]}`,
                '每周至少一次：在安静中等候神（默观祷告）',
              ].filter(Boolean).slice(0, 3).map((practice, i) => (
                <div key={i} style={{
                  padding: '9px 12px', background: 'rgba(52,199,89,0.12)',
                  borderRadius: '8px', fontSize: '13px', color: 'rgba(255,255,255,0.85)',
                  borderLeft: '3px solid #34c759',
                }}>
                  {practice}
                </div>
              ))}
            </div>
            <button
              onClick={() => setActiveTab('habits')}
              style={{
                width: '100%', padding: '10px', background: 'rgba(52,199,89,0.2)',
                border: '1px solid rgba(52,199,89,0.4)', borderRadius: '10px',
                color: '#34c759', fontSize: '13px', fontWeight: 700, cursor: 'pointer',
              }}
            >
              ➕ 前往习惯页面，将这些操练加入每日习惯
            </button>
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

  const loadHistoryItem = (item) => {
    setFormData(prev => ({
      ...prev,
      title: item.title || '',
      description: item.description || '',
      category: item.category || '',
      urgency: item.urgency || 3,
      importance: item.importance || 3,
    }))
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
      <SoulTabs activeTab={activeTab} onTabChange={(tab) => {
        setActiveTab(tab)
        setAnalysisResult(null)
      }} />

      {/* 用户个人标签 - 在 new tab 显示 */}
      {activeTab === 'new' && renderUserTags()}

      {/* 内容区域 */}
      <div style={{ paddingBottom: embedded ? '0' : '80px' }}>
        {activeTab === 'dashboard' && <SoulDashboard user={user} />}
        {activeTab === 'personality' && <PersonalityPage user={user} embedded={true} onSyncToHabits={() => setActiveTab('habits')} />}
        {activeTab === 'habits' && <HabitsPage user={user} token={getToken()} embedded={true} onNeedLogin={onNeedLogin} />}
        {activeTab !== 'dashboard' && activeTab !== 'personality' && activeTab !== 'habits' && (
          analysisResult ? renderAnalysisResult() : (
            <>
              {activeTab === 'new' && renderNewDecisionForm()}
            </>
          )
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
            <div style={{ fontSize: '17px', fontWeight: 600 }}>心迹</div>
          </div>
        </div>

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
