import { useEffect, useState } from 'react'
import { API_BASE } from './api'
import { getToken } from './auth'
import HabitsPage from './HabitsPage'
import PersonalityPage from './PersonalityPage'
import BehaviorPage from './BehaviorPage'

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

// 正向情绪 — 敬虔渴望类 + 数算恩典类
const positiveEmotionsLonging = [
  { value: 'desire', label: '切慕主', emoji: '💧', category: '敬虔渴望', en: 'desire', scripture: '诗42:1' },
  { value: 'longing', label: '心灵渴想', emoji: '💌', category: '属灵思念', en: 'longing', scripture: '诗63:1' },
  { value: 'reminiscence', label: '记念主恩', emoji: '📷', category: '数算恩典', en: 'reminiscence', scripture: '诗77:11' },
  { value: 'yearning', label: '切盼主来', emoji: '🌅', category: '末世盼望', en: 'yearning', scripture: '启22:20' },
  { value: 'anticipation', label: '等候神旨', emoji: '🎁', category: '安静等候', en: 'anticipation', scripture: '赛40:31' },
  { value: 'craving', label: '属灵饥渴', emoji: '🔥', category: '干渴慕义', en: 'craving', scripture: '诗63:1' },
]

// 正向情绪 — 圣灵喜乐类 + 感恩祭类
const positiveEmotionsJoy = [
  { value: 'joy', label: '属天喜乐', emoji: '😊', category: '圣灵果子', en: 'joy', scripture: '加5:22' },
  { value: 'happiness', label: '在主里欢畅', emoji: '😄', category: '以神为乐', en: 'happiness', scripture: '诗16:11' },
  { value: 'pleasure', label: '属灵愉悦', emoji: '😃', category: '爱神之乐', en: 'pleasure', scripture: '诗1:2' },
  { value: 'gladness', label: '主恩欣喜', emoji: '🙂', category: '救恩之乐', en: 'gladness', scripture: '诗30:5' },
  { value: 'bliss', label: '蒙福确据', emoji: '🥰', category: '天国福分', en: 'bliss', scripture: '太5:3-12' },
  { value: 'gratitude', label: '凡事谢恩', emoji: '🙏', category: '感恩祭', en: 'gratitude', scripture: '帖前5:18' },
  { value: 'thankfulness', label: '感戴主恩', emoji: '💝', category: '数算恩典', en: 'thankfulness', scripture: '诗107:1' },
]

// 正向情绪 — 活泼盼望类 + 事主热诚类
const positiveEmotionsHope = [
  { value: 'hope', label: '活泼盼望', emoji: '🌟', category: '盼望确据', en: 'hope', scripture: '罗15:13' },
  { value: 'optimism', label: '信靠乐观', emoji: '☀️', category: '信心眼光', en: 'optimism', scripture: '箴3:5' },
  { value: 'eagerness', label: '事主热诚', emoji: '⚡', category: '事奉热诚', en: 'eagerness', scripture: '罗12:11' },
  { value: 'ardor', label: '爱主火熱', emoji: '🔥', category: '燃烧的爱', en: 'ardor', scripture: '启3:19' },
  { value: 'fervor', label: '圣灵动工', emoji: '✨', category: '属灵火热', en: 'fervor', scripture: '徒18:25' },
  { value: 'exuberance', label: '属灵充沛', emoji: '🎉', category: '灵里丰富', en: 'exuberance', scripture: '约10:10' },
  { value: 'excitement', label: '灵里兴奋', emoji: '🤩', category: '灵恩兴奋', en: 'excitement', scripture: '徒2:46' },
  { value: 'exhilaration', label: '恩门激动', emoji: '🥳', category: '救赎之乐', en: 'exhilaration', scripture: '诗51:12' },
  { value: 'rapture', label: '被提之乐', emoji: '😇', category: '被提盼望', en: 'rapture', scripture: '帖前4:17' },
]

// 正向情绪 — 与主相爱类 + 真理探求类
const positiveEmotionsLove = [
  { value: 'fascination', label: '倾心于主', emoji: '🤯', category: '被主吸引', en: 'fascination', scripture: '雅歌 良人属我' },
  { value: 'infatuation', label: '为主癫狂', emoji: '💘', category: '基督之爱', en: 'infatuation', scripture: '林后5:13' },
  { value: 'fondness', label: '圣徒相爱', emoji: '🥺', category: '肢体相爱', en: 'fondness', scripture: '彼后1:7' },
  { value: 'affection', label: '主内情誼', emoji: '💕', category: '属亲情誼', en: 'affection', scripture: '罗12:10' },
  { value: 'interest', label: '渴慕真道', emoji: '👀', category: '爱慕神话', en: 'interest', scripture: '彼前2:2' },
  { value: 'curiosity', label: '探求真理', emoji: '🤔', category: '探索奥秘', en: 'curiosity', scripture: '箴2:4' },
]

// 正向情绪 — 肢体建造类 + 属灵安息类
const positiveEmotionsCalm = [
  { value: 'invigoration', label: '主里刚强', emoji: '💪', category: '属灵力量', en: 'invigoration', scripture: '弗6:10' },
  { value: 'encouragement', label: '互相劝勉', emoji: '📈', category: '肢体建造', en: 'encouragement', scripture: '帖前5:11' },
  { value: 'peace', label: '属灵安息', emoji: '😌', category: '基督平安', en: 'peace', scripture: '约14:27' },
  { value: 'tranquility', label: '主里宁静', emoji: '🧘', category: '安静', en: 'tranquility', scripture: '诗23:2' },
  { value: 'serenity', label: '神圣安宁', emoji: '🕊️', category: '属天安静', en: 'serenity', scripture: '赛26:3' },
  { value: 'security', label: '确信蒙保守', emoji: '🛡️', category: '安稳', en: 'security', scripture: '彼前1:5' },
]

// 正向情绪 — 赦罪释放类 + 灵里自由类 + 忠心奖赏类
const positiveEmotionsRelief = [
  { value: 'relief', label: '罪得赦免', emoji: '😮', category: '赦罪之乐', en: 'relief', scripture: '诗32:1' },
  { value: 'lightness', label: '重担脱落', emoji: '🎈', category: '脱去重担', en: 'lightness', scripture: '太11:28' },
  { value: 'comfort', label: '主里慰藉', emoji: '🛋️', category: '圣灵保惠', en: 'comfort', scripture: '约14:16' },
  { value: 'enjoyment', label: '领受恩典', emoji: '😋', category: '享受神恩', en: 'enjoyment', scripture: '诗34:8' },
  { value: 'fulfillment', label: '灵命满足', emoji: '✅', category: '完全', en: 'fulfillment', scripture: '腓4:19' },
  { value: 'satisfaction', label: '忠心良善', emoji: '👍', category: '忠心奖赏', en: 'satisfaction', scripture: '太25:23' },
]

// 负向情绪 — 被弃感类 + 寄居者类
const negativeEmotionsLonely = [
  { value: 'loneliness', label: '孤单无依', emoji: '💔', category: '被弃感', en: 'loneliness', scripture: '诗22:1' },
  { value: 'solitude', label: '独处孤独', emoji: '🚶', category: '无人同行', en: 'solitude', scripture: '路8:3' },
  { value: 'isolation', label: '被排斥', emoji: '🏝️', category: '边缘化', en: 'isolation', scripture: '加4:16' },
  { value: 'hunger', label: '灵里贫乏', emoji: '😣', category: '灵性贫穷', en: 'hunger', scripture: '太5:3' },
]

// 负向情绪 — 哀恸痛悔类 + 灵性黑夜类
const negativeEmotionsSad = [
  { value: 'sadness', label: '悲伤哀痛', emoji: '😢', category: '哀恸', en: 'sadness', scripture: '太5:4' },
  { value: 'sorrow', label: '忧伤痛悔', emoji: '😞', category: '神所要的痛悔', en: 'sorrow', scripture: '诗51:17' },
  { value: 'grief', label: '哀哭之夜', emoji: '😭', category: '深夜哀哭', en: 'grief', scripture: '诗30:5' },
  { value: 'anguish', label: '心灵剧痛', emoji: '💔', category: '极其难过', en: 'anguish', scripture: '罗9:2' },
  { value: 'despair', label: '灵性黑夜', emoji: '🌑', category: '绝望', en: 'despair', scripture: '伯3:20' },
  { value: 'hopelessness', label: '失去盼望', emoji: '⚫', category: '绝望', en: 'hopelessness', scripture: '箴13:12' },
]

// 负向情绪 — 虚空类 + 懊悔类 + 良心控告类
const negativeEmotionsLoss = [
  { value: 'loss', label: '失落虚空', emoji: '📉', category: '失去确据', en: 'loss', scripture: '传1:2' },
  { value: 'emptiness', label: '灵里空洞', emoji: '🕳️', category: '空虚', en: 'emptiness', scripture: '耶2:13' },
  { value: 'regret', label: '后悔错过', emoji: '😔', category: '后悔', en: 'regret', scripture: '太27:3' },
  { value: 'remorse', label: '痛悔认罪', emoji: '😖', category: '懊悔', en: 'remorse', scripture: '林后7:10' },
  { value: 'self_condemnation', label: '良心自责', emoji: '💢', category: '良心控告', en: 'self-condemnation', scripture: '约壹3:20' },
]

// 负向情绪 — 罪的羞耻类 + 不被定罪类
const negativeEmotionsShame = [
  { value: 'shame', label: '羞耻遮盖', emoji: '🔴', category: '罪的羞耻', en: 'shame', scripture: '创3:7' },
  { value: 'embarrassment', label: '当众蒙羞', emoji: '😳', category: '羞辱', en: 'embarrassment', scripture: '来12:2' },
  { value: 'guilt', label: '罪疚控告', emoji: '⛓️', category: '定罪', en: 'guilt', scripture: '罗8:1' },
]

// 负向情绪 — 敬畏战兢类 + 小信挂虑类
const negativeEmotionsFear = [
  { value: 'fear', label: '敬畏战兢', emoji: '😱', category: '敬畏', en: 'fear', scripture: '箴9:10' },
  { value: 'dread', label: '惧怕担忧', emoji: '😨', category: '惧怕', en: 'dread', scripture: '提后1:7' },
  { value: 'anxiety', label: '挂虑重担', emoji: '😰', category: '忧虑', en: 'anxiety', scripture: '腓4:6' },
  { value: 'worry', label: '小信担忧', emoji: '🤯', category: '小信', en: 'worry', scripture: '太6:30' },
  { value: 'nervousness', label: '战战兢兢', emoji: '😬', category: '谨慎', en: 'nervousness', scripture: '彼前3:15' },
  { value: 'panic', label: '惊慌失措', emoji: '😵', category: '惊慌', en: 'panic', scripture: '诗46:1-2' },
]

// 负向情绪 — 义怒恨罪类 + 老我争战类
const negativeEmotionsAnger = [
  { value: 'anger', label: '义怒', emoji: '😠', category: '正当愤怒', en: 'anger', scripture: '弗4:26' },
  { value: 'rage', label: '愤恨', emoji: '🤬', category: '愤恨', en: 'rage', scripture: '雅1:20' },
  { value: 'fury', label: '暴怒失控', emoji: '😡', category: '失控', en: 'fury', scripture: '箴14:17' },
  { value: 'irritation', label: '烦躁不平', emoji: '😤', category: '不耐烦', en: 'irritation', scripture: '箴14:29' },
  { value: 'impatience', label: '灵里急躁', emoji: '⏱️', category: '缺乏忍耐', en: 'impatience', scripture: '加5:22-23' },
]

// 负向情绪 — 恨罪忌邪类 + 嫉妒贪心类
const negativeEmotionsDisgust = [
  { value: 'disgust', label: '厌恶罪孽', emoji: '🤢', category: '恨恶罪', en: 'disgust', scripture: '诗97:10' },
  { value: 'contempt', label: '鄙视骄傲', emoji: '😒', category: '轻视', en: 'contempt', scripture: '箴18:12' },
  { value: 'jealousy', label: '嫉妒纷争', emoji: '😒', category: '嫉妒', en: 'jealousy', scripture: '加5:19-21' },
  { value: 'envy', label: '眼红羡慕', emoji: '👀', category: '贪心', en: 'envy', scripture: '来13:5' },
]

// 复杂/关系情绪 — 基督心肠类 + 明白神旨类 + 赦免释放类
const complexEmotionsCompassion = [
  { value: 'compassion', label: '基督心肠', emoji: '🧡', category: '怜悯心肠', en: 'compassion', scripture: '腓1:8' },
  { value: 'sympathy', label: '肢体同情', emoji: '🤝', category: '与哀哭同哭', en: 'sympathy', scripture: '罗12:15' },
  { value: 'empathy', label: '同理理解', emoji: '💜', category: '体恤软弱', en: 'empathy', scripture: '来4:15' },
  { value: 'comprehension', label: '明白神旨', emoji: '💡', category: '属灵领悟', en: 'comprehension', scripture: '弗1:18' },
  { value: 'forgiveness', label: '赦免释放', emoji: '🕊️', category: '饶恕释放', en: 'forgiveness', scripture: '太6:14' },
  { value: 'pardon', label: '白白饶恕', emoji: '✝️', category: '被赦免', en: 'pardon', scripture: '诗103:3' },
]

// 复杂/关系情绪 — 两灵交战类 + 灵性迷惘类 + 信心疑惑类 + 防备自守类 + 与神疏离类
const complexEmotionsAmbivalence = [
  { value: 'ambivalence', label: '两灵交战', emoji: '⚖️', category: '圣灵与情欲', en: 'ambivalence', scripture: '加5:17' },
  { value: 'confusion', label: '灵性迷惘', emoji: '🌫️', category: '迷路', en: 'confusion', scripture: '彼后3:16' },
  { value: 'uncertainty', label: '未知神旨', emoji: '❓', category: '不知前行', en: 'uncertainty', scripture: '箴3:5-6' },
  { value: 'doubt', label: '信心疑惑', emoji: '🤔', category: '小信', en: 'doubt', scripture: '太14:31' },
  { value: 'defensiveness', label: '设防自卫', emoji: '🛡️', category: '防备', en: 'defensiveness', scripture: '林后10:5' },
  { value: 'alienation', label: '与神疏离', emoji: '🧱', category: '与神隔绝', en: 'alienation', scripture: '西1:21' },
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
  const [renderError, setRenderError] = useState(null)
  const [activeTab, setActiveTab] = useState('new') // new, history, principles
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
        { key: 'personality', label: '人格塑造', emoji: '🔮' },
        { key: 'habits', label: '习惯养成', emoji: '🌱' },
        { key: 'behavior', label: '行为追踪', emoji: '📈' },
        { key: 'new', label: '决策支持', emoji: '⚖️' },
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
    {/* 原则模块 - 放在决策标题上方 */}
    <div style={{ padding: '16px', background: 'rgba(139,92,246,0.1)', borderRadius: '12px', marginBottom: '16px', border: '1px solid rgba(139,92,246,0.3)' }}>
      <div style={{ fontSize: '14px', fontWeight: 600, color: '#a78bfa', marginBottom: '8px' }}>
        📖 决策原则
      </div>
      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.7)', marginBottom: '12px' }}>
        在做出决策前默想这些原则，帮助辨识真伪
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {[
          { icon: '❤️', text: '爱 - 这个选择是否使我对神对人的爱更真实？' },
          { icon: '💡', text: '智慧 - 这是否符合圣经的智慧原则？' },
          { icon: '🔍', text: '诚实 - 我是否看清了真相，还是被偏见遮蔽？' },
          { icon: '🤝', text: '关系 - 这对我和他人的关系有何影响？' },
          { icon: '⏰', text: '时机 - 现在是采取行动的合适时机吗？' }
        ].map((principle, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: 'rgba(255,255,255,0.8)' }}>
            <span>{principle.icon}</span>
            <span>{principle.text}</span>
          </div>
        ))}
      </div>
    </div>
    
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

      {/* 提示信息 — 说明灵镜分析已包含属灵辨识 */}
      <div style={{
        padding: '12px 16px',
        borderRadius: '10px',
        background: 'rgba(79,172,254,0.08)',
        border: '1px solid rgba(79,172,254,0.2)',
        fontSize: '12px',
        color: 'rgba(255,255,255,0.6)',
        textAlign: 'center',
        lineHeight: 1.6,
      }}>
        � 点击上方「灵镜分析」按钮，系统将同时进行 MVFE 情绪分析并自动启动属灵辨识（需填写标题和类别）
      </div>
    </form>
    
    {/* 历史模块 - 放在页面最下方 */}
    {decisions.length > 0 && (
      <div style={{ padding: '16px' }}>
        <div style={{ 
          background: 'rgba(30,30,30,0.6)', 
          borderRadius: '12px', 
          padding: '16px',
          border: '1px solid rgba(255,255,255,0.1)'
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            marginBottom: '16px'
          }}>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>
              📜 历史决策
            </div>
            <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
              共 {decisions.length} 条记录
            </div>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {decisions.slice(0, 5).map((item, idx) => (
              <div 
                key={idx}
                onClick={() => loadHistoryItem(item)}
                style={{
                  padding: '12px',
                  background: 'rgba(255,255,255,0.05)',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  borderLeft: `3px solid ${item.status === 'completed' ? '#22c55e' : 
                                        item.status === 'archived' ? '#6b7280' : '#3b82f6'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '14px', color: '#fff', fontWeight: 500 }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.5)' }}>
                    {new Date(item.created_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.6)', marginTop: '4px' }}>
                  {item.category === 'career' && '💼 职业'}
                  {item.category === 'relationship' && '❤️ 关系'}
                  {item.category === 'finance' && '💰 财务'}
                  {item.category === 'health' && '🏥 健康'}
                  {item.category === 'education' && '📚 教育'}
                  {item.category === 'spiritual' && '⛪ 信仰'}
                  {item.category === 'other' && '📋 其他'}
                  {' · '}
                  {item.status === 'completed' && '✅ 已完成'}
                  {item.status === 'archived' && '📦 已归档'}
                  {item.status === 'analyzing' && '🔍 分析中'}
                </div>
              </div>
            ))}
          </div>
          
          {decisions.length > 5 && (
            <div style={{ 
              textAlign: 'center', 
              marginTop: '12px',
              fontSize: '12px',
              color: 'rgba(255,255,255,0.5)'
            }}>
              还有 {decisions.length - 5} 条记录...
            </div>
          )}
        </div>
      </div>
    )}
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
      {renderTabs()}
      
      {/* 用户个人标签 - 在 new tab 显示 */}
      {activeTab === 'new' && renderUserTags()}

      {/* 内容区域 */}
      <div style={{ paddingBottom: embedded ? '0' : '80px' }}>
        {activeTab === 'personality' && <PersonalityPage user={user} embedded={true} />}
        {activeTab === 'habits' && <HabitsPage user={user} token={getToken()} embedded={true} />}
        {activeTab === 'behavior' && <BehaviorPage user={user} embedded={true} />}
        {activeTab !== 'personality' && activeTab !== 'habits' && activeTab !== 'behavior' && (
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
