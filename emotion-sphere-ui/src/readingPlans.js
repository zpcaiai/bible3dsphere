// 读经计划定义（内容在前端，进度在后端）
// kind: 'date' 用 MM-DD 取 mccheyne.json；'seq' 用顺序天 d001..
const psalms30 = [1, 23, 27, 34, 37, 42, 46, 51, 63, 73, 84, 90, 91, 100, 103,
  104, 116, 119, 121, 126, 130, 131, 133, 136, 139, 143, 145, 146, 147, 150]

export const PLANS = [
  {
    id: 'mccheyne', name: '麦琴读经', subtitle: '每天 4 处经文 · 一年通读全本圣经',
    kind: 'date', length: 365, color: '#34c759',
  },
  {
    id: 'john21', name: '约翰福音 · 21 天', subtitle: '每天一章 · 认识那位道成肉身的主',
    kind: 'seq', length: 21, color: '#5ac8fa',
    days: Array.from({ length: 21 }, (_, i) => ({ refs: [`约翰福音 ${i + 1}`] })),
  },
  {
    id: 'psalms30', name: '诗篇 · 30 天', subtitle: '每天一篇 · 与神倾心吐意',
    kind: 'seq', length: 30, color: '#a78bfa',
    days: psalms30.map(n => ({ refs: [`诗篇 ${n}`] })),
  },
]

export function planById(id) { return PLANS.find(p => p.id === id) }

// 今天的 MM-DD（Asia/Shanghai 近似：用本地，足够日常使用）
export function todayMMDD() {
  const d = new Date()
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}-${dd}`
}

// 顺序计划下一天 key（首个未完成）
export function seqDayKey(idx) { return 'd' + String(idx + 1).padStart(3, '0') }
