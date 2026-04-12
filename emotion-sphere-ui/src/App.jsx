import { useEffect, useMemo, useState } from 'react'
import { fetchFeatureDetail, fetchGuidance, fetchHistory, fetchLayout, fetchStats, runQuery, trackStats } from './api'
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

  return orderedIds.map((pkId) => ({
    pk_id: pkId,
    cuv: cuvMap.get(pkId) || null,
    esv: esvMap.get(pkId) || null,
  }))
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
  const [comparisonMode, setComparisonMode] = useState(true)
  const [canInstall, setCanInstall] = useState(false)
  const [installMessage, setInstallMessage] = useState('')
  const [showIosInstallHint, setShowIosInstallHint] = useState(false)
  const [activeTab, setActiveTab] = useState('explore')
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
      // guidance runs in background after results are already shown
      if (includeGuidance) {
        fetchGuidance(query).then(setGuidance).catch(() => {})
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
    setActiveTab('library')
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

    const tabItems = [
      ['explore', '◉', '球体 / 检索'],
      ['library', '✦', '结果 / 历史'],
    ]

    return (
      <div className="mobile-app-shell">
        <header className="mobile-topbar glass">
          <div>
            <div className="eyebrow">Bible Emotion Sphere</div>
            <h1 className="mobile-app-title">情绪经文球体</h1>
          </div>
          <div className="mobile-topbar-status">
            <span className="topbar-pill">{layoutItems.length || 0} emotions</span>
            <span className="topbar-pill">{visitStats.page_views} 浏览</span>
          </div>
        </header>

        {activeTab === 'explore' ? (
          <section className="mobile-hero-card glass">
            <div className="mobile-hero-copy">
              <div className="section-title">3D Emotion Sphere</div>
              <p>点击球体上的情绪词或圆点，直接联动经文与灵性指引。</p>
            </div>
            <div className="mobile-hero-meta">
              <div className="meta-chip">{zoomLevel === 'far' ? '远景' : zoomLevel === 'mid' ? '中景' : '近景'}</div>
              <div className="meta-chip">{queryResult?.query_latency_ms != null ? `${queryResult.query_latency_ms} ms` : '待查询'}</div>
              <div className="meta-chip">{selectedFeature?.zh_label || '未选中情绪'}</div>
              <div className="meta-chip">访客 {visitStats.unique_visitors}</div>
            </div>
            <div className="hero-action-row">
              <button className="hero-action-btn primary" type="button" onClick={async () => { setActiveTab('library'); await doQuery() }}>
                {loading ? '检索中...' : '开始检索'}
              </button>
              <button className="hero-action-btn" type="button" onClick={() => setActiveTab('library')}>
                查看结果
              </button>
            </div>
          </section>
        ) : null}

        <main className="mobile-app-main">
          <section className={`mobile-pane mobile-sphere-pane ${activeTab === 'explore' ? 'active' : ''}`}>

            <div className="mobile-sphere-stage">
              <EmotionSphereScene onVerseTrigger={handleVerseTrigger} />
            </div>

            <div className="mobile-summary-grid">
              <div className="mobile-summary-card glass">
                <div className="section-title">Rerank</div>
                <div className="meta-value">
                  {queryResult?.rerank?.applied
                    ? `已启用 · 候选 ${queryResult.rerank.candidate_pool_per_language} · 权重 ${queryResult.rerank.weight}`
                    : queryResult?.rerank?.enabled && queryResult?.rerank?.error
                    ? '启用失败 (已降级)'
                    : '未启用'}
                </div>
                {queryResult?.rerank?.model && (
                  <div className="muted" style={{ fontSize: '10px', marginTop: 4, wordBreak: 'break-all' }}>{queryResult.rerank.model}</div>
                )}
              </div>
              <div className="mobile-summary-card glass">
                <div className="section-title">情绪簇</div>
                <div className="mobile-cluster-preview">
                  {clusters.map(([name, items]) => (
                    <span key={name} className="cluster-pill">{name} · {items.length}</span>
                  ))}
                </div>
              </div>
              <div className="mobile-summary-card glass">
                <div className="section-title">访问统计</div>
                <div className="meta-value">浏览量 {visitStats.page_views}</div>
                <div className="muted">独立访客 {visitStats.unique_visitors}</div>
              </div>
              <div className="mobile-summary-card glass accent-card">
                <div className="section-title">当前焦点</div>
                <div className="feature-name">{selectedFeature?.zh_label || '点击球体选择情绪'}</div>
                <div className="muted">{selectedFeature?.explanation || '选择某个情绪后，这里会显示对应说明。'}</div>
              </div>
            </div>

            <div className="mobile-card-stack">
              <section className="mobile-card glass">
                <div className="section-title">情绪检索</div>
                <form className="query-form" onSubmit={handleSubmit}>
                  <label>
                    <span>自然语言情绪输入</span>
                    <textarea value={query} onChange={(e) => setQuery(e.target.value)} />
                  </label>

                  <div className="form-grid">
                    <label>
                      <span>关联情绪节点</span>
                      <input type="number" min="1" max="12" value={topFeatures} onChange={(e) => setTopFeatures(Number(e.target.value))} />
                    </label>
                    <label>
                      <span>返回经文</span>
                      <input type="number" min="1" max="10" value={topVerses} onChange={(e) => setTopVerses(Number(e.target.value))} />
                    </label>
                  </div>

                  <div className="segmented-control mobile-language-switch">
                    {[
                      ['both', '中英双语'],
                      ['cuv', '只看 和合本'],
                      ['esv', '只看 ESV'],
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

                  <label className="guidance-toggle">
                    <input
                      type="checkbox"
                      checked={includeGuidance}
                      onChange={(e) => setIncludeGuidance(e.target.checked)}
                    />
                    <span>生成心理状态评估 + 灵性指引</span>
                  </label>

                  <label className="guidance-toggle">
                    <input
                      type="checkbox"
                      checked={enableRerank}
                      onChange={(e) => setEnableRerank(e.target.checked)}
                    />
                    <span>启用轻量 Rerank 精排</span>
                  </label>

                  {enableRerank ? (
                    <div className="form-grid">
                      <label>
                        <span>Rerank Candidates</span>
                        <input type="number" min="5" max="100" value={rerankCandidates} onChange={(e) => setRerankCandidates(Number(e.target.value))} />
                      </label>
                      <label>
                        <span>Rerank Weight</span>
                        <input type="number" min="0" max="1" step="0.1" value={rerankWeight} onChange={(e) => setRerankWeight(Number(e.target.value))} />
                      </label>
                    </div>
                  ) : null}

                  <button className="primary-btn mobile-submit-btn" type="submit" disabled={loading}>
                    {loading ? '检索中...' : '检索经文'}
                  </button>
                </form>
              </section>

              <section className="mobile-card glass">
                <div className="section-title">安装到手机</div>
                <div className="muted">将当前页面添加到主屏幕，获得更接近原生 App 的体验。</div>
                {canInstall ? (
                  <button className="primary-btn install-btn" type="button" onClick={handleInstallApp}>Install App</button>
                ) : null}
                {!canInstall && showIosInstallHint ? (
                  <div className="install-hint">iPhone 请在 Safari 中点击“分享” → “添加到主屏幕”。</div>
                ) : null}
                {installMessage ? <div className="install-hint">{installMessage}</div> : null}
                <div className="quick-action-list">
                  <button className="quick-action-btn" type="button" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>返回顶部</button>
                  <button className="quick-action-btn" type="button" onClick={() => setActiveTab('library')}>查看结果 / 历史</button>
                </div>
              </section>
            </div>
          </section>

          <section className={`mobile-pane ${activeTab === 'library' ? 'active' : ''}`}>
            <div className="mobile-card-stack">
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
                <div className="section-title">选中情绪点</div>
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
                        <div>ESV matches: {(selectedFeatureDetail.matches?.esv || []).length}</div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="muted">点击球体上的情绪点查看详情。</div>
                )}
              </section>

              <section className="mobile-card glass detail-section">
                <div className="section-title">经文结果</div>
                <div className="segmented-control view-mode-toggle">
                  <button
                    type="button"
                    className={comparisonMode ? 'segment active' : 'segment'}
                    onClick={() => setComparisonMode(true)}
                  >
                    对照模式
                  </button>
                  <button
                    type="button"
                    className={!comparisonMode ? 'segment active' : 'segment'}
                    onClick={() => setComparisonMode(false)}
                  >
                    分语言模式
                  </button>
                </div>
                {queryResult ? (
                  comparisonMode && languageFilter === 'both' ? (
                    <div className="comparison-list">
                      {comparisonRows.map((row) => (
                        <div key={row.pk_id} className="comparison-card glass-subtle">
                          <div className="comparison-stacked">
                            <div className="comparison-entry">
                              <div className="comparison-label">和合本</div>
                              {row.cuv ? (
                                <>
                                  <div className="verse-ref-ui">{row.cuv.book_name} {row.cuv.chapter}:{row.cuv.verse}</div>
                                  <div className="verse-text-ui">{row.cuv.raw_text}</div>
                                </>
                              ) : (
                                <div className="muted">没有匹配到对应中文经文。</div>
                              )}
                            </div>
                            <div className="comparison-entry comparison-entry-esv">
                              <div className="comparison-label">ESV</div>
                              {row.esv ? (
                                <>
                                  <div className="verse-ref-ui">{row.esv.book_name} {row.esv.chapter}:{row.esv.verse}</div>
                                  <div className="verse-text-ui">{row.esv.raw_text}</div>
                                </>
                              ) : (
                                <div className="muted">没有匹配到对应英文经文。</div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    verseGroups.map((group) => (
                      <div key={group.language} className="verse-group">
                        <h3>{group.language === 'cuv' ? '和合本' : 'ESV'}</h3>
                        {group.items.map((item) => (
                          <div key={item.pk_id} className="verse-card-ui glass-subtle">
                            <div className="verse-ref-ui">{item.book_name} {item.chapter}:{item.verse}</div>
                            <div className="verse-text-ui">{item.raw_text}</div>
                            {item.counterpart ? (
                              <div className="verse-counterpart">
                                <div className="counterpart-label">{group.language === 'cuv' ? 'ESV' : '和合本'}</div>
                                <div className="verse-ref-ui">{item.counterpart.book_name} {item.counterpart.chapter}:{item.counterpart.verse}</div>
                                <div className="verse-text-ui">{item.counterpart.raw_text}</div>
                              </div>
                            ) : null}
                          </div>
                        ))}
                      </div>
                    ))
                  )
                ) : (
                  <div className="muted">先输入自然语言并检索，或点击情绪点后在此处查看相关结果。</div>
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
                        setActiveTab('explore')
                      }}
                    >
                      <span>{item.query_text}</span>
                    </button>
                  ))}
                </div>
              </section>

              <section className="mobile-card glass">
                <div className="section-title">球体状态</div>
                <div className="meta-card-inline">
                  <div className="meta-title">LOD</div>
                  <div className="meta-value">{zoomLevel === 'far' ? '远景：显示簇' : zoomLevel === 'mid' ? '中景：显示部分标签' : '近景：显示具体点与标签'}</div>
                </div>
                <div className="meta-card-inline">
                  <div className="meta-title">Latency</div>
                  <div className="meta-value">{queryResult?.query_latency_ms != null ? `${queryResult.query_latency_ms} ms` : '等待查询'}</div>
                </div>
              </section>
            </div>
          </section>
        </main>

        <nav className="mobile-bottom-nav glass">
          {tabItems.map(([value, icon, label]) => (
            <button
              key={value}
              type="button"
              className={activeTab === value ? 'mobile-nav-item active' : 'mobile-nav-item'}
              onClick={() => setActiveTab(value)}
            >
              <span className="mobile-nav-icon">{icon}</span>
              <span className="mobile-nav-label">{label}</span>
            </button>
          ))}
        </nav>
      </div>
    )
  }
