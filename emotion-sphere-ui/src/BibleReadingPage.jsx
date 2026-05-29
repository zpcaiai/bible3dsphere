/**
 * BibleReadingPage — 圣经通读 · 在线和合本
 *
 * 三层导航：
 *   书卷列表 → 章节网格 → 章节阅读（完整经文 + 标记已读 + 上/下章）
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { API_BASE, fetchReadingProgress, markChapterRead, fetchBibleStudy, fetchScripture } from './api'
import { TTSFullBar, TTSButton } from './useGlobalAudio.jsx'

// ── 全部 66 卷（旧约 39 + 新约 27）────────────────────────────────────────────
const BOOKS = [
  // ── 旧约 ──────────────────────────────────────────────────────────────────
  { name: '创世记',       chapters: 50, testament: 'OT' },
  { name: '出埃及记',     chapters: 40, testament: 'OT' },
  { name: '利未记',       chapters: 27, testament: 'OT' },
  { name: '民数记',       chapters: 36, testament: 'OT' },
  { name: '申命记',       chapters: 34, testament: 'OT' },
  { name: '约书亚记',     chapters: 24, testament: 'OT' },
  { name: '士师记',       chapters: 21, testament: 'OT' },
  { name: '路得记',       chapters: 4,  testament: 'OT' },
  { name: '撒母耳记上',   chapters: 31, testament: 'OT' },
  { name: '撒母耳记下',   chapters: 24, testament: 'OT' },
  { name: '列王纪上',     chapters: 22, testament: 'OT' },
  { name: '列王纪下',     chapters: 25, testament: 'OT' },
  { name: '历代志上',     chapters: 29, testament: 'OT' },
  { name: '历代志下',     chapters: 36, testament: 'OT' },
  { name: '以斯拉记',     chapters: 10, testament: 'OT' },
  { name: '尼希米记',     chapters: 13, testament: 'OT' },
  { name: '以斯帖记',     chapters: 10, testament: 'OT' },
  { name: '约伯记',       chapters: 42, testament: 'OT' },
  { name: '诗篇',         chapters: 150, testament: 'OT' },
  { name: '箴言',         chapters: 31, testament: 'OT' },
  { name: '传道书',       chapters: 12, testament: 'OT' },
  { name: '雅歌',         chapters: 8,  testament: 'OT' },
  { name: '以赛亚书',     chapters: 66, testament: 'OT' },
  { name: '耶利米书',     chapters: 52, testament: 'OT' },
  { name: '耶利米哀歌',   chapters: 5,  testament: 'OT' },
  { name: '以西结书',     chapters: 48, testament: 'OT' },
  { name: '但以理书',     chapters: 12, testament: 'OT' },
  { name: '何西阿书',     chapters: 14, testament: 'OT' },
  { name: '约珥书',       chapters: 3,  testament: 'OT' },
  { name: '阿摩司书',     chapters: 9,  testament: 'OT' },
  { name: '俄巴底亚书',   chapters: 1,  testament: 'OT' },
  { name: '约拿书',       chapters: 4,  testament: 'OT' },
  { name: '弥迦书',       chapters: 7,  testament: 'OT' },
  { name: '那鸿书',       chapters: 3,  testament: 'OT' },
  { name: '哈巴谷书',     chapters: 3,  testament: 'OT' },
  { name: '西番雅书',     chapters: 3,  testament: 'OT' },
  { name: '哈该书',       chapters: 2,  testament: 'OT' },
  { name: '撒迦利亚书',   chapters: 14, testament: 'OT' },
  { name: '玛拉基书',     chapters: 4,  testament: 'OT' },
  // ── 新约 ──────────────────────────────────────────────────────────────────
  { name: '马太福音',       chapters: 28, testament: 'NT' },
  { name: '马可福音',       chapters: 16, testament: 'NT' },
  { name: '路加福音',       chapters: 24, testament: 'NT' },
  { name: '约翰福音',       chapters: 21, testament: 'NT' },
  { name: '使徒行传',       chapters: 28, testament: 'NT' },
  { name: '罗马书',         chapters: 16, testament: 'NT' },
  { name: '哥林多前书',     chapters: 16, testament: 'NT' },
  { name: '哥林多后书',     chapters: 13, testament: 'NT' },
  { name: '加拉太书',       chapters: 6,  testament: 'NT' },
  { name: '以弗所书',       chapters: 6,  testament: 'NT' },
  { name: '腓立比书',       chapters: 4,  testament: 'NT' },
  { name: '歌罗西书',       chapters: 4,  testament: 'NT' },
  { name: '帖撒罗尼迦前书', chapters: 5,  testament: 'NT' },
  { name: '帖撒罗尼迦后书', chapters: 3,  testament: 'NT' },
  { name: '提摩太前书',     chapters: 6,  testament: 'NT' },
  { name: '提摩太后书',     chapters: 4,  testament: 'NT' },
  { name: '提多书',         chapters: 3,  testament: 'NT' },
  { name: '腓利门书',       chapters: 1,  testament: 'NT' },
  { name: '希伯来书',       chapters: 13, testament: 'NT' },
  { name: '雅各书',         chapters: 5,  testament: 'NT' },
  { name: '彼得前书',       chapters: 5,  testament: 'NT' },
  { name: '彼得后书',       chapters: 3,  testament: 'NT' },
  { name: '约翰一书',       chapters: 5,  testament: 'NT' },
  { name: '约翰二书',       chapters: 1,  testament: 'NT' },
  { name: '约翰三书',       chapters: 1,  testament: 'NT' },
  { name: '犹大书',         chapters: 1,  testament: 'NT' },
  { name: '启示录',         chapters: 22, testament: 'NT' },
]

const TOTAL_CHAPTERS = BOOKS.reduce((s, b) => s + b.chapters, 0)

// ── 样式常量 ─────────────────────────────────────────────────────────────────
const S = {
  page: { position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', background: '#0a0a1a' },
  header: { display: 'flex', alignItems: 'center', gap: 10, padding: '12px 16px', background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.08)', flexShrink: 0 },
  backBtn: { background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 8, color: '#fff', width: 34, height: 34, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 },
  body: { flex: 1, overflowY: 'auto', padding: '16px 16px 90px', boxSizing: 'border-box' },
  tabBar: { display: 'flex', gap: 6, padding: '8px 16px', flexShrink: 0, borderBottom: '1px solid rgba(255,255,255,0.06)' },
  tab: (active) => ({ fontSize: 12, padding: '5px 14px', borderRadius: 20, border: 'none', background: active ? 'rgba(88,86,214,0.5)' : 'rgba(255,255,255,0.08)', color: active ? '#fff' : 'rgba(255,255,255,0.5)', cursor: 'pointer', fontWeight: active ? 700 : 400 }),
  bookCard: (complete) => ({
    background: complete ? 'linear-gradient(135deg,rgba(0,122,255,0.15),rgba(88,86,214,0.12))' : 'rgba(255,255,255,0.04)',
    border: complete ? '1px solid rgba(0,122,255,0.3)' : '1px solid rgba(255,255,255,0.08)',
    borderRadius: 10, padding: '12px 10px', cursor: 'pointer', userSelect: 'none',
  }),
  chapterBtn: (done, marking) => ({
    height: 42, borderRadius: 8,
    border: done ? 'none' : '1px solid rgba(255,255,255,0.12)',
    background: done ? 'linear-gradient(135deg,#007aff,#5856d6)' : marking ? 'rgba(0,122,255,0.25)' : 'rgba(255,255,255,0.06)',
    color: done ? '#fff' : 'rgba(255,255,255,0.7)', fontSize: 13,
    fontWeight: done ? 700 : 400, cursor: 'pointer',
  }),
  verseRow: { display: 'flex', gap: 8, padding: '7px 0', borderBottom: '1px solid rgba(255,255,255,0.06)', alignItems: 'flex-start' },
  verseNum: { fontSize: 11, fontWeight: 700, color: 'rgba(90,200,250,0.6)', minWidth: 24, paddingTop: 3, flexShrink: 0 },
  verseText: { fontSize: 15, lineHeight: 1.85, color: 'rgba(255,255,255,0.9)' },
}


// ── CrossRefText — 解析文本中的圣经引用，点击展开原文 ──────────────────────
const BIBLE_REF_RE = /([\u4e00-\u9fa5]{2,8}?(?:书|记|篇|传|歌|大|书|纳|伯|玛|太|可|路|约|徒|罗|林[前后]|加|弗|腓|西|帖[前后]|提[前后]|多|门|来|彼[前后]|约[一二三]|犹|启)?[\u4e00-\u9fa5]?)(\d{1,3})[：:](\d{1,3}(?:-\d{1,3})?)/g

function CrossRefText({ text, autoExpand = false }) {
  const [expanded, setExpanded] = useState({})   // ref → {loading, verses, err}

  // Auto-fetch all refs when autoExpand=true (e.g. when section opens)
  useEffect(() => {
    if (!autoExpand || !text) return
    const re2 = new RegExp(BIBLE_REF_RE.source, 'g')
    let m2
    while ((m2 = re2.exec(text)) !== null) {
      const raw = m2[0], book = m2[1], chapter = m2[2], verses = m2[3]
      setExpanded(prev => {
        if (prev[raw]?.verses || prev[raw]?.loading) return prev
        return { ...prev, [raw]: { loading: true } }
      })
      const refStr = book + chapter + ':' + verses
      fetchScripture(refStr)
        .then(data => setExpanded(prev => ({ ...prev, [raw]: { verses: data.verses || [] } })))
        .catch(() => setExpanded(prev => ({ ...prev, [raw]: { err: '无法加载' } })))
    }
  }, [text, autoExpand])

  if (!text) return null

  // Split text into plain segments and reference tokens
  const parts = []
  let last = 0
  const re = new RegExp(BIBLE_REF_RE.source, 'g')
  let m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ type: 'text', value: text.slice(last, m.index) })
    parts.push({ type: 'ref', raw: m[0], book: m[1], chapter: m[2], verses: m[3] })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ type: 'text', value: text.slice(last) })

  async function handleRefClick(ref) {
    if (expanded[ref.raw]?.verses) {
      // toggle off
      setExpanded(prev => { const n = {...prev}; delete n[ref.raw]; return n })
      return
    }
    setExpanded(prev => ({ ...prev, [ref.raw]: { loading: true } }))
    try {
      const refStr = ref.book + ref.chapter + ':' + ref.verses
      const data = await fetchScripture(refStr)
      const vv = data.verses || []
      setExpanded(prev => ({ ...prev, [ref.raw]: { verses: vv } }))
    } catch (e) {
      setExpanded(prev => ({ ...prev, [ref.raw]: { err: '无法加载经文' } }))
    }
  }

  return (
    <span>
      {parts.map((p, i) => {
        if (p.type === 'text') return <span key={i}>{p.value}</span>
        const state = expanded[p.raw]
        const isOpen = !!state?.verses
        return (
          <span key={i} style={{ display: 'inline' }}>
            <button
              onClick={() => handleRefClick(p)}
              style={{
                background: isOpen ? 'rgba(90,200,250,0.18)' : 'rgba(90,200,250,0.10)',
                border: '1px solid rgba(90,200,250,0.35)',
                borderRadius: 5,
                color: '#5ac8fa',
                padding: '1px 6px',
                fontSize: 12,
                cursor: 'pointer',
                margin: '0 2px',
                fontWeight: 600,
              }}
            >
              {state?.loading ? '⏳' : p.raw}
            </button>
            {state?.verses && state.verses.length > 0 && (
              <span style={{
                display: 'block',
                margin: '6px 0 8px 8px',
                padding: '8px 12px',
                background: 'rgba(90,200,250,0.06)',
                border: '1px solid rgba(90,200,250,0.18)',
                borderRadius: 8,
                fontSize: 12,
                color: 'rgba(255,220,100,0.9)',
                lineHeight: 1.8,
                fontStyle: 'italic',
              }}>
                {state.verses.map(v => (
                  <span key={v.verse} style={{ display: 'block' }}>
                    <span style={{ color: 'rgba(90,200,250,0.6)', fontStyle: 'normal', marginRight: 4 }}>{v.verse}</span>
                    {v.text}
                  </span>
                ))}
              </span>
            )}
            {state?.err && <span style={{ color: '#ff6b6b', fontSize: 11 }}> ({state.err})</span>}
          </span>
        )
      })}
    </span>
  )
}

// ── 子组件：章节阅读视图 ──────────────────────────────────────────────────────
function ChapterReader({ book, chapter, doneChapters, onMark, onBack, onNav, user, token }) {
  const [verses, setVerses] = useState(null)
  const [loadErr, setLoadErr] = useState(null)
  const [highlight, setHighlight] = useState('')
  const [marking, setMarking] = useState(false)
  const [marked, setMarked] = useState(false)
  // 查经 state
  const [study, setStudy] = useState(null)
  const [studyLoading, setStudyLoading] = useState(false)
  const [studyErr, setStudyErr] = useState('')
  const [openSections, setOpenSections] = useState({})
  const studyRef = useRef(null)
  const topRef = useRef(null)

  const isDone = (doneChapters || []).includes(chapter)

  const load = useCallback(() => {
    setVerses(null); setLoadErr(null)
    fetch(`${API_BASE}/scripture?ref=${encodeURIComponent(book.name + chapter)}`)
      .then(r => r.json())
      .then(d => {
        if (d.ok && d.verses?.length) setVerses(d.verses)
        else setLoadErr(d.error || '暂无经文内容')
      })
      .catch(() => setLoadErr('加载失败，请检查网络'))
  }, [book.name, chapter])

  useEffect(() => {
    load()
    setMarked(false)
    setHighlight('')
    setStudy(null)
    setStudyLoading(false)
    setStudyErr('')
    setOpenSections({})
  }, [load])
  useEffect(() => { topRef.current?.scrollIntoView({ behavior: 'instant' }) }, [book.name, chapter])

  async function handleMark() {
    if (!user || marking || isDone || marked) return
    setMarking(true)
    if (window.showToast) window.showToast("保存中…", "loading")
    try {
      await onMark(book.name, chapter, highlight)
      setMarked(true)
    } finally { setMarking(false) }
  }

  async function handleGenerateStudy() {
    if (studyLoading || !verses?.length) return
    setStudyLoading(true)
    setStudyErr('')
    setStudy(null)
    if (window.showToast) window.showToast("📖 正在生成查经材料…", "loading", 60000)
    setOpenSections({ summary: true })
    setTimeout(() => studyRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    try {
      const data = await fetchBibleStudy(book.name, chapter, verses, token)
      setStudy(data.study)
      setOpenSections({ summary: true, verse_comments: true })
    } catch (e) {
      setStudyErr(e.message || '生成失败，请重试')
    } finally {
      setStudyLoading(false)
    }
  }

  function toggleSection(key) {
    setOpenSections(prev => ({ ...prev, [key]: !prev[key] }))
  }


  const hasPrev = chapter > 1 || BOOKS.findIndex(b => b.name === book.name) > 0
  const hasNext = chapter < book.chapters || BOOKS.findIndex(b => b.name === book.name) < BOOKS.length - 1

  function prev() {
    if (chapter > 1) { onNav(book, chapter - 1) }
    else {
      const idx = BOOKS.findIndex(b => b.name === book.name)
      if (idx > 0) onNav(BOOKS[idx - 1], BOOKS[idx - 1].chapters)
    }
  }
  function next() {
    if (chapter < book.chapters) { onNav(book, chapter + 1) }
    else {
      const idx = BOOKS.findIndex(b => b.name === book.name)
      if (idx < BOOKS.length - 1) onNav(BOOKS[idx + 1], 1)
    }
  }

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={S.header}>
        <button style={S.backBtn} onClick={onBack}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>{book.name} · 第{chapter}章</div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
            {isDone || marked ? '✅ 已读' : `第 ${chapter}/${book.chapters} 章`}
          </div>
        </div>
        {/* 查经 button */}
        {verses?.length > 0 && (
          <button
            onClick={handleGenerateStudy}
            disabled={studyLoading}
            style={{
              padding: '5px 11px', borderRadius: 8, border: '1px solid rgba(255,200,50,0.35)',
              background: study ? 'rgba(255,200,50,0.18)' : 'rgba(255,200,50,0.10)',
              color: '#ffd60a', fontSize: 12, fontWeight: 600, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 4, whiteSpace: 'nowrap',
            }}
          >
            {studyLoading ? '⏳' : '📖'} {studyLoading ? '生成中…' : study ? '重新查经' : '查经'}
          </button>
        )}

        {/* Prev / Next */}
        <button onClick={prev} disabled={!hasPrev} style={{ ...S.backBtn, opacity: hasPrev ? 1 : 0.3 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <button onClick={next} disabled={!hasNext} style={{ ...S.backBtn, opacity: hasNext ? 1 : 0.3 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><polyline points="9 18 15 12 9 6" /></svg>
        </button>
      </div>

      {/* Body */}
      <div style={S.body}>
        <div ref={topRef} />

        {!verses && !loadErr && (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(90,200,250,0.5)', fontSize: 14 }}>经文加载中…</div>
        )}
        {loadErr && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <div style={{ color: 'rgba(255,100,100,0.7)', marginBottom: 16 }}>{loadErr}</div>
            <button onClick={load} style={{ padding: '8px 20px', borderRadius: 8, border: 'none', background: 'rgba(0,122,255,0.4)', color: '#fff', cursor: 'pointer' }}>重试</button>
          </div>
        )}

        {verses && (
          <>
            {/* Chapter title + TTS */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <div style={{ fontSize: 12, color: 'rgba(90,200,250,0.6)', fontWeight: 600, letterSpacing: '0.05em' }}>
                {book.name} {chapter}章 · 共{verses.length}节
              </div>
              <TTSButton
                text={`${book.name}第${chapter}章。\n` + verses.map(v => `第${v.verse}节。${v.text}`).join('\n')}
                style={{ fontSize: 16, padding: '4px 8px' }}
              />
            </div>

            {/* Verses */}
            {verses.map(v => (
              <div key={v.verse} style={S.verseRow}>
                <span style={S.verseNum}>{v.verse}</span>
                <span style={S.verseText}>{v.text}</span>
              </div>
            ))}



            {/* ── 查经面板 ─────────────────────────────────────────── */}
            <div ref={studyRef} style={{ marginTop: 24 }}>
              {studyLoading && (
                <div style={{ padding: '28px 0', textAlign: 'center', color: 'rgba(255,200,50,0.6)', fontSize: 14 }}>
                  <div style={{ fontSize: 24, marginBottom: 10 }}>📖</div>
                  正在生成查经材料，请稍候…<br />
                  <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)', marginTop: 6, display: 'block' }}>通常需要 15-30 秒</span>
                </div>
              )}
              {studyErr && (
                <div style={{ padding: '14px 16px', borderRadius: 10, background: 'rgba(255,59,48,0.1)', border: '1px solid rgba(255,59,48,0.25)', color: '#ff6b6b', fontSize: 13, marginBottom: 8 }}>
                  {studyErr}
                  <button onClick={handleGenerateStudy} style={{ marginLeft: 12, background: 'none', border: 'none', color: '#5ac8fa', cursor: 'pointer', fontSize: 13 }}>重试</button>
                </div>
              )}
              {study && (() => {
                // Support both new schema (verse_by_verse) and old (verse_comments)
                const vbv = study.verse_by_verse || study.verse_comments || []
                const SECTIONS = [
                  { key: 'overview',      icon: '🗺️', title: '章节概览' },
                  { key: 'summary',       icon: '📋', title: '核心要义' },
                  { key: 'context',       icon: '🏛️', title: '历史文化背景' },
                  { key: 'structure',     icon: '📐', title: '段落结构' },
                  { key: '__vbv__',       icon: '🔍', title: `逐节详解（共${vbv.length}节）` },
                  { key: 'key_words',     icon: '🔑', title: '关键词语原文解析' },
                  { key: 'cross_refs',    icon: '🔗', title: '串珠平行经文' },
                  { key: 'theology',      icon: '✝️',  title: '核心神学主题' },
                  { key: 'echoes',        icon: '📜', title: '历史印证' },
                  { key: 'application',   icon: '✨', title: '时代应用' },
                  { key: 'practice',      icon: '🚶', title: '操练建议' },
                  { key: 'prayer',        icon: '🙏', title: '祷告引导' },
                ]
                // Open overview by default on first render
                return (
                  <div style={{ borderRadius: 14, overflow: 'hidden', border: '1px solid rgba(255,200,50,0.22)', background: 'rgba(255,200,50,0.03)', marginBottom: 8 }}>
                    {/* Study header + full TTS */}
                    <div style={{ padding: '13px 16px', background: 'linear-gradient(135deg,rgba(255,200,50,0.14),rgba(255,160,20,0.08))', borderBottom: '1px solid rgba(255,200,50,0.18)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                        <span style={{ fontSize: 18 }}>📖</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: 14, fontWeight: 700, color: '#ffd60a' }}>查经 — {book.name} 第{chapter}章</div>
                          <div style={{ fontSize: 11, color: 'rgba(255,200,50,0.55)', marginTop: 2 }}>逐节精解 · 神学主题 · 祷告引导</div>
                        </div>
                      </div>
                      {/* 全篇朗读 */}
                      <TTSFullBar
                        label="全篇朗读"
                        buildText={() => {
                          const parts = []
                          const KEYS = ['overview','summary','context','structure','key_words','cross_refs','theology','echoes','application','practice','prayer']
                          const LABELS = {overview:'章节概览',summary:'核心要义',context:'历史文化背景',structure:'段落结构',key_words:'关键词语',cross_refs:'串珠平行经文',theology:'核心神学主题',echoes:'历史印证',application:'时代应用',practice:'操练建议',prayer:'祷告引导'}
                          KEYS.forEach(k => {
                            const v = study[k]
                            if (!v) return
                            if (k === 'prayer') { parts.push(LABELS[k] + '。' + v); return }
                            parts.push(LABELS[k] + '。' + (typeof v === 'string' ? v : ''))
                          })
                          const vbv = study.verse_by_verse || study.verse_comments || []
                          if (vbv.length) {
                            const vtext = vbv.map(item => {
                              const n = item.verse ?? item.range
                              return `第${n}节：${item.comment || ''}${item.apply ? '　应用：' + item.apply : ''}`
                            }).join('　')
                            parts.splice(3, 0, '逐节详解。' + vtext)
                          }
                          return parts.join('\n\n')
                        }}
                      />
                    </div>
                    {SECTIONS.map(({ key, icon, title }) => {
                      const isVbv = key === '__vbv__'
                      const content = isVbv ? vbv : study[key]
                      if (!content || (Array.isArray(content) && content.length === 0)) return null
                      const isOpen = !!openSections[key]

                      // Build TTS text for this section
                      const sectionTtsText = isVbv
                        ? vbv.map(item => {
                            const n = item.verse ?? item.range
                            return `第${n}节：${item.comment || ''}${item.apply ? '　应用：' + item.apply : ''}`
                          }).join('　')
                        : (typeof content === 'string' ? content : '')

                      return (
                        <div key={key} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          {/* Section header row: toggle + TTS button */}
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <button
                              onClick={() => toggleSection(key)}
                              style={{ flex: 1, padding: '12px 8px 12px 16px', background: isOpen ? 'rgba(255,200,50,0.06)' : 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, textAlign: 'left', transition: 'background 0.15s' }}
                            >
                              <span style={{ fontSize: 15 }}>{icon}</span>
                              <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: isOpen ? '#ffd60a' : 'rgba(255,255,255,0.82)' }}>{title}</span>
                              <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.3)', transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }}>▼</span>
                            </button>
                            {sectionTtsText && (
                              <TTSButton text={sectionTtsText} style={{ marginRight: 10, fontSize: 15 }} />
                            )}
                          </div>
                          {isOpen && (
                            <div style={{ padding: '0 14px 16px 14px' }}>
                              {isVbv ? (
                                /* ── 逐节详解 ── */
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                  {vbv.map((item, i) => {
                                    const verseNum = item.verse ?? item.range
                                    const comment  = item.comment || ''
                                    const wordNote = item.word || ''
                                    const applyNote= item.apply || ''
                                    const vbvTts   = `第${verseNum}节：${comment}${applyNote ? '　应用：' + applyNote : ''}`
                                    return (
                                      <div key={i} style={{ borderRadius: 10, border: '1px solid rgba(90,200,250,0.15)', background: 'rgba(90,200,250,0.04)', overflow: 'hidden' }}>
                                        {/* Verse badge row + per-verse TTS */}
                                        <div style={{ padding: '8px 12px', background: 'rgba(90,200,250,0.09)', display: 'flex', alignItems: 'center', gap: 8 }}>
                                          <span style={{ minWidth: 28, height: 28, borderRadius: 14, background: 'rgba(90,200,250,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, color: '#5ac8fa', flexShrink: 0 }}>
                                            {verseNum}
                                          </span>
                                          {verses && (() => {
                                            const vObj = typeof verseNum === 'number' ? verses.find(v => v.verse === verseNum) : null
                                            return vObj ? (
                                              <span style={{ flex: 1, fontSize: 12, color: 'rgba(255,220,80,0.85)', lineHeight: 1.6, fontStyle: 'italic' }}>{vObj.text}</span>
                                            ) : <span style={{ flex: 1 }} />
                                          })()}
                                          <TTSButton text={vbvTts} style={{ fontSize: 13, flexShrink: 0 }} />
                                        </div>
                                        {/* Commentary */}
                                        <div style={{ padding: '10px 12px', fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.85, whiteSpace: 'pre-wrap' }}>{comment}</div>
                                        {wordNote && (
                                          <div style={{ margin: '0 12px 10px', padding: '8px 12px', borderRadius: 8, background: 'rgba(88,86,214,0.12)', border: '1px solid rgba(88,86,214,0.25)' }}>
                                            <span style={{ fontSize: 10, fontWeight: 700, color: 'rgba(180,170,255,0.7)', letterSpacing: '0.06em' }}>🔑 原文词语　</span>
                                            <span style={{ fontSize: 12, color: 'rgba(200,190,255,0.9)', lineHeight: 1.75 }}>{wordNote}</span>
                                          </div>
                                        )}
                                        {applyNote && (
                                          <div style={{ margin: '0 12px 12px', padding: '7px 12px', borderRadius: 8, background: 'rgba(52,199,89,0.08)', border: '1px solid rgba(52,199,89,0.2)' }}>
                                            <span style={{ fontSize: 10, fontWeight: 700, color: 'rgba(100,220,120,0.7)', letterSpacing: '0.06em' }}>💚 应用提示　</span>
                                            <span style={{ fontSize: 12, color: 'rgba(160,240,180,0.9)', lineHeight: 1.7 }}>{applyNote}</span>
                                          </div>
                                        )}
                                      </div>
                                    )
                                  })}
                                </div>
                              ) : key === 'prayer' ? (
                                /* ── 祷告引导 ── */
                                <div style={{ padding: '14px 16px', borderRadius: 10, background: 'rgba(255,200,50,0.06)', border: '1px solid rgba(255,200,50,0.15)', fontSize: 13, color: 'rgba(255,230,120,0.9)', lineHeight: 2, whiteSpace: 'pre-wrap', fontStyle: 'italic' }}>
                                  🙏 {typeof content === 'string' ? content : ''}
                                </div>
                              ) : key === 'cross_refs' ? (
                                /* ── 串珠平行经文：自动展开所有引用经文 ── */
                                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.9, paddingTop: 4 }}>
                                  <CrossRefText text={typeof content === 'string' ? content : ''} autoExpand={isOpen} />
                                </div>
                              ) : (
                                /* ── 普通段落 ── */
                                <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.82)', lineHeight: 1.9, whiteSpace: 'pre-wrap', paddingTop: 4 }}>
                                  {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })()}
            </div>

            {/* Mark as read section */}
            {user && (
              <div style={{ marginTop: 28, padding: '16px', background: 'rgba(255,255,255,0.04)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.08)' }}>
                {isDone || marked ? (
                  <div style={{ textAlign: 'center', color: 'rgba(52,199,89,0.8)', fontSize: 14, padding: '8px 0' }}>
                    ✅ 已标记为已读
                  </div>
                ) : (
                  <>
                    <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 10 }}>读完了？记录一句遇见神的话：</div>
                    <input
                      value={highlight}
                      onChange={e => setHighlight(e.target.value)}
                      placeholder="可选：摘录一节经文或灵感（可留空）"
                      style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.06)', color: '#fff', fontSize: 13, outline: 'none', boxSizing: 'border-box', marginBottom: 12 }}
                    />
                    <button onClick={handleMark} disabled={marking}
                      style={{ width: '100%', padding: '11px', borderRadius: 10, border: 'none', background: marking ? 'rgba(0,122,255,0.3)' : 'linear-gradient(135deg,#007aff,#5856d6)', color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>
                      {marking ? '保存中…' : '✓ 标记本章已读'}
                    </button>
                  </>
                )}
              </div>
            )}

            {/* Bottom navigation */}
            <div style={{ display: 'flex', gap: 10, marginTop: 16, marginBottom: 20 }}>
              {hasPrev && (
                <button onClick={prev} style={{ flex: 1, padding: '11px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.7)', fontSize: 13, cursor: 'pointer' }}>
                  ← 上一章
                </button>
              )}
              {hasNext && (
                <button onClick={next} style={{ flex: 1, padding: '11px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.7)', fontSize: 13, cursor: 'pointer' }}>
                  下一章 →
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────
export default function BibleReadingPage({ user, token, onBack }) {
  const [progress, setProgress] = useState({ items: [], by_book: {} })
  const [loadingProgress, setLoadingProgress] = useState(true)
  const [view, setView] = useState('books')      // 'books' | 'chapters' | 'reading'
  const [selectedBook, setSelectedBook] = useState(null)
  const [selectedChapter, setSelectedChapter] = useState(null)
  const [testament, setTestament] = useState('NT')
  const [completedBook, setCompletedBook] = useState(null)

  // Load progress
  useEffect(() => {
    if (!user) { setLoadingProgress(false); return }
    fetchReadingProgress(token)
      .then(p => setProgress(p))
      .catch(() => {})
      .finally(() => setLoadingProgress(false))
  }, [user, token])

  const totalDone = Object.values(progress.by_book).reduce((s, chs) => s + chs.length, 0)
  const pct = Math.round((totalDone / TOTAL_CHAPTERS) * 100)

  async function handleMark(book, chapter, hl) {
    try {
      const result = await markChapterRead(book, chapter, hl, token)
      const updated = await fetchReadingProgress(token)
      setProgress(updated)
      if (result.book_completed) {
        setCompletedBook(book)
        setTimeout(() => setCompletedBook(null), 4000)
      }
    } catch (e) { console.error(e) }
  }

  // ── Reading view ────────────────────────────────────────────────────────────
  if (view === 'reading' && selectedBook && selectedChapter) {
    return (
      <ChapterReader
        book={selectedBook}
        chapter={selectedChapter}
        doneChapters={progress.by_book[selectedBook.name] || []}
        onMark={handleMark}
        user={user}
        token={token}
        onBack={() => setView('chapters')}
        onNav={(book, ch) => {
          // If navigating to a different book, update selectedBook too
          if (book.name !== selectedBook.name) {
            setSelectedBook(book)
          }
          setSelectedChapter(ch)
        }}
      />
    )
  }

  const visibleBooks = BOOKS.filter(b => b.testament === testament)

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={S.header}>
        <button style={S.backBtn} onClick={view === 'chapters' ? () => setView('books') : onBack}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#fff' }}>
            {view === 'chapters' && selectedBook ? `📖 ${selectedBook.name}` : '📖 圣经通读'}
          </div>
          {view === 'books' ? (
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
              {totalDone} / {TOTAL_CHAPTERS} 章 · {pct}% 已读完
            </div>
          ) : selectedBook ? (
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 1 }}>
              {(progress.by_book[selectedBook.name] || []).length} / {selectedBook.chapters} 章已读
            </div>
          ) : null}
        </div>
      </div>

      {/* Completed book toast */}
      {completedBook && (
        <div style={{ background: 'linear-gradient(135deg,#ffd700,#ff9500)', padding: '10px', textAlign: 'center', fontSize: 13, fontWeight: 700, color: '#000', flexShrink: 0 }}>
          🎉 你读完了整卷《{completedBook}》！
        </div>
      )}

      {/* OT / NT tabs — only on books view */}
      {view === 'books' && (
        <div style={S.tabBar}>
          {[['NT', '新约'], ['OT', '旧约']].map(([k, l]) => (
            <button key={k} onClick={() => setTestament(k)} style={S.tab(testament === k)}>{l}</button>
          ))}
          <div style={{ flex: 1 }} />
          {user && (
            <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)', alignSelf: 'center' }}>
              全本 {pct}% ✓
            </div>
          )}
        </div>
      )}

      {/* Body */}
      <div style={S.body}>

        {/* Overall progress bar */}
        {view === 'books' && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#5856d6,#007aff)', borderRadius: 3, transition: 'width .5s' }} />
            </div>
          </div>
        )}

        {loadingProgress ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'rgba(255,255,255,0.3)', fontSize: 13 }}>加载中…</div>
        ) : view === 'books' ? (
          // ── Book list ─────────────────────────────────────────────────────
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(128px, 1fr))', gap: 8 }}>
            {visibleBooks.map(book => {
              const done = (progress.by_book[book.name] || []).length
              const bPct = Math.round((done / book.chapters) * 100)
              const complete = done >= book.chapters
              return (
                <div key={book.name} style={S.bookCard(complete)}
                  onClick={() => { setSelectedBook(book); setView('chapters') }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{book.name}</span>
                    {complete && <span style={{ fontSize: 11 }}>✅</span>}
                  </div>
                  <div style={{ height: 3, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginBottom: 5 }}>
                    <div style={{ height: '100%', width: `${bPct}%`, background: complete ? '#007aff' : '#5856d6', borderRadius: 2 }} />
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)' }}>{done}/{book.chapters} 章</div>
                </div>
              )
            })}
          </div>
        ) : (
          // ── Chapter grid ──────────────────────────────────────────────────
          <div>
            <div style={{ marginBottom: 16, fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>
              点击章节数字可阅读全章经文
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(50px, 1fr))', gap: 8 }}>
              {Array.from({ length: selectedBook.chapters }, (_, i) => i + 1).map(ch => {
                const done = (progress.by_book[selectedBook.name] || []).includes(ch)
                return (
                  <button key={ch}
                    style={S.chapterBtn(done, false)}
                    onClick={() => { setSelectedChapter(ch); setView('reading') }}>
                    {ch}
                  </button>
                )
              })}
            </div>

            {/* Legend */}
            <div style={{ marginTop: 18, display: 'flex', gap: 16, fontSize: 12, color: 'rgba(255,255,255,0.35)' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 16, height: 16, background: 'linear-gradient(135deg,#007aff,#5856d6)', borderRadius: 4, display: 'inline-block' }} />已读
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 16, height: 16, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 4, display: 'inline-block' }} />未读
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
