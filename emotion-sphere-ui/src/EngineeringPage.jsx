import { useEffect, useMemo, useState } from 'react'
import { fetchRetrievalEvaluation } from './api'

function Metric({ label, value, tone = 'default' }) {
  const color = tone === 'good' ? '#34c759' : tone === 'warn' ? '#ff9f0a' : '#64d2ff'
  return (
    <div style={{
      minWidth: 0,
      padding: '14px',
      borderRadius: '12px',
      background: 'rgba(255,255,255,0.055)',
      border: '1px solid rgba(255,255,255,0.09)',
    }}>
      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.48)', marginBottom: '8px' }}>{label}</div>
      <div style={{ fontSize: '24px', fontWeight: 750, color }}>{value}</div>
    </div>
  )
}

function formatRate(value) {
  if (typeof value !== 'number') return '暂无'
  return `${Math.round(value * 100)}%`
}

export default function EngineeringPage({ onBack }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchRetrievalEvaluation()
      .then((payload) => {
        if (!cancelled) setData(payload)
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || String(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const summary = data?.latest_report?.summary || null
  const cases = data?.latest_report?.cases || []
  const weakCases = useMemo(() => cases.filter((item) => !item.hit || item.avoid_hit).slice(0, 8), [cases])
  const themes = Object.entries(data?.gold_set?.themes || {})

  return (
    <div style={{
      minHeight: '100%',
      width: '100%',
      background: '#0d0d14',
      color: 'rgba(255,255,255,0.92)',
      overflowY: 'auto',
      padding: '18px 16px 88px',
      boxSizing: 'border-box',
    }}>
      <div style={{ maxWidth: '960px', margin: '0 auto' }}>
        <header style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '18px' }}>
          <button
            type="button"
            onClick={onBack}
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              border: '1px solid rgba(255,255,255,0.12)',
              background: 'rgba(255,255,255,0.07)',
              color: 'white',
              cursor: 'pointer',
            }}
          >
            ←
          </button>
          <div>
            <h1 style={{ margin: 0, fontSize: '22px', letterSpacing: 0 }}>工程评测</h1>
            <div style={{ color: 'rgba(255,255,255,0.52)', fontSize: '13px', marginTop: '4px' }}>
              检索质量、gold set 覆盖和数据产物可追踪性
            </div>
          </div>
        </header>

        {loading && <div style={{ color: 'rgba(255,255,255,0.55)' }}>加载评测状态…</div>}
        {error && <div style={{ color: '#ff6961', padding: '14px', background: 'rgba(255,59,48,0.12)', borderRadius: '12px' }}>{error}</div>}

        {data && (
          <>
            <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginBottom: '14px' }}>
              <Metric label="Gold set cases" value={data.gold_set?.case_count ?? 0} />
              <Metric label="Hit rate @K" value={formatRate(summary?.hit_rate_at_k)} tone={summary?.hit_rate_at_k >= 0.7 ? 'good' : 'warn'} />
              <Metric label="MRR @K" value={typeof summary?.mrr_at_k === 'number' ? summary.mrr_at_k.toFixed(2) : '暂无'} />
              <Metric label="Avoid hit rate" value={formatRate(summary?.avoid_rate_at_k)} tone={summary?.avoid_rate_at_k === 0 ? 'good' : 'warn'} />
            </section>

            <section style={{ padding: '16px', borderRadius: '14px', background: 'rgba(255,255,255,0.045)', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '14px' }}>
              <h2 style={{ margin: '0 0 12px', fontSize: '15px' }}>主题覆盖</h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {themes.map(([theme, count]) => (
                  <span key={theme} style={{ fontSize: '12px', padding: '6px 10px', borderRadius: '999px', background: 'rgba(100,210,255,0.1)', border: '1px solid rgba(100,210,255,0.18)', color: '#9cdcfe' }}>
                    {theme} · {count}
                  </span>
                ))}
              </div>
            </section>

            <section style={{ padding: '16px', borderRadius: '14px', background: 'rgba(255,255,255,0.045)', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '14px' }}>
              <h2 style={{ margin: '0 0 12px', fontSize: '15px' }}>需要改进的样例</h2>
              {weakCases.length === 0 ? (
                <div style={{ color: 'rgba(255,255,255,0.52)', fontSize: '13px' }}>
                  当前没有最新评测失败样例。运行 pipeline evaluate 后这里会显示弱项。
                </div>
              ) : (
                <div style={{ display: 'grid', gap: '8px' }}>
                  {weakCases.map((item) => (
                    <div key={item.case_id} style={{ padding: '10px 12px', borderRadius: '10px', background: 'rgba(0,0,0,0.22)', border: '1px solid rgba(255,255,255,0.07)' }}>
                      <div style={{ fontSize: '13px', fontWeight: 650 }}>{item.case_id}</div>
                      <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.54)', marginTop: '4px' }}>
                        hit: {String(item.hit)} · avoid: {String(item.avoid_hit)} · first rank: {item.first_expected_rank ?? 'none'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section style={{ padding: '16px', borderRadius: '14px', background: 'rgba(255,255,255,0.045)', border: '1px solid rgba(255,255,255,0.08)' }}>
              <h2 style={{ margin: '0 0 12px', fontSize: '15px' }}>产物追踪</h2>
              <div style={{ color: 'rgba(255,255,255,0.58)', fontSize: '12px', marginBottom: '10px' }}>
                manifest: {data.manifest?.available ? data.manifest.generated_at : '未生成'} · artifacts: {data.manifest?.artifact_count || 0}
              </div>
              <div style={{ display: 'grid', gap: '8px' }}>
                {(data.manifest?.artifacts || []).map((artifact) => (
                  <div key={artifact.path} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', alignItems: 'center', padding: '10px 12px', borderRadius: '10px', background: 'rgba(0,0,0,0.22)', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{artifact.path}</div>
                      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.45)', marginTop: '4px' }}>{artifact.sha256?.slice(0, 16)}…</div>
                    </div>
                    <div style={{ fontSize: '12px', color: 'rgba(255,255,255,0.58)' }}>{Math.round((artifact.bytes || 0) / 1024)} KB</div>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
