import { useEffect, useMemo, useState } from 'react'
import { fetchBiblicalExample, fetchFeatureDetail, fetchGuidance, fetchHistory, fetchLayout, fetchStats, runQuery, trackStats } from './api'
import { isIosInstallable, promptInstall, subscribeToInstallPrompt } from './pwa'
import { useEmotionStore } from './store'
import { EmotionSphereScene } from './EmotionSphereScene'

const VISITOR_ID_KEY = 'bible-sphere-visitor-id'

function getOrCreateVisitorId() {
  const existingId = window.localStorage.getItem(VISITOR_ID_KEY)
  if (existingId) {
    return existingId
  }

  const visitorId = typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `visitor-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

  window.localStorage.setItem(VISITOR_ID_KEY, visitorId)
  return visitorId
}

function verseGroupsFromResult(result, languageFilter) {
  if (!result?.verse_summary) return []
  const langs = languageFilter === 'both' ? ['cuv', 'esv'] : [languageFilter]
  return langs.map((language) => ({ language, items: result.verse_summary[language] || [] }))
}

function buildComparisonRows(result) {
  if (!result?.verse_summary) return []

  const cuvMap = new Map((result.verse_summary.cuv || []).map((item) => [item.pk_id, item]))
  const esvMap = new Map((result.verse_summary.esv || []).map((item) => [item.pk_id, item]))
  const orderedIds = []

  for (const item of result.verse_summary.cuv || []) {
    if (item.pk_id && !orderedIds.includes(item.pk_id)) {
      orderedIds.push(item.pk_id)
    }
  }

  for (const item of result.verse_summary.esv || []) {
    if (item.pk_id && !orderedIds.includes(item.pk_id)) {
      orderedIds.push(item.pk_id)
    }
  }

  return orderedIds.map((pkId) => {
    let cuv = cuvMap.get(pkId) || null
    let esv = esvMap.get(pkId) || null
    // Fill missing side from the other's counterpart (backend lookup)
    if (cuv && !esv && cuv.counterpart) esv = cuv.counterpart
    if (esv && !cuv && esv.counterpart) cuv = esv.counterpart
    return { pk_id: pkId, cuv, esv }
  })
}

export default function App() {
  const {
    layoutItems,
    historyItems,
    selectedFeature,
    selectedFeatureDetail,
    queryResult,
    languageFilter,
    topFeatures,
    topVerses,
    zoomLevel,
    loading,
    error,
    setLayoutItems,
    setHistoryItems,
    setSelectedFeature,
    setSelectedFeatureDetail,
    setQueryResult,
    setLanguageFilter,
    setTopFeatures,
    setTopVerses,
    setLoading,
    setError,
  } = useEmotionStore()

  const [query, setQuery] = useState('我感到很痛苦，也很想被安慰，但仍然想抓住一点盼望')
  const [includeGuidance, setIncludeGuidance] = useState(false)
  const [enableRerank, setEnableRerank] = useState(false)
  const [rerankCandidates, setRerankCandidates] = useState(20)
  const [rerankWeight, setRerankWeight] = useState(0.7)
  const [guidance, setGuidance] = useState(null)
  const [biblicalExample, setBiblicalExample] = useState(null)
  const [includeBiblicalExample, setIncludeBiblicalExample] = useState(false)
  const [comparisonMode, setComparisonMode] = useState(true)
  const [canInstall, setCanInstall] = useState(false)
  const [installMessage, setInstallMessage] = useState('')
  const [showIosInstallHint, setShowIosInstallHint] = useState(false)
  const [visitStats, setVisitStats] = useState({ page_views: 0, unique_visitors: 0 })

  useEffect(() => {
    fetchLayout().then((data) => setLayoutItems(data.items || [])).catch((err) => setError(String(err)))
    fetchHistory().then((data) => setHistoryItems(data.items || [])).catch(() => {})
  }, [setLayoutItems, setHistoryItems, setError])

  useEffect(() => {
    let cancelled = false

    async function loadVisitStats() {
      try {
        const visitorId = getOrCreateVisitorId()
        const stats = await trackStats(visitorId)
        if (!cancelled) {
          setVisitStats(stats)
        }
      } catch {
        try {
          const stats = await fetchStats()
          if (!cancelled) {
            setVisitStats(stats)
          }
        } catch {
        }
      }
    }

    loadVisitStats()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const unsubscribe = subscribeToInstallPrompt((available) => {
      setCanInstall(available)
    })
    setShowIosInstallHint(isIosInstallable())
    return unsubscribe
  }, [])

  const clusters = useMemo(() => {
    const map = new Map()
    for (const item of layoutItems) {
      const key = (item.source_keyword || 'emotion').toLowerCase()
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(item)
    }
    return [...map.entries()].slice(0, 6)
  }, [layoutItems])

  const verseGroups = useMemo(() => verseGroupsFromResult(queryResult, languageFilter), [queryResult, languageFilter])
  const comparisonRows = useMemo(() => buildComparisonRows(queryResult), [queryResult])

  async function doQuery() {
    setLoading(true)
    setError('')
    setInstallMessage('')
    setGuidance(null)
    setBiblicalExample(null)
    try {
      const result = await runQuery({
        query,
        topFeatures,
        topVerses,
        languageFilter,
        enableRerank,
        rerankCandidates,
        rerankWeight,
      })
      setQueryResult(result)
      setLoading(false)
      fetchHistory().then((h) => setHistoryItems(h.items || [])).catch(() => {})
      // guidance and biblical example run in background after results are already shown
      if (includeGuidance) {
        fetchGuidance(query).then(setGuidance).catch(() => {})
      }
      if (includeBiblicalExample) {
        fetchBiblicalExample(query).then(setBiblicalExample).catch(() => {})
      }
    } catch (err) {
      setError(String(err.message || err))
      setLoading(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    await doQuery()
  }

  async function handleInstallApp() {
    const installed = await promptInstall()
    setCanInstall(false)
    setInstallMessage(installed ? '已触发安装，你可以将应用添加到主屏幕。' : '当前浏览器没有弹出安装确认，可使用浏览器菜单手动添加到主屏幕。')
  }

  async function handleVerseTrigger(feature) {
    setSelectedFeature(feature)
    try {
      const detail = await fetchFeatureDetail(feature.feature_key)
      setSelectedFeatureDetail(detail)
      if (!detail?.matches) return
      setQueryResult({
        query_text: feature.explanation,
        selected_emotions: [feature],
        verse_summary: detail.matches,
        query_latency_ms: null,
      })
    } catch (err) {
      setError(String(err.message || err))
    }

  }

    return (
      <div className="mobile-app-shell">
        <header className="mobile-topbar glass">
          <div>
            <div className="eyebrow">Bible Emotion Sphere</div>
            <h1 className="mobile-app-title">情感星球</h1>
          </div>
        </header>
        <div className="mobile-summary-card glass">
          <div className="section-title">情绪簇</div>
          <div style={{display: 'flex', gap: '12px', alignItems: 'center'}}>
            <div className="mobile-topbar-status">
              <span className="topbar-pill">{layoutItems.length || 0} emotions</span>
            </div>
            <div className="mobile-summary-card glass" style={{flex: 1}}>
              <span className="topbar-stats">
                <span className="topbar-stats-icon">👁</span>
                {visitStats.page_views}
              </span>
            </div>
          </div>
          {/*  <div className="mobile-cluster-preview">
            {clusters.map(([name, items]) => (
                <span key={name} className="cluster-pill">{name} · {items.length}</span>
            ))}
          </div>  */}

        </div>

        <section className="mobile-hero-card glass">
          <div className="mobile-hero-meta">
            <div className="meta-chip">{zoomLevel === 'far' ? '远景' : zoomLevel === 'mid' ? '中景' : '近景'}</div>
            <div
                    className="meta-chip">{queryResult?.query_latency_ms != null ? `${queryResult.query_latency_ms} ms` : ''}</div>
              <div className="meta-chip">{selectedFeature?.zh_label || ''}</div>
            </div>
          </section>
        <main className="mobile-app-main" style={{display: 'block'}}>
          <section className="mobile-pane mobile-sphere-pane" style={{display: 'flex'}}>
            <div className="mobile-sphere-stage">
              <EmotionSphereScene onVerseTrigger={handleVerseTrigger} />
            </div>

            <div className="mobile-summary-grid">
              <div className="mobile-summary-card glass accent-card">
                <div className="section-title"></div>
                <div className="feature-name">{selectedFeature?.zh_label || ''}</div>
                <div className="muted">{selectedFeature?.explanation || ''}</div>
              </div>
            </div>
          </section>

          <section className="mobile-pane" style={{display: 'block'}}>
            <div className="mobile-card-stack">
              <section className="mobile-card glass">
                <div className="section-title"></div>
                <form className="query-form" onSubmit={handleSubmit}>
                  <label>
                    <span></span>
                    <textarea value={query} onChange={(e) => setQuery(e.target.value)} />
                  </label>

                  <div className="form-grid">
                    <label>
                      <span>关联情绪节点</span>
                      <input type="number" min="1" max="10" value={topFeatures} onChange={(e) => setTopFeatures(Number(e.target.value))} readOnly />
                    </label>
                    <label>
                      <span>返回经文</span>
                      <input type="number" min="1" max="10" value={topVerses} onChange={(e) => setTopVerses(Number(e.target.value))} readOnly />
                    </label>
                  </div>

                  <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start'}}>
                    <div className="segmented-control mobile-language-switch" style={{flex: 1}}>
                      {[
                        ['cuv', '和合本'],
                        ['esv', 'ESV'],
                      ].map(([value, label]) => (
                        <button
                          type="button"
                          key={value}
                          className={languageFilter === value ? 'segment active' : 'segment'}
                          onClick={() => setLanguageFilter(value)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>

                  </div>

                  <div style={{display: 'flex', gap: '12px', alignItems: 'flex-start', flexWrap: 'wrap'}}>
                    <label className="guidance-toggle" style={{flex: 1}}>
                      <input
                        type="checkbox"
                        checked={includeGuidance}
                        onChange={(e) => setIncludeGuidance(e.target.checked)}
                      />
                      <span>心理状态评估</span>
                    </label>
                    <label className="guidance-toggle" style={{flex: 1}}>
                      <input
                        type="checkbox"
                        checked={includeBiblicalExample}
                        onChange={(e) => setIncludeBiblicalExample(e.target.checked)}
                      />
                      <span>圣经榜样案例</span>
                    </label>
                    <label className="guidance-toggle" style={{flex: 1}}>
                      <input
                        type="checkbox"
                        checked={enableRerank}
                        onChange={(e) => setEnableRerank(e.target.checked)}
                      />
                      <span>启用Rerank精排</span>
                    </label>
                  </div>

                  {enableRerank ? (
                    <div className="form-grid">
                      <label>
                        <span>候选经文</span>
                        <input type="number" min="1" max="10" value={rerankCandidates} onChange={(e) => setRerankCandidates(Number(e.target.value))} readOnly />
                      </label>
                      <label>
                        <span>精排权重</span>
                        <input type="number" min="0" max="1" step="0.1" value={rerankWeight} onChange={(e) => setRerankWeight(Number(e.target.value))} readOnly />
                      </label>
                    </div>
                  ) : <div className="muted" style={{marginTop: 4, fontSize: '12px'}}></div>}

                  <button className="primary-btn mobile-submit-btn" type="submit" disabled={loading}>
                    {loading ? '检索中...' : '检索经文'}
                  </button>
                </form>
              </section>
              <section className="mobile-pane" style={{display: 'block'}}>
                <div className="segmented-control view-mode-toggle" style={{flex: '0 0 auto'}}>
                  <button
                      type="button"
                      className={comparisonMode ? 'segment active' : 'segment'}
                      onClick={() => setComparisonMode(true)}
                  >
                    中英对照
                  </button>
                  <button
                      type="button"
                      className={!comparisonMode ? 'segment active' : 'segment'}
                      onClick={() => setComparisonMode(false)}
                  >
                    分语言
                  </button>
                </div>
              </section>

            </div>
          </section>

          <section className="mobile-pane" style={{display: 'block', marginTop: '20px'}}>
            <div className="mobile-card-stack">
              {biblicalExample && (
                <section className="mobile-card detail-section guidance-section">
                  <div className="section-title">📖 圣经榜样案例</div>
                  <div style={{display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px'}}>
                    <span className="emotion-tag" style={{fontSize: '15px', fontWeight: 700}}>{biblicalExample.person}</span>
                    {biblicalExample.era && <span className="muted" style={{fontSize: '12px'}}>{biblicalExample.era}</span>}
                  </div>
                  {biblicalExample.similar_situation && (
                    <div className="guidance-block">
                      <div className="guidance-label">相似处境</div>
                      <p>{biblicalExample.similar_situation}</p>
                    </div>
                  )}
                  {biblicalExample.biblical_response && (
                    <div className="guidance-block">
                      <div className="guidance-label">信仰回应</div>
                      <p>{biblicalExample.biblical_response}</p>
                    </div>
                  )}
                  {biblicalExample.key_verse && (
                    <div className="guidance-block spiritual">
                      <div className="guidance-label">关键经文</div>
                      <p style={{fontStyle: 'italic'}}>{biblicalExample.key_verse}</p>
                    </div>
                  )}
                  {biblicalExample.application && (
                    <div className="guidance-core-need">
                      <strong>{biblicalExample.application}</strong>
                    </div>
                  )}
                </section>
              )}

              {guidance && (
                  <section className="mobile-card detail-section guidance-section">
                    <div className="section-title">心理状态评估 · 灵性指引</div>
                    {guidance.core_emotions?.length > 0 && (
                        <div className="guidance-emotions">
                          {guidance.core_emotions.map((e) => (
                              <span key={e} className="emotion-tag">{e}</span>
                          ))}
                        </div>
                    )}
                    {guidance.psychological_assessment && (
                        <div className="guidance-block">
                          <div className="guidance-label">心理评估</div>
                          <p>{guidance.psychological_assessment}</p>
                        </div>
                    )}
                    {guidance.coping_suggestions?.length > 0 && (
                        <div className="guidance-block">
                          <div className="guidance-label">应对建议</div>
                          <ul className="guidance-tips">
                            {guidance.coping_suggestions.map((s, i) => (
                                <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </div>
                    )}
                    {guidance.spiritual_guidance && (
                        <div className="guidance-block spiritual">
                          <div className="guidance-label">灵性指引</div>
                          <p>{guidance.spiritual_guidance}</p>
                        </div>
                    )}
                    {guidance.core_need && (
                        <div className="guidance-core-need">
                          <strong>{guidance.core_need}</strong>
                        </div>
                    )}
                  </section>
              )}

              <section className="mobile-card glass detail-section">
                <div className="section-title"></div>
                {selectedFeature ? (
                    <>
                      <div className="feature-name">
                        {selectedFeature.zh_label || `${selectedFeature.layer}:${selectedFeature.feature_id}`}
                      </div>
                      <div className="feature-copy">{selectedFeature.explanation}</div>
                      {selectedFeatureDetail && (
                          <div className="feature-meta">
                            <div>keyword: {selectedFeatureDetail.source_keyword}</div>
                            <div>和合本 matches: {(selectedFeatureDetail.matches?.cuv || []).length}</div>
                                </div>
                      )}
                    </>
                ) : (
                    <div className="muted"></div>
                )}
              </section>

              <section className="mobile-card glass detail-section">
                <div className="section-title">经文结果</div>
                {queryResult?.rerank?.enabled && queryResult?.rerank?.error && (
                    <div className="rerank-warning">
                      ⚠️ Rerank 降级：{queryResult.rerank.error}
                    </div>
                )}
                {queryResult ? (
                    comparisonMode && languageFilter === 'both' ? (
                        <div className="comparison-list">
                          {comparisonRows.filter((row) => row.cuv || row.esv).map((row) => (
                              <div key={row.pk_id} className="comparison-card glass-subtle">
                                <div className="comparison-stacked">
                                  {row.cuv && (
                                      <div className="comparison-entry">
                                        <div className="comparison-label">
                                          和合本{row.cuv.from_lookup && <span className="lookup-badge">关联</span>}
                                        </div>
                                        <div
                                            className="verse-ref-ui">{row.cuv.book_name} {row.cuv.chapter}:{row.cuv.verse}</div>
                                        <div className="verse-text-ui">{row.cuv.raw_text}</div>
                                        {row.cuv.rerank_score != null && (
                                            <div className="verse-score-row">
                                              <span className="score-pill rerank">rerank {row.cuv.rerank_score}</span>
                                              <span className="score-pill final">final {row.cuv.final_score}</span>
                                            </div>
                                        )}
                                      </div>
                                  )}
                                </div>
                              </div>
                          ))}
                        </div>
                    ) : (
                        verseGroups.map((group) => (
                            <div key={group.language} className="verse-group">
                              {group.items.map((item) => (
                                  <div key={item.pk_id} className="verse-card-ui glass-subtle">
                                    <div className="verse-ref-ui">{item.book_name} {item.chapter}:{item.verse}</div>
                                    <div className="verse-text-ui">{item.raw_text}</div>
                                    {item.rerank_score != null && (
                                        <div className="verse-score-row">
                                          <span className="score-pill rerank">rerank {item.rerank_score}</span>
                                          <span className="score-pill final">final {item.final_score}</span>
                                        </div>
                                    )}
                                  </div>
                              ))}
                            </div>
                        ))
                    )
                ) : (
                    <div className="muted"></div>
                )}
              </section>

              {error ? <div className="error-box">{error}</div> : null}

              <section className="mobile-card glass">
                <div className="section-title">历史记录</div>
                <div className="history-list">
                  {historyItems.slice(0, 12).map((item, idx) => (
                      <button
                          key={`${item.query_text}-${idx}`}
                          className="history-item"
                          onClick={() => {
                            setQuery(item.query_text)
                          }}
                      >
                        <span>{item.query_text}</span>
                      </button>
                  ))}
                </div>
              </section>

              {/*   <section className="mobile-card glass">
                <div className="section-title">球体状态</div>
                <div className="meta-card-inline">
                  <div className="meta-title">LOD</div>
                  <div className="meta-value">{zoomLevel === 'far' ? '远景：显示簇' : zoomLevel === 'mid' ? '中景：显示部分标签' : '近景：显示具体点与标签'}</div>
                </div>
                <div className="meta-card-inline">
                  <div className="meta-title">Latency</div>
                  <div className="meta-value">{queryResult?.query_latency_ms != null ? `${queryResult.query_latency_ms} ms` : '等待查询'}</div>
                </div>
              </section> */}
              <section className="mobile-card glass">
                <div className="section-title">安装到手机</div>
                <div className="muted">将当前页面添加到主屏幕，获得更接近原生 App 的体验。</div>
                {canInstall ? (
                    <button className="primary-btn install-btn" type="button" onClick={handleInstallApp}>Install
                      App</button>
                ) : null}
                {!canInstall && showIosInstallHint ? (
                    <div className="install-hint">iPhone 请在 Safari 中点击"分享" → "添加到主屏幕"。</div>
                ) : null}
                {installMessage ? <div className="install-hint">{installMessage}</div> : null}
                <div className="quick-action-list">
                  <button className="segment active" type="button"
                          onClick={() => window.scrollTo({top: 0, behavior: 'smooth'})}>返回顶部
                  </button>
                </div>
              </section>
              <section className="mobile-card glass stats-gradient">
                <div className="section-title">📊 访问统计</div>
                <div className="stats-cards">
                  <div className="stats-card">
                    <div className="stats-pulse"></div>
                    <div className="stats-icon">👁</div>
                    <div className="stats-value">{visitStats.page_views.toLocaleString()}</div>
                    <div className="stats-label">总浏览量</div>
                  </div>
                  <div className="stats-card">
                    <div className="stats-icon">👤</div>
                    <div className="stats-value">{visitStats.unique_visitors.toLocaleString()}</div>
                    <div className="stats-label">独立访客</div>
                  </div>
                </div>
                <div className="muted" style={{fontSize: '11px', marginTop: '10px', textAlign: 'center'}}>
                  实时统计 · 持久化存储
                </div>
              </section>
            </div>
          </section>
        </main>
      </div>
    )
}
