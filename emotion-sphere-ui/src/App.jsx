import { useEffect, useMemo, useState } from 'react'
import { fetchBiblicalExample, fetchFeatureDetail, fetchGuidance, fetchHistory, fetchLayout, fetchSermon, fetchStats, runQuery, trackStats } from './api'
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
  const [includeGuidance, setIncludeGuidance] = useState(true)
  const [rerankMode, setRerankMode] = useState('llm')
  const [rerankCandidates, setRerankCandidates] = useState(20)
  const [rerankWeight, setRerankWeight] = useState(0.3)
  const [guidance, setGuidance] = useState(null)
  const [biblicalExample, setBiblicalExample] = useState(null)
  const [sermon, setSermon] = useState(null)
  const [sermonLoading, setSermonLoading] = useState(false)
  const [includeBiblicalExample, setIncludeBiblicalExample] = useState(true)
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
        enableRerank: rerankMode !== 'none',
        rerankCandidates,
        rerankWeight,
        rerankMode,
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
    setGuidance(null)
    setBiblicalExample(null)
    try {
      const detail = await fetchFeatureDetail(feature.feature_key)
      setSelectedFeatureDetail(detail)
      if (!detail?.matches) return
      const { esv: _esv, ...cuvOnly } = detail.matches
      setQueryResult({
        query_text: feature.explanation,
        selected_emotions: [feature],
        verse_summary: cuvOnly,
        query_latency_ms: null,
      })
      const q = feature.zh_label || feature.explanation
      fetchGuidance(q).then(setGuidance).catch(() => {})
      fetchBiblicalExample(q).then(setBiblicalExample).catch(() => {})
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
            <div className="mobile-summary-card glass" style={{display: 'inline-flex', width: 'fit-content'}}>
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
                      <span>关联情绪</span>
                      <input type="number" min="1" max="10" value={topFeatures} onChange={(e) => setTopFeatures(Number(e.target.value))} readOnly />
                    </label>
                    <label>
                      <span>祂的话</span>
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


                  <button className="primary-btn mobile-submit-btn" type="submit" disabled={loading}>
                    {loading ? '沉思中...' : '心灵花园'}
                  </button>
                  <button
                    className="sermon-btn mobile-submit-btn"
                    type="button"
                    disabled={sermonLoading || !query.trim()}
                    onClick={() => {
                      setSermon(null)
                      setSermonLoading(true)
                      fetchSermon(query).then(s => { setSermon(s); setSermonLoading(false) }).catch(() => setSermonLoading(false))
                    }}
                  >
                    {sermonLoading ? '沉思中...' : '对你讲道'}
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

              {sermon && (
                <section className="result-unified-card mobile-card guidance-section sermon-card">
                  <div className="sermon-title">{sermon.title}</div>
                  {sermon.theme_verse && (
                    <div className="result-spiritual-block" style={{marginBottom: '16px'}}>
                      <p style={{margin: 0, fontStyle: 'italic'}}>{sermon.theme_verse}</p>
                    </div>
                  )}

                  {sermon.introduction && (
                    <div className="result-block">
                      <div className="result-block-title">引言</div>
                      <p className="result-body-text">{sermon.introduction}</p>
                    </div>
                  )}

                  {sermon.sections?.map((sec, i) => (
                    <div key={i} className="result-block">
                      <div className="result-divider" />
                      <div className="sermon-section-heading">{sec.heading}</div>
                      <p className="result-body-text">{sec.content}</p>
                      {sec.supporting_verse && (
                        <div className="result-spiritual-block">
                          <p style={{margin: 0, fontStyle: 'italic', fontSize: '12px'}}>{sec.supporting_verse}</p>
                        </div>
                      )}
                    </div>
                  ))}

                  {sermon.spiritual_diagnosis && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">属灵剖析</div>
                      <p className="result-body-text">{sermon.spiritual_diagnosis}</p>
                    </div>
                  )}

                  {sermon.historical_case && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">历史见证</div>
                      <div className="result-person-row">
                        <span className="result-person-name">{sermon.historical_case.person}</span>
                        {sermon.historical_case.era && <span className="result-person-era">{sermon.historical_case.era}</span>}
                      </div>
                      <p className="result-body-text">{sermon.historical_case.story}</p>
                      {sermon.historical_case.lesson && (
                        <div className="result-core-need">{sermon.historical_case.lesson}</div>
                      )}
                    </div>
                  )}

                  {sermon.application && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">属灵操练</div>
                      <p className="result-body-text" style={{whiteSpace: 'pre-line'}}>{Array.isArray(sermon.application) ? sermon.application.join('\n') : sermon.application}</p>
                    </div>
                  )}

                  {sermon.encouragement && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">勉励与安慰</div>
                      <p className="result-body-text">{sermon.encouragement}</p>
                    </div>
                  )}

                  {sermon.prayer && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">祝祷</div>
                      <div className="result-spiritual-block">
                        <p style={{margin: 0, whiteSpace: 'pre-line'}}>{sermon.prayer}</p>
                      </div>
                    </div>
                  )}

                  {sermon.conclusion && (
                    <div className="result-block">
                      <div className="result-divider" />
                      <div className="result-block-title">结语与盼望</div>
                      <p className="result-body-text">{sermon.conclusion}</p>
                    </div>
                  )}
                </section>
              )}

              {(guidance || biblicalExample || queryResult) && (
                <section className="result-unified-card mobile-card guidance-section">

                  {/* ── 心理评估 ── */}
                  {guidance && (
                    <div className="result-block">
                      <div className="result-block-title">灵魂处境</div>
                      {guidance.core_emotions?.length > 0 && (
                        <div className="guidance-emotions">
                          {guidance.core_emotions.map((e) => (
                            <span key={e} className="emotion-tag">{e}</span>
                          ))}
                        </div>
                      )}
                      {guidance.psychological_assessment && (
                        <p className="result-body-text">{guidance.psychological_assessment}</p>
                      )}
                      {guidance.core_need && (
                        <div className="result-core-need">{guidance.core_need}</div>
                      )}
                      {guidance.coping_suggestions?.length > 0 && (
                        <ul className="guidance-tips">
                          {guidance.coping_suggestions.map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ul>
                      )}
                      {guidance.spiritual_guidance && (
                        <div className="result-spiritual-block">
                          <p>{guidance.spiritual_guidance}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {guidance && (biblicalExample || queryResult) && <div className="result-divider" />}

                  {/* ── 圣经榜样 ── */}
                  {biblicalExample && (
                    <div className="result-block">
                      <div className="result-block-title">圣经榜样</div>
                      <div className="result-person-row">
                        <span className="result-person-name">{biblicalExample.person}</span>
                        {biblicalExample.era && <span className="result-person-era">{biblicalExample.era}</span>}
                      </div>
                      {biblicalExample.similar_situation && (
                        <p className="result-body-text">{biblicalExample.similar_situation}</p>
                      )}
                      {biblicalExample.biblical_response && (
                        <p className="result-body-text">{biblicalExample.biblical_response}</p>
                      )}
                      {biblicalExample.key_verse && (
                        <div className="result-spiritual-block">
                          <p style={{fontStyle: 'italic', margin: 0}}>{biblicalExample.key_verse}</p>
                        </div>
                      )}
                      {biblicalExample.application && (
                        <div className="result-core-need">{biblicalExample.application}</div>
                      )}
                    </div>
                  )}

                  {biblicalExample && queryResult && <div className="result-divider" />}

                  {/* ── 经文结果 ── */}
                  {queryResult && (
                    <div className="result-block">
                      <div className="result-block-title">默想经文</div>
                      {selectedFeature && (
                        <div className="result-feature-pill">
                          {selectedFeature.zh_label || `${selectedFeature.layer}:${selectedFeature.feature_id}`}
                        </div>
                      )}
                      {queryResult.rerank?.enabled && queryResult.rerank?.error && (
                        <div className="rerank-warning">⚠️ Rerank 降级：{queryResult.rerank.error}</div>
                      )}
                      <div className="verse-list">
                        {verseGroups.flatMap((group) =>
                          group.items.map((item) => (
                            <div key={item.pk_id} className="verse-item">
                              <div className="verse-ref-ui">{item.book_name} {item.chapter}:{item.verse}</div>
                              <div className="verse-text-ui">{item.raw_text}</div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                </section>
              )}

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
