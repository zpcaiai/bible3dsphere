/**
 * PlanetHome — 属灵星球 · 成长地图（IA v1，增量、不删现有功能）
 * 把愿景的五大陆作为「人格塑造路径」的导航，路由到已有功能。
 * 作为今日心镜 overlay 渲染，故可直接用 go() 跳到其它 overlay。
 */
const CONTINENTS = [
  {
    icon: '🧭', name: '认识自己', en: 'Self Discovery', color: '#da77f2',
    q: '我为什么软弱、焦虑、重复跌倒？',
    by: '钟马田 · 看见真实的自己',
    chips: [['偶像监测', 'idolatry'], ['低潮体检', 'checkup'], ['今日省察', 'examen']],
  },
  {
    icon: '✝️', name: '回到福音', en: 'Gospel Center', color: '#ffd43b',
    q: '我的伤口，福音如何回应？',
    by: '从情绪挖到不信，再挖回基督',
    chips: [['福音诊断室', 'gospel'], ['决策辨识', 'discern'], ['属灵牧者对话', 'agent']],
  },
  {
    icon: '🌅', name: '与神同行', en: 'Walk With God', color: '#34c759',
    q: '今天如何亲近基督？',
    by: '司布真 · 看见荣耀的基督',
    chips: [['灵修操练', 'hub'], ['养料库', 'fuel']],
    note: '清晨甘露 · 读经计划 · 背经，都在底部「灵修」里',
  },
  {
    icon: '🕯️', name: '等候上帝', en: 'Waiting for God', color: '#5ac8fa',
    q: '我在等什么？神在等待中塑造我什么？',
    by: '从等待戈多，到等候上帝',
    chips: [['等候之路', 'waiting']],
  },
  {
    icon: '🗺️', name: '天路客', en: 'Pilgrim Journey', color: '#51cf66',
    q: '此刻，我走在天路历程的哪一处？',
    by: '本仁《天路历程》· 据你的状态定位',
    chips: [['进入天路历程', 'pilgrim']],
  },
  {
    icon: '✦', name: '人格塑造', en: 'Formation', color: '#a78bfa',
    q: '我今天，更像耶稣了吗？',
    by: '信 · 望 · 爱 · 谦卑 · 顺服',
    chips: [['信望爱星系', 'fhl'], ['本周牧养小结', '_close'], ['八维概览', '_close']],
  },
]

export default function PlanetHome({ onClose, go }) {
  const act = (target) => { if (target === '_close') onClose(); else go(target) }
  return (
    <div style={{ width: '100%', height: '100%', background: 'radial-gradient(circle at 50% 12%, rgba(139,92,246,0.18), #05060c 60%)', color: '#fff', overflowY: 'auto', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12, position: 'sticky', top: 0, zIndex: 100, background: 'rgba(5,6,12,0.7)', backdropFilter: 'blur(10px)' }}>
        <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: '50%', width: 36, height: 36, color: '#fff', fontSize: 20, cursor: 'pointer' }}>‹</button>
        <div><div style={{ fontSize: 17, fontWeight: 600 }}>属灵星球</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)' }}>你不是在课程里学习，而是在一颗星球上成长</div></div>
      </div>

      <div style={{ textAlign: 'center', padding: '8px 16px 16px' }}>
        <div style={{ fontSize: 46 }}>🪐</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.6)', lineHeight: 1.7, maxWidth: 420, margin: '6px auto 0' }}>
          状态 → 识别 → 引导 → 行动 → 复盘 → 人格形成。<br />一条把你塑造得越来越像基督的成长路径。
        </div>
      </div>

      <div style={{ padding: '0 16px 110px', maxWidth: 640, margin: '0 auto' }}>
        {CONTINENTS.map((c, i) => (
          <div key={i} onClick={() => act(c.chips[0][1])} style={{ cursor: 'pointer', marginBottom: 14, borderRadius: 18, padding: 18, background: `linear-gradient(135deg, ${c.color}22, rgba(255,255,255,0.02))`, border: `1px solid ${c.color}44` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 30 }}>{c.icon}</span>
              <div>
                <div style={{ fontSize: 17, fontWeight: 700 }}>{c.name}</div>
                <div style={{ fontSize: 10.5, color: c.color, letterSpacing: 1 }}>{c.en} · {c.by}</div>
              </div>
            </div>
            <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.82)', lineHeight: 1.6, fontStyle: 'italic', marginBottom: 12 }}>「{c.q}」</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {c.chips.map(([label, target], j) => (
                <button key={j} onClick={(e) => { e.stopPropagation(); act(target) }} style={{ padding: '7px 14px', borderRadius: 18, border: 'none', cursor: 'pointer', fontSize: 12.5, fontWeight: 700, background: `${c.color}28`, color: c.color }}>{label} ›</button>
              ))}
            </div>
            {c.note && <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.4)', marginTop: 10 }}>{c.note}</div>}
          </div>
        ))}
        <div style={{ fontSize: 10.5, color: 'rgba(255,255,255,0.3)', textAlign: 'center', lineHeight: 1.7, marginTop: 4 }}>
          内容只是燃料，养料库随你的状态被自动调用。<br />愿你在这颗星球上，越来越有信、有望、有爱，越来越像祂。
        </div>
      </div>
    </div>
  )
}
