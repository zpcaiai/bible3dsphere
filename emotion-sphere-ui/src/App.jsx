import { useEffect, useMemo, useState } from 'react'
import jsPDF from 'jspdf'
import html2canvas from 'html2canvas'
import { fetchBiblicalExample, fetchFeatureDetail, fetchGuidance, fetchHistory, fetchLayout, fetchSermon, fetchStats, runQuery, trackStats } from './api'
import { fetchCurrentUser, getCachedUser, getToken, logout, setCachedUser, clearToken } from './auth'
import { isIosInstallable, promptInstall, subscribeToInstallPrompt } from './pwa'
import { useEmotionStore } from './store'
import { EmotionSphereScene } from './EmotionSphereScene'
import LoginScreen from './LoginScreen'
import CheckInPage from './CheckInPage'
import ShareWallPage from './ShareWallPage'
import PersonalDevotionPage from './PersonalDevotionPage'
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

  const updateUser = (u) => {
    setUser(u)
    if (u) {
      setCachedUser(u)
    } else {
      clearToken()
    }
  }

  return { user, authLoading, setUser: updateUser, handleLogout }
}

export default function App() {
  const { user, setUser, authLoading, handleLogout } = useAuth()

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
  const [pendingPanel, setPendingPanel] = useState(null)
  const [loginMessage, setLoginMessage] = useState('')
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
    if (!queryResult?.verse_summary && !sermon) return
    let content = `情感星球 - 默想经文\n`
    content += `查询：${query}\n`
    content += `日期：${new Date().toLocaleString('zh-CN')}\n\n`

    // 添加引导信息（带小标题，与页面一致）
    if (guidance) {
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n`
      content += `  引导信息\n`
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n\n`
      if (guidance.core_emotions?.length) {
        content += `【核心情绪】\n`
        content += `${guidance.core_emotions.join('、')}\n\n`
      }
      if (guidance.core_need) {
        content += `【核心需要】\n`
        content += `${guidance.core_need}\n\n`
      }
      if (guidance.psychological_assessment) {
        content += `【心理评估】\n`
        content += `${guidance.psychological_assessment}\n\n`
      }
      if (guidance.spiritual_guidance) {
        content += `【属灵引导】\n`
        content += `${guidance.spiritual_guidance}\n\n`
      }
      if (guidance.coping_suggestions?.length) {
        content += `【应对建议】\n`
        content += `${guidance.coping_suggestions.map((s, i) => `${i + 1}. ${s}`).join('\n')}\n\n`
      }
    }

    // 添加圣经例子（带小标题）
    if (biblicalExample) {
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n`
      content += `  圣经榜样\n`
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n\n`
      if (biblicalExample.person) {
        content += `人物：${biblicalExample.person}`
        if (biblicalExample.era) content += ` (${biblicalExample.era})`
        content += `\n\n`
      }
      if (biblicalExample.similar_situation) {
        content += `【相似处境】\n`
        content += `${biblicalExample.similar_situation}\n\n`
      }
      if (biblicalExample.biblical_response) {
        content += `【圣经回应】\n`
        content += `${biblicalExample.biblical_response}\n\n`
      }
      if (biblicalExample.key_verse) {
        content += `【关键经文】\n`
        content += `${biblicalExample.key_verse}\n\n`
      }
      if (biblicalExample.application) {
        content += `【应用】\n`
        content += `${biblicalExample.application}\n\n`
      }
    }

    // 添加默想经文（放到最后，与 PDF 一致）
    const groups = verseGroupsFromResult(queryResult, languageFilter)
    if (groups.length > 0) {
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n`
      content += `  默想经文\n`
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n\n`
      groups.forEach(group => {
        content += `─── ${group.language === 'cuv' ? '中文（和合本）' : 'English (ESV)'} ───\n\n`
        group.items.forEach(item => {
          content += `▸ ${item.book_name} ${item.chapter}:${item.verse}\n`
          content += `${item.raw_text}\n\n`
        })
      })
    }

    // 添加讲道内容
    if (sermon) {
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n`
      content += `  专属讲道${sermon.title ? `：${sermon.title}` : ''}\n`
      content += `━━━━━━━━━━━━━━━━━━━━━━━\n\n`
      if (sermon.theme_verse) {
        content += `【主题经文】\n`
        content += `${sermon.theme_verse}\n\n`
      }
      if (sermon.introduction) {
        content += `【引言】\n`
        content += `${sermon.introduction}\n\n`
      }
      sermon.sections?.forEach((sec) => {
        content += `【${sec.heading}】\n`
        content += `${sec.content}\n\n`
      })
      if (sermon.spiritual_diagnosis) {
        content += `【属灵剖析】\n`
        content += `${sermon.spiritual_diagnosis}\n\n`
      }
      if (sermon.application) {
        content += `【属灵操练】\n`
        const appText = Array.isArray(sermon.application)
          ? sermon.application.join('\n')
          : (typeof sermon.application === 'object' ? JSON.stringify(sermon.application, null, 2) : sermon.application)
        content += `${appText}\n\n`
      }
    }

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url

    // Format filename: emotions or sermon title + datetime
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const datetime = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`

    let filenameBase
    if (guidance?.core_emotions?.length > 0) {
      // Use emotions joined by & for "求赐恩言"
      filenameBase = guidance.core_emotions.slice(0, 3).join('&')
    } else if (sermon?.title) {
      // Use sermon title for "专属讲道"
      const titleStr = typeof sermon.title === 'string' ? sermon.title : String(sermon.title)
      filenameBase = titleStr.replace(/[\\/:*?"<>|]/g, '')
    } else {
      filenameBase = '默想经文'
    }

    a.download = `${filenameBase}_${datetime}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function exportVersesToPdf() {
    if (!queryResult?.verse_summary && !sermon) return

    // Create a hidden container for PDF generation
    const container = document.createElement('div')
    container.style.cssText = 'position: fixed; left: -9999px; top: 0; width: 794px; background: #0d0d1a; padding: 40px; font-family: "Microsoft YaHei", "PingFang SC", "SimHei", sans-serif; line-height: 1.6; color: #ffffff;'
    document.body.appendChild(container)

    // Format filename
    const now = new Date()
    const pad = (n) => String(n).padStart(2, '0')
    const datetime = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
    let filenameBase
    if (guidance?.core_emotions?.length > 0) {
      filenameBase = guidance.core_emotions.slice(0, 3).join('&')
    } else if (sermon?.title) {
      const titleStr = typeof sermon.title === 'string' ? sermon.title : String(sermon.title)
      filenameBase = titleStr.replace(/[\\/:*?"<>|]/g, '')
    } else {
      filenameBase = '默想经文'
    }
    const filename = `${filenameBase}_${datetime}.pdf`

    // Build content (dark theme matching the app) — 经文放最后
    let content = `
      <h1 style="font-size: 20px; color: #007aff; margin-bottom: 10px;">情感星球 - 默想经文</h1>
      <div style="font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 20px;">查询：${query}<br>日期：${new Date().toLocaleString('zh-CN')}</div>
    `

    // 先添加引导信息
    if (guidance) {
      content += '<div style="margin: 20px 0;"><div style="font-size: 14px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">引导信息</div><div style="background: rgba(0,122,255,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(0,122,255,0.25); margin: 12px 0; color: #ffffff;">'
      if (guidance.core_emotions?.length) {
        content += `<div style="margin-bottom:8px;"><strong style="color:#5ac8fa;">核心情绪：</strong>${guidance.core_emotions.join('、')}</div>`
      }
      if (guidance.core_need) {
        content += `<div style="margin-bottom:8px;"><strong style="color:#5ac8fa;">核心需要：</strong>${guidance.core_need}</div>`
      }
      if (guidance.psychological_assessment) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">心理评估</strong><div style="margin-top:6px;color:rgba(255,255,255,0.88);">${guidance.psychological_assessment.replace(/\n/g, '<br>')}</div></div>`
      }
      if (guidance.spiritual_guidance) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">属灵引导</strong><div style="margin-top:6px;color:rgba(255,255,255,0.88);">${guidance.spiritual_guidance.replace(/\n/g, '<br>')}</div></div>`
      }
      if (guidance.coping_suggestions?.length) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">应对建议</strong><ol style="margin:6px 0;padding-left:20px;color:rgba(255,255,255,0.88);">${guidance.coping_suggestions.map(s => `<li style="margin:4px 0;">${s}</li>`).join('')}</ol></div>`
      }
      content += '</div></div>'
    }

    // 添加圣经例子
    if (biblicalExample) {
      content += '<div style="margin: 20px 0;"><div style="font-size: 14px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">圣经例子</div><div style="background: rgba(0,122,255,0.15); padding: 14px; border-radius: 8px; border: 1px solid rgba(0,122,255,0.25); margin: 12px 0; color: #ffffff;">'
      if (biblicalExample.person) {
        content += `<div style="margin-bottom:8px;"><strong style="color:#5ac8fa;">人物：</strong>${biblicalExample.person}${biblicalExample.era ? ` (${biblicalExample.era})` : ''}</div>`
      }
      if (biblicalExample.similar_situation) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">相似处境</strong><div style="margin-top:6px;">${biblicalExample.similar_situation.replace(/\n/g, '<br>')}</div></div>`
      }
      if (biblicalExample.biblical_response) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">圣经回应</strong><div style="margin-top:6px;">${biblicalExample.biblical_response.replace(/\n/g, '<br>')}</div></div>`
      }
      if (biblicalExample.key_verse) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">关键经文</strong><div style="margin-top:6px;font-style:italic;color:rgba(255,255,255,0.88);">${biblicalExample.key_verse}</div></div>`
      }
      if (biblicalExample.application) {
        content += `<div style="margin:12px 0;"><strong style="color:#5ac8fa;">应用</strong><div style="margin-top:6px;">${biblicalExample.application.replace(/\n/g, '<br>')}</div></div>`
      }
      content += '</div></div>'
    }

    // 添加默想经文（放到最后）
    const groups = verseGroupsFromResult(queryResult, languageFilter)
    if (groups.length > 0) {
      content += '<div style="margin: 20px 0;"><div style="font-size: 14px; font-weight: bold; color: rgba(255,255,255,0.78); margin-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 4px;">默想经文</div>'
      groups.forEach(group => {
        content += `<div style="margin: 16px 0 8px; font-size: 12px; color: rgba(255,255,255,0.5); font-weight: 600;">${group.language === 'cuv' ? '中文（和合本）' : 'English (ESV)'}</div>`
        group.items.forEach(item => {
          content += `
            <div style="margin: 10px 0; padding: 10px; background: rgba(255,255,255,0.06); border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
              <div style="font-size: 11px; color: #007aff; font-weight: 600;">${item.book_name} ${item.chapter}:${item.verse}</div>
              <div style="font-size: 13px; margin-top: 4px; color: #ffffff;">${item.raw_text}</div>
            </div>
          `
        })
      })
      content += '</div>'
    }

    // 添加讲道内容
    if (sermon) {
      content += `<div style="margin: 20px 0; background: rgba(88,86,214,0.2); padding: 14px; border-radius: 8px; border: 1px solid rgba(88,86,214,0.35);"><div style="font-size: 16px; font-weight: bold; color: #a78bfa; margin-bottom: 8px;">专属讲道：${sermon.title || ''}</div>`
      if (sermon.theme_verse) content += `<div style="font-style:italic;margin-bottom:12px;color:rgba(255,255,255,0.7);">${sermon.theme_verse}</div>`
      if (sermon.introduction) content += `<p style="color:#ffffff;">${sermon.introduction.replace(/\n/g, '<br>')}</p>`
      sermon.sections?.forEach((sec) => {
        content += `<div style="margin:12px 0;"><strong style="color:#c4b5fd;">${sec.heading}</strong><p style="color:rgba(255,255,255,0.88);margin-top:6px;">${sec.content.replace(/\n/g, '<br>')}</p></div>`
      })
      if (sermon.spiritual_diagnosis) content += `<div style="margin-top:12px;"><strong style="color:#c4b5fd;">属灵剖析</strong><p style="color:rgba(255,255,255,0.88);margin-top:6px;">${sermon.spiritual_diagnosis.replace(/\n/g, '<br>')}</p></div>`
      if (sermon.application) {
        const appHtml = Array.isArray(sermon.application)
          ? sermon.application.map(a => `<p style="color:rgba(255,255,255,0.88);">${a.replace(/\n/g, '<br>')}</p>`).join('')
          : (typeof sermon.application === 'object' ? `<pre style="color:#ffffff;">${JSON.stringify(sermon.application, null, 2)}</pre>` : `<p style="color:rgba(255,255,255,0.88);">${sermon.application.replace(/\n/g, '<br>')}</p>`)
        content += `<div style="margin-top:12px;"><strong style="color:#c4b5fd;">属灵操练</strong>${appHtml}</div>`
      }
      content += `</div>`
    }

    container.innerHTML = content

    // Generate PDF using html2canvas + jsPDF
    try {
      const canvas = await html2canvas(container, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff'
      })

      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF('p', 'mm', 'a4')
      const pdfWidth = pdf.internal.pageSize.getWidth()
      const pdfHeight = pdf.internal.pageSize.getHeight()
      const imgWidth = canvas.width
      const imgHeight = canvas.height
      const ratio = Math.min(pdfWidth / imgWidth, pdfHeight / imgHeight)
      const imgX = (pdfWidth - imgWidth * ratio) / 2
      let imgY = 10

      // Calculate how many pages needed
      const scaledHeight = imgHeight * ratio * (pdfWidth - 20) / (imgWidth * ratio)
      let heightLeft = scaledHeight
      let position = 0

      // Add first page
      pdf.addImage(imgData, 'PNG', 10, imgY, pdfWidth - 20, scaledHeight)
      heightLeft -= (pdfHeight - 20)

      // Add more pages if content is long
      while (heightLeft >= 0) {
        position = heightLeft - scaledHeight + 10
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', 10, position, pdfWidth - 20, scaledHeight)
        heightLeft -= (pdfHeight - 20)
      }

      pdf.save(filename)
    } catch (err) {
      console.error('PDF generation failed:', err)
      alert('PDF 生成失败，请重试')
    } finally {
      document.body.removeChild(container)
    }
  }

  function handlePanelSwitch(panel) {
    const needsLogin = ['mydevotion', 'prayer', 'devotion']
    if (needsLogin.includes(panel) && !user) {
      const messages = {
        mydevotion: '登录后记录和分享你的灵修日记',
        prayer: '登录后参与代祷和分享祷告需要',
        devotion: '登录后记录你的灵修成长'
      }
      setLoginMessage(messages[panel])
      setPendingPanel(panel)
      setShowLogin(true)
      return
    }
    setActivePanel(panel)
  }

  function handleLoginSuccess(u) {
    setUser(u)  // Update React auth state so user is recognized
    setShowLogin(false)
    if (pendingPanel) {
      setActivePanel(pendingPanel)
      setPendingPanel(null)
      setLoginMessage('')
    } else {
      // No need to reload since state is now properly updated
      setActivePanel('sphere')
    }
  }

    if (showLogin) {
      return (
        <div className="mobile-app-shell">
          <LoginScreen 
            onLogin={handleLoginSuccess} 
            onBack={() => {
              setShowLogin(false)
              setPendingPanel(null)
              setLoginMessage('')
            }}
            message={loginMessage}
          />
        </div>
      )
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

                  {/* 快速提示 */}
                  <div style={{margin: '10px 0'}}>
                    <div style={{fontSize: '12px', color: 'rgba(255,255,255,0.5)', marginBottom: '8px'}}>✨ 你可以这样开始：</div>
                    <div style={{display: 'flex', flexWrap: 'wrap', gap: '8px'}}>
                      {[
                        '我最近感到很焦虑，不知道神是否在乎我',
                        '我在工作中遭遇不公平，很难饶恕那个人',
                        '我对祷告感到疲惫，感觉神沉默不语',
                        '我和配偶之间有很深的隔阂，不知道怎么办',
                        '我重复犯同样的罪，非常自责',
                        '我想更亲近神，但不知从哪里开始',
                      ].map((s) => (
                        <button
                          key={s}
                          type="button"
                          onClick={() => setQuery(s)}
                          style={{
                            fontSize: '12px',
                            padding: '6px 12px',
                            borderRadius: '16px',
                            border: '1px solid rgba(255,255,255,0.15)',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'rgba(255,255,255,0.8)',
                            cursor: 'pointer',
                            textAlign: 'left',
                            lineHeight: 1.4,
                          }}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>

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
                        // Always fetch sermon on first click or after reset
                        if (newCount === 1 || newCount > 2) {
                          setSermonLoading(true)
                          fetchSermon(query)
                            .then(s => { setSermon(s); setSermonLoading(false) })
                            .catch(() => setSermonLoading(false))
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
                        <>
                          <div className="result-sub-label">核心情绪</div>
                          <div className="guidance-emotions">
                            {guidance.core_emotions.map((e) => (
                              <span key={e} className="emotion-tag">{e}</span>
                            ))}
                          </div>
                        </>
                      )}
                      {guidance.psychological_assessment && (
                        <>
                          <div className="result-sub-label">心理评估</div>
                          <p className="result-body-text">{guidance.psychological_assessment}</p>
                        </>
                      )}
                      {guidance.core_need && (
                        <>
                          <div className="result-sub-label">核心需要</div>
                          <div className="result-core-need">{guidance.core_need}</div>
                        </>
                      )}
                      {guidance.coping_suggestions?.length > 0 && (
                        <>
                          <div className="result-sub-label">应对建议</div>
                          <ul className="guidance-tips">
                            {guidance.coping_suggestions.map((s, i) => (
                              <li key={i}>{s}</li>
                            ))}
                          </ul>
                        </>
                      )}
                      {guidance.spiritual_guidance && (
                        <>
                          <div className="result-sub-label">属灵引导</div>
                          <div className="result-spiritual-block">
                            <p>{guidance.spiritual_guidance}</p>
                          </div>
                        </>
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
                        <>
                          <div className="result-sub-label">相似处境</div>
                          <p className="result-body-text">{biblicalExample.similar_situation}</p>
                        </>
                      )}
                      {biblicalExample.biblical_response && (
                        <>
                          <div className="result-sub-label">圣经回应</div>
                          <p className="result-body-text">{biblicalExample.biblical_response}</p>
                        </>
                      )}
                      {biblicalExample.key_verse && (
                        <>
                          <div className="result-sub-label">关键经文</div>
                          <div className="result-spiritual-block">
                            <p style={{fontStyle: 'italic', margin: 0}}>{biblicalExample.key_verse}</p>
                          </div>
                        </>
                      )}
                      {biblicalExample.application && (
                        <>
                          <div className="result-sub-label">应用</div>
                          <div className="result-core-need">{biblicalExample.application}</div>
                        </>
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

              {(queryResult?.verse_summary || sermon) && (
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
          <div className="page-overlay">
            <PrayerWallPage
              user={user}
              token={getToken()}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
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

        {/* 主日信息页面 */}
        {activePanel === 'journal' && (
          <div className="page-overlay">
            <SermonJournalPage
              user={user}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
        )}

        {/* 灵修日记页面 */}
        {activePanel === 'devotion' && (
          <div className="page-overlay">
            <DevotionJournalPage
              user={user}
              token={getToken()}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
        )}

        {/* 分享墙页面 */}
        {activePanel === 'sharewall' && (
          <div className="page-overlay">
            <ShareWallPage
              user={user}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
        )}

        {/* 我的日记页面 */}
        {activePanel === 'mydevotion' && (
          <div className="page-overlay">
            <PersonalDevotionPage
              user={user}
              onBack={() => setActivePanel('sphere')}
            />
          </div>
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
            className={`mobile-nav-item ${activePanel === 'sharewall' ? 'active' : ''}`}
            onClick={() => setActivePanel('sharewall')}
          >
            <span className="mobile-nav-icon">🌟</span>
            <span className="mobile-nav-label">分享墙</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'journal' ? 'active' : ''}`}
            onClick={() => setActivePanel('journal')}
          >
            <span className="mobile-nav-icon">📖</span>
            <span className="mobile-nav-label">主日</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'mydevotion' ? 'active' : ''}`}
            onClick={() => handlePanelSwitch('mydevotion')}
          >
            <span className="mobile-nav-icon">✍️</span>
            <span className="mobile-nav-label">日记</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'prayer' ? 'active' : ''}`}
            onClick={() => handlePanelSwitch('prayer')}
          >
            <span className="mobile-nav-icon">🙏</span>
            <span className="mobile-nav-label">代祷</span>
          </button>
          <button
            className={`mobile-nav-item ${activePanel === 'devotion' ? 'active' : ''}`}
            onClick={() => handlePanelSwitch('devotion')}
          >
            <span className="mobile-nav-icon">📔</span>
            <span className="mobile-nav-label">灵修</span>
          </button>
        </nav>
      </div>
    )
}
