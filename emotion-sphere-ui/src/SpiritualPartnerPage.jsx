import { useEffect, useState } from 'react'
import { fetchPartnerStatus, requestPartner, respondPartner, sendEncouragement, fetchSpiritualHealthCheck } from './api'

const ENCOURAGEMENT_VERSES = [
  { ref: '腓立比书 4:13', text: '我靠着那加给我力量的，凡事都能做。' },
  { ref: '以赛亚书 40:31', text: '但那等候耶和华的，必重新得力，他们必如鹰展翅上腾。' },
  { ref: '诗篇 23:1', text: '耶和华是我的牧者，我必不至缺乏。' },
  { ref: '罗马书 8:28', text: '万事都互相效力，叫爱神的人得益处。' },
]

export default function SpiritualPartnerPage({ user, token, onBack }) {
  const [partnerData, setPartnerData] = useState(null)
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [partnerEmail, setPartnerEmail] = useState('')
  const [requesting, setRequesting] = useState(false)
  const [requestSent, setRequestSent] = useState(false)
  const [error, setError] = useState('')
  const [encourageSent, setEncourageSent] = useState(false)

  useEffect(() => {
    if (!user) return
    Promise.all([
      fetchPartnerStatus(token),
      fetchSpiritualHealthCheck(token),
    ]).then(([pd, hd]) => {
      setPartnerData(pd)
      setHealthData(hd)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [user, token])

  async function handleRequest() {
    if (!partnerEmail.trim() || requesting) return
    setRequesting(true)
    setError('')
    try {
      await requestPartner(partnerEmail.trim(), token)
      setRequestSent(true)
    } catch (e) {
      setError(e.message)
    } finally {
      setRequesting(false)
    }
  }

  async function handleRespond(requester, accept) {
    try {
      await respondPartner(requester, accept, token)
      const pd = await fetchPartnerStatus(token)
      setPartnerData(pd)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleEncourage() {
    await sendEncouragement(token)
    setEncourageSent(true)
    setTimeout(() => setEncourageSent(false), 3000)
  }

  const partner = partnerData?.partner
  const pending = partnerData?.pending || []
  const inboundRequests = pending.filter(p => p.partner === user?.email && p.status === 'pending')

  return (
    <div className="pw-page">
      <header className="pw-header">
        <button className="checkin-back-btn" onClick={onBack} aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div className="pw-header-center">
          <div className="pw-title">🤝 属灵伙伴</div>
          <div className="pw-subtitle">同行者让灵命更持久</div>
        </div>
      </header>

      <div style={{ padding: '20px 16px', maxWidth: 560, margin: '0 auto' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
        ) : (
          <>
            {/* A3: 倒退预警横幅 */}
            {healthData?.alert_level && (
              <div style={{
                background: healthData.alert_level === 'gentle' ? 'rgba(0,122,255,0.1)' : 'rgba(255,149,0,0.1)',
                border: `1px solid ${healthData.alert_level === 'gentle' ? 'rgba(0,122,255,0.3)' : 'rgba(255,149,0,0.3)'}`,
                borderRadius: 14, padding: '18px', marginBottom: 20,
              }}>
                <div style={{ fontSize: 14, color: '#fff', fontWeight: 600, marginBottom: 8 }}>
                  {healthData.alert_level === 'gentle' ? '💌 神记念你' : '🕯️ 神看顾你'}
                </div>
                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.8)', lineHeight: 1.7, marginBottom: 12 }}>
                  {healthData.message}
                </div>
                {healthData.verse && (
                  <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.55)', fontStyle: 'italic', borderLeft: '2px solid rgba(0,122,255,0.4)', paddingLeft: 10, lineHeight: 1.6 }}>
                    {healthData.verse}
                  </div>
                )}
              </div>
            )}

            {/* Active partner card */}
            {partner ? (
              <div style={{ background: 'linear-gradient(135deg, rgba(52,199,89,0.1), rgba(0,122,255,0.08))', border: '1px solid rgba(52,199,89,0.25)', borderRadius: 16, padding: '20px', marginBottom: 20 }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)', marginBottom: 12, fontWeight: 600, letterSpacing: '0.05em' }}>你的属灵伙伴</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 16 }}>
                  <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'linear-gradient(135deg,#5856d6,#007aff)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 700, color: '#fff' }}>
                    {(partner.nickname || '?')[0].toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>{partner.nickname}</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>{partner.email}</div>
                  </div>
                </div>
                {/* Partner devotion status */}
                <div style={{ padding: '12px', background: 'rgba(255,255,255,0.05)', borderRadius: 10, marginBottom: 14 }}>
                  {partner.has_devotion_today ? (
                    <div style={{ fontSize: 13, color: '#34c759' }}>✅ 今天已灵修</div>
                  ) : partner.last_devotion_days_ago !== null ? (
                    <div style={{ fontSize: 13, color: partner.last_devotion_days_ago >= 3 ? '#ff9f40' : 'rgba(255,255,255,0.6)' }}>
                      {partner.last_devotion_days_ago === 0 ? '今天已灵修' : `${partner.last_devotion_days_ago} 天前最近一次灵修`}
                      {partner.last_devotion_days_ago >= 3 && ' · 可以为他/她代祷'}
                    </div>
                  ) : (
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.4)' }}>暂无灵修记录</div>
                  )}
                </div>
                {/* Encouragement button */}
                <button
                  onClick={handleEncourage}
                  style={{
                    width: '100%', padding: '11px', background: encourageSent ? 'rgba(52,199,89,0.2)' : 'rgba(0,122,255,0.2)',
                    border: `1px solid ${encourageSent ? 'rgba(52,199,89,0.4)' : 'rgba(0,122,255,0.4)'}`,
                    borderRadius: 10, color: encourageSent ? '#34c759' : '#5eb0ff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  {encourageSent ? '✅ 鼓励已发送！' : '📖 发送一句经文鼓励'}
                </button>
                {encourageSent && (
                  <div style={{ marginTop: 10, textAlign: 'center' }}>
                    {(() => {
                      const v = ENCOURAGEMENT_VERSES[Math.floor(Math.random() * ENCOURAGEMENT_VERSES.length)]
                      return <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.5)', fontStyle: 'italic' }}>「{v.text}」— {v.ref}</div>
                    })()}
                  </div>
                )}
              </div>
            ) : null}

            {/* Inbound requests */}
            {inboundRequests.map((req, i) => (
              <div key={i} style={{ background: 'rgba(255,215,0,0.08)', border: '1px solid rgba(255,215,0,0.3)', borderRadius: 14, padding: '16px', marginBottom: 16 }}>
                <div style={{ fontSize: 13, color: '#ffd700', marginBottom: 10 }}>🤝 收到属灵伙伴邀请</div>
                <div style={{ fontSize: 14, color: '#fff', marginBottom: 14 }}>{req.requester} 邀请你成为属灵伙伴</div>
                <div style={{ display: 'flex', gap: 10 }}>
                  <button onClick={() => handleRespond(req.requester, true)} style={{ flex: 1, padding: '9px', background: 'rgba(52,199,89,0.2)', border: '1px solid rgba(52,199,89,0.4)', borderRadius: 8, color: '#34c759', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>接受</button>
                  <button onClick={() => handleRespond(req.requester, false)} style={{ flex: 1, padding: '9px', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, color: 'rgba(255,255,255,0.5)', fontSize: 13, cursor: 'pointer' }}>暂不</button>
                </div>
              </div>
            ))}

            {/* Request new partner */}
            {!partner && (
              <div style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 14, padding: '20px' }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#fff', marginBottom: 6 }}>邀请属灵伙伴</div>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginBottom: 16, lineHeight: 1.6 }}>
                  有人同行，灵命习惯坚持率高4倍。你们只互相看见打卡状态，内容完全私密。
                </div>
                {requestSent ? (
                  <div style={{ textAlign: 'center', padding: '16px', color: '#34c759', fontSize: 14 }}>
                    ✅ 邀请已发送！等待对方接受
                  </div>
                ) : (
                  <>
                    <input
                      value={partnerEmail}
                      onChange={e => setPartnerEmail(e.target.value)}
                      placeholder="输入对方的注册邮箱"
                      style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.08)', color: '#fff', fontSize: 14, outline: 'none', boxSizing: 'border-box', marginBottom: 10 }}
                    />
                    {error && <div style={{ color: '#ff3b30', fontSize: 12, marginBottom: 8 }}>{error}</div>}
                    <button
                      onClick={handleRequest}
                      disabled={!partnerEmail.trim() || requesting}
                      style={{ width: '100%', padding: '10px', background: 'rgba(88,86,214,0.3)', border: '1px solid rgba(88,86,214,0.5)', borderRadius: 8, color: '#c4b5fd', fontSize: 14, fontWeight: 600, cursor: 'pointer' }}
                    >
                      {requesting ? '发送中...' : '🤝 发出邀请'}
                    </button>
                  </>
                )}
              </div>
            )}

            {/* About section */}
            <div style={{ marginTop: 24, padding: '14px 16px', background: 'rgba(255,255,255,0.03)', borderRadius: 10, fontSize: 12, color: 'rgba(255,255,255,0.35)', lineHeight: 1.7 }}>
              「二人同心，所做的事比一人更好...因为一人跌倒，另一人可以扶起他的同伴。」— 传道书 4:9-10
            </div>
          </>
        )}
      </div>
    </div>
  )
}
