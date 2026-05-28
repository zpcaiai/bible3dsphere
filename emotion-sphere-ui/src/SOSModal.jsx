import { useState } from 'react'

const DARK_MOMENT_CHARACTERS = [
  {
    name: '以利亚', ref: '列王纪上 19:4',
    situation: '在旷野求死：「耶和华啊，罢了！求你取我的性命。」',
    how_god_met: '神没有指责他，而是让天使两次摸他、喂他食物，说「起来吃吧，你当走的路甚远」。',
    hope: '神在你最崩溃的时候，第一个动作是：照顾你的身体，然后差你继续上路。',
  },
  {
    name: '约伯', ref: '约伯记 3:3',
    situation: '「愿我生的那日和说怀了男胎的那夜都灭没」——诅咒自己出生的那天。',
    how_god_met: '神在最后出现了，不是给答案，而是带约伯看宇宙的宏大，让他知道：有一位神比苦难更大。',
    hope: '你可以在神面前诚实地说出最黑暗的感受，祂能承受，祂没有离开。',
  },
  {
    name: '耶利米', ref: '耶利米书 20:14',
    situation: '「愿我生的那日被咒诅」——先知书写中最黑暗的一章。',
    how_god_met: '神对他说「我知道我向你们所怀的意念，是赐平安的意念」（29:11），黑暗之中，计划未改。',
    hope: '神对耶利米没有放弃——即使在最深的黑暗里，神对你的计划也没有改变。',
  },
]

const SOS_KEYWORDS = ['绝望', '放弃', '活不下去', '不想活', '失去信仰', '看不见神', '神在哪里', '抛弃']

export function checkSOSKeywords(text) {
  if (!text) return false
  return SOS_KEYWORDS.some(kw => text.includes(kw))
}

export default function SOSModal({ onClose, onPrayerWall }) {
  const [expanded, setExpanded] = useState(null)

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 500,
      background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'flex-end', justifyContent: 'center',
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{
        width: '100%', maxWidth: 560, maxHeight: '85vh', overflow: 'auto',
        background: 'linear-gradient(180deg, #0f0f1e, #0a0a14)',
        border: '1px solid rgba(88,86,214,0.3)', borderRadius: '20px 20px 0 0',
        padding: '24px 20px 40px',
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div style={{ fontSize: 36, marginBottom: 10 }}>🕯️</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#fff', marginBottom: 6 }}>
            你不是一个人
          </div>
          <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.55)', lineHeight: 1.7 }}>
            就在黑暗中，神的眼目仍在看顾你。<br />
            在圣经里，许多神所爱的人也走过这样的时刻。
          </div>
        </div>

        {/* Characters */}
        <div style={{ marginBottom: 20 }}>
          {DARK_MOMENT_CHARACTERS.map((char, i) => (
            <div key={i} style={{
              background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12, padding: '14px', marginBottom: 10, cursor: 'pointer',
            }} onClick={() => setExpanded(expanded === i ? null : i)}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#e0d4ff' }}>{char.name}</div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{char.ref}</div>
                </div>
                <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>{expanded === i ? '▲' : '▼'}</span>
              </div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.6)', marginTop: 8, lineHeight: 1.6, fontStyle: 'italic' }}>
                {char.situation}
              </div>
              {expanded === i && (
                <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.7)', lineHeight: 1.65, marginBottom: 8 }}>
                    <span style={{ color: '#5ac8fa', fontWeight: 600 }}>神的回应：</span> {char.how_god_met}
                  </div>
                  <div style={{ fontSize: 12, color: '#ffd700', lineHeight: 1.65, fontStyle: 'italic', background: 'rgba(255,215,0,0.07)', padding: '8px 10px', borderRadius: 8 }}>
                    💛 {char.hope}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Key verse */}
        <div style={{ background: 'rgba(88,86,214,0.1)', border: '1px solid rgba(88,86,214,0.25)', borderRadius: 12, padding: '16px', marginBottom: 20, textAlign: 'center' }}>
          <div style={{ fontSize: 14, color: '#fff', lineHeight: 1.8, fontStyle: 'italic', marginBottom: 8 }}>
            「你们要将一切的忧虑卸给神，<br />因为他顾念你们。」
          </div>
          <div style={{ fontSize: 12, color: '#c4b5fd' }}>彼得前书 5:7</div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {onPrayerWall && (
            <button onClick={onPrayerWall} style={{ padding: '12px', background: 'rgba(0,122,255,0.2)', border: '1px solid rgba(0,122,255,0.4)', borderRadius: 12, color: '#5eb0ff', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
              🙏 在代祷墙上提出来，让弟兄姐妹同心代祷
            </button>
          )}
          <button onClick={onClose} style={{ padding: '12px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 12, color: 'rgba(255,255,255,0.6)', fontSize: 13, cursor: 'pointer' }}>
            我明白了，继续
          </button>
        </div>
      </div>
    </div>
  )
}
