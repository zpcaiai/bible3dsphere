import { useEffect, useState } from 'react'
import { fetchReadingProgress, markChapterRead } from './api'

const BOOKS = [
  { name: '创世记', abbr: '创', chapters: 50, testament: 'OT' },
  { name: '出埃及记', abbr: '出', chapters: 40, testament: 'OT' },
  { name: '利未记', abbr: '利', chapters: 27, testament: 'OT' },
  { name: '民数记', abbr: '民', chapters: 36, testament: 'OT' },
  { name: '申命记', abbr: '申', chapters: 34, testament: 'OT' },
  { name: '约书亚记', abbr: '书', chapters: 24, testament: 'OT' },
  { name: '士师记', abbr: '士', chapters: 21, testament: 'OT' },
  { name: '路得记', abbr: '得', chapters: 4, testament: 'OT' },
  { name: '撒母耳记上', abbr: '撒上', chapters: 31, testament: 'OT' },
  { name: '撒母耳记下', abbr: '撒下', chapters: 24, testament: 'OT' },
  { name: '列王纪上', abbr: '王上', chapters: 22, testament: 'OT' },
  { name: '列王纪下', abbr: '王下', chapters: 25, testament: 'OT' },
  { name: '诗篇', abbr: '诗', chapters: 150, testament: 'OT' },
  { name: '箴言', abbr: '箴', chapters: 31, testament: 'OT' },
  { name: '传道书', abbr: '传', chapters: 12, testament: 'OT' },
  { name: '以赛亚书', abbr: '赛', chapters: 66, testament: 'OT' },
  { name: '耶利米书', abbr: '耶', chapters: 52, testament: 'OT' },
  { name: '以西结书', abbr: '结', chapters: 48, testament: 'OT' },
  { name: '但以理书', abbr: '但', chapters: 12, testament: 'OT' },
  { name: '马太福音', abbr: '太', chapters: 28, testament: 'NT' },
  { name: '马可福音', abbr: '可', chapters: 16, testament: 'NT' },
  { name: '路加福音', abbr: '路', chapters: 24, testament: 'NT' },
  { name: '约翰福音', abbr: '约', chapters: 21, testament: 'NT' },
  { name: '使徒行传', abbr: '徒', chapters: 28, testament: 'NT' },
  { name: '罗马书', abbr: '罗', chapters: 16, testament: 'NT' },
  { name: '哥林多前书', abbr: '林前', chapters: 16, testament: 'NT' },
  { name: '哥林多后书', abbr: '林后', chapters: 13, testament: 'NT' },
  { name: '加拉太书', abbr: '加', chapters: 6, testament: 'NT' },
  { name: '以弗所书', abbr: '弗', chapters: 6, testament: 'NT' },
  { name: '腓立比书', abbr: '腓', chapters: 4, testament: 'NT' },
  { name: '歌罗西书', abbr: '西', chapters: 4, testament: 'NT' },
  { name: '帖撒罗尼迦前书', abbr: '帖前', chapters: 5, testament: 'NT' },
  { name: '帖撒罗尼迦后书', abbr: '帖后', chapters: 3, testament: 'NT' },
  { name: '提摩太前书', abbr: '提前', chapters: 6, testament: 'NT' },
  { name: '提摩太后书', abbr: '提后', chapters: 4, testament: 'NT' },
  { name: '提多书', abbr: '多', chapters: 3, testament: 'NT' },
  { name: '腓利门书', abbr: '门', chapters: 1, testament: 'NT' },
  { name: '希伯来书', abbr: '来', chapters: 13, testament: 'NT' },
  { name: '雅各书', abbr: '雅', chapters: 5, testament: 'NT' },
  { name: '彼得前书', abbr: '彼前', chapters: 5, testament: 'NT' },
  { name: '彼得后书', abbr: '彼后', chapters: 3, testament: 'NT' },
  { name: '约翰一书', abbr: '约一', chapters: 5, testament: 'NT' },
  { name: '约翰二书', abbr: '约二', chapters: 1, testament: 'NT' },
  { name: '约翰三书', abbr: '约三', chapters: 1, testament: 'NT' },
  { name: '犹大书', abbr: '犹', chapters: 1, testament: 'NT' },
  { name: '启示录', abbr: '启', chapters: 22, testament: 'NT' },
]

const TOTAL_CHAPTERS = BOOKS.reduce((s, b) => s + b.chapters, 0)

export default function BibleReadingPage({ user, token, onBack }) {
  const [progress, setProgress] = useState({ items: [], by_book: {} })
  const [loading, setLoading] = useState(true)
  const [selectedBook, setSelectedBook] = useState(null)
  const [highlight, setHighlight] = useState('')
  const [markingChapter, setMarkingChapter] = useState(null)
  const [completedBook, setCompletedBook] = useState(null)
  const [tab, setTab] = useState('NT') // 'OT' | 'NT'

  useEffect(() => {
    if (!user) return
    fetchReadingProgress(token).then(p => { setProgress(p); setLoading(false) }).catch(() => setLoading(false))
  }, [user, token])

  const totalDone = Object.values(progress.by_book).reduce((s, chs) => s + chs.length, 0)
  const pct = Math.round((totalDone / TOTAL_CHAPTERS) * 100)

  async function handleMark(book, chapter) {
    if (!user) return
    setMarkingChapter(`${book}${chapter}`)
    try {
      const result = await markChapterRead(book, chapter, highlight, token)
      const updated = await fetchReadingProgress(token)
      setProgress(updated)
      setHighlight('')
      if (result.book_completed) {
        setCompletedBook(book)
        setTimeout(() => setCompletedBook(null), 4000)
      }
    } catch (e) { } finally {
      setMarkingChapter(null)
    }
  }

  const books = BOOKS.filter(b => b.testament === tab)

  return (
    <div className="pw-page">
      <header className="pw-header">
        <button className="checkin-back-btn" onClick={onBack}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
        <div className="pw-header-center">
          <div className="pw-title">📖 圣经通读</div>
          <div className="pw-subtitle">{totalDone} / {TOTAL_CHAPTERS} 章 · {pct}%</div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {[['NT', '新约'], ['OT', '旧约']].map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} style={{ fontSize: 11, padding: '4px 10px', borderRadius: 8, border: 'none', background: tab === k ? 'rgba(88,86,214,0.4)' : 'rgba(255,255,255,0.1)', color: '#fff', cursor: 'pointer' }}>{l}</button>
          ))}
        </div>
      </header>

      {completedBook && (
        <div style={{ background: 'linear-gradient(135deg,#ffd700,#ff9500)', padding: '12px', textAlign: 'center', fontSize: 14, fontWeight: 700, color: '#000' }}>
          🎉 你读完了整卷《{completedBook}》！
        </div>
      )}

      <div style={{ padding: '16px' }}>
        {/* Overall progress bar */}
        <div style={{ marginBottom: 20 }}>
          <div style={{ height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#5856d6,#007aff)', transition: 'width .4s', borderRadius: 4 }} />
          </div>
          <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 4, textAlign: 'right' }}>全本圣经 {pct}% 已读</div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
        ) : selectedBook ? (
          /* Chapter grid for selected book */
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <button onClick={() => { setSelectedBook(null); setHighlight('') }} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8, color: '#fff', padding: '6px 14px', cursor: 'pointer', fontSize: 13 }}>← 返回</button>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>{selectedBook.name}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>
                  {(progress.by_book[selectedBook.name] || []).length} / {selectedBook.chapters} 章已读
                </div>
              </div>
            </div>

            {/* Highlight input */}
            <div style={{ marginBottom: 16 }}>
              <input
                value={highlight}
                onChange={e => setHighlight(e.target.value)}
                placeholder="可选：记录遇见神的话（标记章节时保存）"
                style={{ width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.06)', color: '#fff', fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(48px, 1fr))', gap: 8 }}>
              {Array.from({ length: selectedBook.chapters }, (_, i) => i + 1).map(ch => {
                const done = (progress.by_book[selectedBook.name] || []).includes(ch)
                const marking = markingChapter === `${selectedBook.name}${ch}`
                return (
                  <button key={ch} onClick={() => !done && handleMark(selectedBook.name, ch)} disabled={done || !!markingChapter}
                    style={{
                      height: 44, borderRadius: 8, border: done ? 'none' : '1px solid rgba(255,255,255,0.15)',
                      background: done ? 'linear-gradient(135deg,#007aff,#5856d6)' : marking ? 'rgba(0,122,255,0.3)' : 'rgba(255,255,255,0.06)',
                      color: done ? '#fff' : 'rgba(255,255,255,0.6)', fontSize: 13, fontWeight: done ? 700 : 400,
                      cursor: done ? 'default' : 'pointer',
                    }}>
                    {marking ? '...' : ch}
                  </button>
                )
              })}
            </div>
          </div>
        ) : (
          /* Book list */
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 10 }}>
            {books.map(book => {
              const done = (progress.by_book[book.name] || []).length
              const pctBook = Math.round((done / book.chapters) * 100)
              const complete = done >= book.chapters
              return (
                <div key={book.name} onClick={() => setSelectedBook(book)}
                  style={{
                    background: complete ? 'linear-gradient(135deg,rgba(0,122,255,0.2),rgba(88,86,214,0.15))' : 'rgba(255,255,255,0.05)',
                    border: complete ? '1px solid rgba(0,122,255,0.35)' : '1px solid rgba(255,255,255,0.09)',
                    borderRadius: 12, padding: '14px 12px', cursor: 'pointer',
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 14, fontWeight: 600, color: '#fff' }}>{book.name}</span>
                    {complete && <span style={{ fontSize: 12 }}>✅</span>}
                  </div>
                  <div style={{ height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginBottom: 4 }}>
                    <div style={{ height: '100%', width: `${pctBook}%`, background: complete ? '#007aff' : '#5856d6', borderRadius: 2 }} />
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{done}/{book.chapters} 章</div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
