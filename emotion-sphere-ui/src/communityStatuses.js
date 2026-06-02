// communityStatuses.js — 个人状态库：发帖时从中选择当前属灵/心情/生活状态
export const COMMUNITY_STATUS_GROUPS = [
  { group: '信仰', items: [
    { key: 'grateful',         emoji: '🙏', label: '感恩' },
    { key: 'touched',          emoji: '✨', label: '被神触摸' },
    { key: 'thirsty-for-god',  emoji: '🔥', label: '渴慕神' },
    { key: 'need-prayer',      emoji: '🕊', label: '软弱·求代祷' },
    { key: 'waiting',          emoji: '⏳', label: '在等候中' },
    { key: 'new-believer',     emoji: '🌱', label: '刚信主' },
    { key: 'experienced-god',  emoji: '🌟', label: '经历神' },
    { key: 'dry',              emoji: '🏜', label: '灵里干渴' },
  ]},
  { group: '心情', items: [
    { key: 'joyful',   emoji: '😊', label: '喜乐' },
    { key: 'peaceful', emoji: '😌', label: '平安' },
    { key: 'hopeful',  emoji: '🌈', label: '满有盼望' },
    { key: 'calm',     emoji: '🌊', label: '平静' },
    { key: 'anxious',  emoji: '😟', label: '焦虑' },
    { key: 'sad',      emoji: '😢', label: '忧伤' },
    { key: 'lonely',   emoji: '🌧', label: '孤独' },
    { key: 'tired',    emoji: '😮‍💨', label: '疲惫' },
  ]},
  { group: '生活', items: [
    { key: 'new-start',      emoji: '🌅', label: '新的开始' },
    { key: 'busy',          emoji: '😅', label: '忙碌中' },
    { key: 'sick',          emoji: '🤒', label: '病中·求祷告' },
    { key: 'family-blessed', emoji: '🏡', label: '家庭蒙福' },
    { key: 'work-stress',   emoji: '💼', label: '工作压力' },
    { key: 'studying',      emoji: '📚', label: '考试/学习' },
    { key: 'traveling',     emoji: '🧳', label: '旅途中' },
    { key: 'celebrating',   emoji: '🎉', label: '庆祝感恩' },
  ]},
]

export const COMMUNITY_STATUS_BY_KEY = Object.fromEntries(
  COMMUNITY_STATUS_GROUPS.flatMap(g => g.items.map(it => [it.key, it])),
)
