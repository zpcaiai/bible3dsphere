/**
 * BibleReadingPage — 圣经通读 · 在线和合本
 *
 * 三层导航：
 *   书卷列表 → 章节网格 → 章节阅读（完整经文 + 标记已读 + 上/下章）
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { API_BASE } from './api'
import { fetchReadingProgress, markChapterRead } from './api'

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
  body: { flex: 1, overflowY: 'auto', padding: '16px', boxSizing: 'border-box' },
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

// ── 子组件：章节阅读视图 ──────────────────────────────────────────────────────
function ChapterReader({ book, chapter, doneChapters, onMark, onBack, onNav, user }) {
  const [verses, setVerses] = useState(null)
  const [loadErr, setLoadErr] = useState(null)
  const [highlight, setHighlight] = useState('')
  const [marking, setMarking] = useState(false)
  const [marked, setMarked] = useState(false)
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

  useEffect(() => { load(); setMarked(false); setHighlight('') }, [load])
  useEffect(() => { topRef.current?.scrollIntoView({ behavior: 'instant' }) }, [book.name, chapter])

  async function handleMark() {
    if (!user || marking || isDone || marked) return
    setMarking(true)
    try {
      await onMark(book.name, chapter, highlight)
      setMarked(true)
    } finally { setMarking(false) }
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
            {/* Chapter title */}
            <div style={{ fontSize: 12, color: 'rgba(90,200,250,0.6)', fontWeight: 600, marginBottom: 14, letterSpacing: '0.05em' }}>
              {book.name} {chapter}章 · 共{verses.length}节
            </div>

            {/* Verses */}
            {verses.map(v => (
              <div key={v.verse} style={S.verseRow}>
                <span style={S.verseNum}>{v.verse}</span>
                <span style={S.verseText}>{v.text}</span>
              </div>
            ))}

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
