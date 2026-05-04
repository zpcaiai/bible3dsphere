import { useEffect, useMemo, useState } from 'react'
import jsPDF from 'jspdf'
import { fetchBiblicalExample, fetchFeatureDetail, fetchGuidance, fetchHistory, fetchLayout, fetchSermon, fetchStats, runQuery, trackStats } from './api'
import { fetchCurrentUser, getCachedUser, getToken, logout, setCachedUser } from './auth'
import { isIosInstallable, promptInstall, subscribeToInstallPrompt } from './pwa'
import { useEmotionStore } from './store'
import { EmotionSphereScene } from './EmotionSphereScene'
import LoginScreen from './LoginScreen'
import CheckInPage from './CheckInPage'
import ChatPage from './ChatPage'
import SermonJournalPage from './SermonJournalPage'
import PrayerWallPage from './PrayerWallPage'
import DevotionJournalPage from './DevotionJournalPage'

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

function useAuth() {
  const [user, setUser] = useState(() => getCachedUser())
  const [authLoading, setAuthLoading] = useState(true)

  useEffect(() => {
    fetchCurrentUser().then((u) => {
      setUser(u)
      setAuthLoading(false)
    })
  }, [])

  const handleLogout = async () => {
    await logout()
    setUser(null)
  }

  return { user, authLoading, setUser, handleLogout }
}

export default function App() {
  const { user, authLoading, handleLogout } = useAuth()

  const [showLogin, setShowLogin] = useState(false)

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
    setSphereGuidance,
    setSpheresBiblicalExample,
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
  const [activePanel, setActivePanel] = useState('sphere')
  const [gardenClickCount, setGardenClickCount] = useState(0)
  const [sermonClickCount, setSermonClickCount] = useState(0)
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
    setActivePanel('garden')
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
    setSphereGuidance(null)
    setSpheresBiblicalExample(null)
    try {
      const detail = await fetchFeatureDetail(feature.feature_key)
      setSelectedFeatureDetail(detail)
      const parts = [feature.explanation, feature.zh_label].filter(Boolean)
      const q = parts.join('，')
      fetchGuidance(q).then(setSphereGuidance).catch(() => {})
      fetchBiblicalExample(q).then(setSpheresBiblicalExample).catch(() => {})
    } catch (err) {
      setError(String(err.message || err))
    }
  }

  function exportVersesToTxt() {
    if (!queryResult?.verse_summary) return
    let content = `情感星球 - 默想经文\n`
    content += `查询：${query}\n`
    content += `日期：${new Date().toLocaleString('zh-CN')}\n\n`

    // 添加经文
    const groups = verseGroupsFromResult(queryResult, languageFilter)
    groups.forEach(group => {
      content += `【${group.language === 'cuv' ? '中文' : 'English'}】\n`
      group.items.forEach(item => {
        content += `${item.book_name} ${item.chapter}:${item.verse}\n${item.raw_text}\n\n`
      })
    })

    // 添加引导信息
    if (guidance) {
      content += `\n【引导信息】\n${guidance}\n\n`
    }

    // 添加圣经例子
    if (biblicalExample) {
      content += `\n【圣经例子】\n${biblicalExample}\n\n`
    }

    // 添加讲道内容
    if (sermon) {
      content += `\n【专属讲道：${sermon.title || ''}】\n\n`
      if (sermon.theme_verse) content += `主题经文：${sermon.theme_verse}\n\n`
      if (sermon.introduction) content += `引言：\n${sermon.introduction}\n\n`
      sermon.sections?.forEach((sec, i) => {
        content += `${sec.heading}\n${sec.content}\n\n`
      })
      if (sermon.spiritual_diagnosis) content += `属灵剖析：\n${sermon.spiritual_diagnosis}\n\n`
      if (sermon.application) content += `属灵操练：\n${sermon.application}\n\n`
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `默想经文_${new Date().toISOString().slice(0,10)}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  function exportVersesToPdf() {
    if (!queryResult?.verse_summary) return

    // Create HTML content for better Chinese support
    let htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; padding: 40px; line-height: 1.6; }
          h1 { font-size: 20px; color: #007aff; margin-bottom: 10px; }
          .meta { font-size: 12px; color: #666; margin-bottom: 20px; }
          .section { margin: 20px 0; }
          .section-title { font-size: 14px; font-weight: bold; color: #333; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
          .verse-item { margin: 12px 0; padding: 10px; background: #f8f9fa; border-radius: 6px; }
          .verse-ref { font-size: 11px; color: #007aff; font-weight: 600; }
          .verse-text { font-size: 13px; margin-top: 4px; }
          .guidance { background: #e8f4f8; padding: 12px; border-radius: 6px; margin: 12px 0; }
          .sermon { background: #fff8e8; padding: 12px; border-radius: 6px; margin: 12px 0; }
          .sermon-title { font-size: 16px; font-weight: bold; color: #5e5ce6; margin-bottom: 8px; }
        </style>
      </head>
      <body>
        <h1>情感星球 - 默想经文</h1>
        <div class="meta">查询：${query}<br>日期：${new Date().toLocaleString('zh-CN')}</div>
    `

    // 添加经文
    const groups = verseGroupsFromResult(queryResult, languageFilter)
    groups.forEach(group => {
      htmlContent += `<div class="section"><div class="section-title">${group.language === 'cuv' ? '中文' : 'English'}</div>`
      group.items.forEach(item => {
        htmlContent += `
          <div class="verse-item">
            <div class="verse-ref">${item.book_name} ${item.chapter}:${item.verse}</div>
            <div class="verse-text">${item.raw_text}</div>
          </div>
        `
      })
      htmlContent += `</div>`
    })

    // 添加引导信息
    if (guidance) {
      htmlContent += `<div class="section"><div class="section-title">引导信息</div><div class="guidance">${guidance.replace(/\n/g, '<br>')}</div></div>`
    }

    // 添加圣经例子
    if (biblicalExample) {
      htmlContent += `<div class="section"><div class="section-title">圣经例子</div><div class="guidance">${biblicalExample.replace(/\n/g, '<br>')}</div></div>`
    }

    // 添加讲道内容
    if (sermon) {
      htmlContent += `<div class="section sermon"><div class="sermon-title">专属讲道：${sermon.title || ''}</div>`
      if (sermon.theme_verse) htmlContent += `<div style="font-style:italic;margin-bottom:12px;">${sermon.theme_verse}</div>`
      if (sermon.introduction) htmlContent += `<p>${sermon.introduction.replace(/\n/g, '<br>')}</p>`
      sermon.sections?.forEach((sec) => {
        htmlContent += `<div style="margin:12px 0;"><strong>${sec.heading}</strong><p>${sec.content.replace(/\n/g, '<br>')}</p></div>`
      })
      if (sermon.spiritual_diagnosis) htmlContent += `<div style="margin-top:12px;"><strong>属灵剖析</strong><p>${sermon.spiritual_diagnosis.replace(/\n/g, '<br>')}</p></div>`
      if (sermon.application) htmlContent += `<div style="margin-top:12px;"><strong>属灵操练</strong><p>${sermon.application.replace(/\n/g, '<br>')}</p></div>`
      htmlContent += `</div>`
    }

    htmlContent += `</body></html>`

    // Open in new window for print to PDF
    const printWindow = window.open('', '_blank')
    printWindow.document.write(htmlContent)
    printWindow.document.close()

    // Auto print after images load
    setTimeout(() => {
      printWindow.print()
    }, 500)
  }

    if (showLogin) {
      return <LoginScreen onLogin={(u) => { setCachedUser(u); window.location.reload() }} onBack={() => setShowLogin(false)} />
    }

    return (
      <div className="mobile-app-shell">
        <header className="mobile-topbar">
          <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
            <span style={{fontSize: '22px', lineHeight: 1}}>🔮</span>
            <h1 className="mobile-app-title">情感星球</h1>
          </div>
          <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
            {layoutItems.length > 0 && (
              <span className="topbar-pill">{layoutItems.length} 情绪</span>
            )}
            {user ? (
              <div style={{display: 'flex', alignItems: 'center', gap: '6px'}}>
                {user.avatar ? (
                  <img
                    src={user.avatar}
                    alt={user.nickname || '用户'}
                    style={{
                      width: '28px', height: '28px', borderRadius: '50%',
                      objectFit: 'cover', border: '1.5px solid rgba(255,255,255,0.2)',
                      flexShrink: 0,
                    }}
                  />
                ) : (
                  <div style={{
                    width: '28px', height: '28px', borderRadius: '50%',
                    background: 'linear-gradient(135deg,#007aff,#5e5ce6)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '13px', fontWeight: 700, color: '#fff', flexShrink: 0,
                  }}>
                    {(user.nickname || '用')[0]}
                  </div>
                )}
                <span style={{fontSize: '13px', color: 'rgba(255,255,255,0.7)', maxWidth: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap'}}>
                  {user.nickname || '弟兄'}
                </span>
                <button
                  onClick={handleLogout}
                  style={{
                    background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)',
                    borderRadius: '7px', color: 'rgba(255,255,255,0.45)',
                    fontSize: '11px', padding: '3px 8px',
                    cursor: 'pointer', fontFamily: 'inherit',
                  }}
                >
                  退出
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowLogin(true)}
                style={{
                  background: 'linear-gradient(135deg,#007aff,#5e5ce6)',
                  border: 'none', borderRadius: '8px',
                  color: '#fff', fontSize: '13px', fontWeight: 600,
                  padding: '5px 14px', cursor: 'pointer', fontFamily: 'inherit',
                  boxShadow: '0 2px 8px rgba(0,122,255,0.3)',
                }}
              >
                登录
              </button>
            )}
          </div>
        </header>

        <section className="mobile-hero-card glass" style={{padding: '8px 14px', minHeight: 'unset'}}>
          <div className="mobile-hero-meta" style={{gap: '6px', flexWrap: 'wrap'}}>
            <div className="meta-chip">{zoomLevel === 'far' ? '🌌 远景' : zoomLevel === 'mid' ? '🔭 中景' : '🔬 近景'}</div>
            {queryResult?.query_latency_ms != null && (
              <div className="meta-chip">⚡ {queryResult.query_latency_ms} ms</div>
            )}
            {selectedFeature?.zh_label && (
              <div className="meta-chip" style={{background: 'rgba(0,122,255,0.18)', color: '#5eb0ff', borderColor: 'rgba(0,122,255,0.25)'}}>✨ {selectedFeature.zh_label}</div>
            )}
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
              </div>
            </div>
          </section>

          <section className="mobile-pane" style={{display: 'block'}}>
            <div className="mobile-card-stack">
              <section className="mobile-card glass">
                <div className="section-title" style={{display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px'}}>
                  <span>🙏</span><span>向神倾诉</span>
                </div>
                <form className="query-form" onSubmit={handleSubmit}>
                  <label>
                    <span style={{display: 'none'}}></span>
                    <textarea
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="说出你心中的处境、情绪或困惑…"
                      style={{minHeight: '80px'}}
                    />
                  </label>


                  <div style={{display: 'none'}}>
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


                  <div style={{display: 'flex', gap: '8px'}}>
                    <button
                      className="primary-btn mobile-submit-btn"
                      type="submit"
                      disabled={loading}
                      style={{flex: 1}}
                      onClick={() => {
                        const newCount = gardenClickCount + 1
                        setGardenClickCount(newCount)
                        setActivePanel('garden')
                        if (newCount > 2) {
                          setGuidance(null)
                          setBiblicalExample(null)
                          setQueryResult(null)
                        }
                      }}
                    >
                      {loading ? '⏳ 俯伏祷告...' : '🌿 求赐恩言'}
                    </button>
                    <button
                      className="primary-btn mobile-submit-btn"
                      type="button"
                      disabled={sermonLoading || !query.trim()}
                      style={{flex: 1, background: 'linear-gradient(135deg,#5e5ce6,#af52de)'}}
                      onClick={() => {
                        const newCount = sermonClickCount + 1
                        setSermonClickCount(newCount)
                        setActivePanel('sermon')
                        if (newCount === 1 || newCount > 2) {
                          setSermon(null)
                          setSermonLoading(true)
                          fetchSermon(query).then(s => { setSermon(s); setSermonLoading(false) }).catch(() => setSermonLoading(false))
                        }
                      }}
                    >
                      {sermonLoading ? '⏳ 心灵花园...' : '📜 专属讲道'}
                    </button>
                  </div>
                </form>
              </section>
              <section className="mobile-pane" style={{display: 'none'}}>
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

              {sermon && activePanel === 'sermon' && (
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

              {(guidance || biblicalExample || queryResult) && activePanel !== 'sermon' && (
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

              {queryResult?.verse_summary && (
                <div className="export-bar">
                  <button className="export-btn" onClick={exportVersesToTxt} title="导出TXT">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                      <polyline points="10 9 9 9 8 9"/>
                    </svg>
                    导出TXT
                  </button>
                  <button className="export-btn" onClick={exportVersesToPdf} title="导出PDF">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <path d="M9 15l3 3 3-3"/>
                      <path d="M12 18V9"/>
                    </svg>
                    导出PDF
                  </button>
                </div>
              )}

              {historyItems.length > 0 && (
              <section className="mobile-card glass">
                <div className="section-title" style={{display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '12px'}}>
                  <span>🕐</span><span>最近祷告</span>
                </div>
                <div className="history-list">
                  {historyItems.slice(0, 8).map((item, idx) => (
                      <button
                          key={`${item.query_text}-${idx}`}
                          className="history-item"
                          onClick={() => { setQuery(item.query_text) }}
                      >
                        <span style={{fontSize:'12px', opacity:0.4, marginRight:'6px', flexShrink:0}}>›</span>
                        <span style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{item.query_text}</span>
                      </button>
                  ))}
                </div>
              </section>
              )}

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
                <div className="quick-action-list" style={{marginTop: '12px'}}>
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

        {/* 代祷墙页面 */}
        {activePanel === 'prayer' && (
          <PrayerWallPage
            user={user}
            token={getToken()}
            onBack={() => setActivePanel('sphere')}
          />
        )}

        {/* 打卡页面覆盖层（情绪选中后从星球页进入） */}
        {activePanel === 'checkin' && (
          <div className="checkin-overlay">
            <CheckInPage
              user={user}
              emotionLabel={selectedFeature?.zh_label || ''}
              emotionQuery={query}
              token={getToken()}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
        )}

        {/* 讲道日志页面 */}
        {activePanel === 'journal' && (
          <SermonJournalPage
            user={user}
            onBack={() => setActivePanel('sphere')}
          />
        )}

        {/* 灵修日记页面 */}
        {activePanel === 'devotion' && (
          <DevotionJournalPage
            user={user}
            token={getToken()}
            onBack={() => setActivePanel('sphere')}
          />
        )}

        {/* 恩言对话页面 */}
        {activePanel === 'chat' && (
          <ChatPage
            user={user}
            token={getToken()}
            onBack={() => setActivePanel('sphere')}
          />
        )}

        {/* 底部 Tab Bar */}
        <nav className="mobile-bottom-nav glass">
          <button
            className={`mobile-nav-item ${activePanel === 'sphere' ? 'active' : ''}`}
            onClick={() => setActivePanel('sphere')}
          >
            <span className="mobile-nav-icon">🔮</span>
            <span className="mobile-nav-label">星球</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'chat' ? 'active' : ''}`}
            onClick={() => setActivePanel('chat')}
          >
            <span className="mobile-nav-icon">🌿</span>
            <span className="mobile-nav-label">恩言</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'journal' ? 'active' : ''}`}
            onClick={() => setActivePanel('journal')}
          >
            <span className="mobile-nav-icon">📖</span>
            <span className="mobile-nav-label">讲道</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'prayer' ? 'active' : ''}`}
            onClick={() => setActivePanel('prayer')}
          >
            <span className="mobile-nav-icon">🙏</span>
            <span className="mobile-nav-label">代祷</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'devotion' ? 'active' : ''}`}
            onClick={() => setActivePanel('devotion')}
          >
            <span className="mobile-nav-icon">📔</span>
            <span className="mobile-nav-label">日记</span>
          </button>
        </nav>
      </div>
    )
}
