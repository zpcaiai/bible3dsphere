/**
 * SpiritualBooksPage — 属灵书籍 书库
 *
 * 灵修 tab 下的「属灵书籍」子页：一个可扩展的书库。
 * - 第一本书《晨恩日新》复用 DailyDevotionPage（已有全文 + 逐段语音朗读）。
 * - 以后新增的书可作为 PDF 放在  public/book/<文件名>.pdf ，在下面 BOOKS 里加一条即可：
 *     · kind:'pdf'  → 显示 PDF 阅读器 + 下载；
 *     · 若同时提供 chapters（文字），则也显示文字 + TTS 语音朗读。
 */
import { useState, useRef, useEffect, lazy, Suspense } from 'react'
import { TTSFullBar, TTSButton } from './useGlobalAudio.jsx'
import DailyDevotionPage from './DailyDevotionPage.jsx'
import { API_BASE } from './api.js'
import { getToken } from './auth.js'

// ── 书库（可扩展）──────────────────────────────────────────────────────────────
export const BOOKS = [
  {
    id: 'daily',
    title: '晨恩日新',
    subtitle: '福音灵修日引 · 全年 365 篇',
    author: '保罗·区普（Paul David Tripp）',
    emoji: '🌅',
    color: '#34c759',
    kind: 'epub', epub: '/book/daily.epub',   // 全文 EPUB；日历版仍在「灵修」tab(DailyDevotionPage)
    blurb: '保罗·区普的福音灵修日引，全年 365 篇，以基督的福音浇灌每个清晨。可在应用内翻页阅读全文并逐页语音朗读。（按日历逐日阅读的版本在「灵修」tab。）',
  },
  { id: 'pilgrim', title: '天路历程', subtitle: '基督徒的属灵旅程', author: '约翰·班扬（John Bunyan, 1678）', emoji: '🧭', color: '#5ac8fa', kind: 'epub', epub: '/book/pilgrim.epub', blurb: '仅次于圣经流传最广的属灵寓言：背负罪担的「基督徒」逃离将亡城、奔向天城的旅程。可在应用内翻页阅读原著全文，并逐页语音朗读。' },
  { id: 'imitation', title: '效法基督', subtitle: '内在生命与谦卑舍己', author: '托马斯·肯培（Thomas à Kempis, 约15世纪）', emoji: '🕊️', color: '#c084fc', kind: 'epub', epub: '/book/imitation.epub', blurb: '仅次于圣经流传最广的灵修经典，四卷劝人离弃虚浮、注重内在生命、谦卑效法基督。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'owen-mortif', title: '治死信徒身上的罪', subtitle: '靠圣灵天天治死罪', author: '约翰·欧文（John Owen, Mortification of Sin）', emoji: '⚔️', color: '#f97316', kind: 'epub', epub: '/book/owen-mortif.epub', blurb: '欧文论成圣最实际的一本书——「你若不天天治死罪，罪必天天害你」。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'baxter-rest', title: '圣徒永恒的安息', subtitle: '默想天家，以永恒坚固今生', author: '理查德·巴克斯特（Richard Baxter, The Saints’ Everlasting Rest）', emoji: '🌅', color: '#34d399', kind: 'epub', epub: '/book/baxter-rest.epub', blurb: '巴克斯特在病重将死时写成的默想巨著，引导信徒操练默想天家的永恒安息。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'law-seriouscall', title: '敬虔与圣洁生活的严肃呼召', subtitle: '让信仰贯穿全部的生活', author: '威廉·罗（William Law, A Serious Call to a Devout and Holy Life）', emoji: '📯', color: '#60a5fa', kind: 'epub', epub: '/book/law-seriouscall.epub', blurb: '威廉·罗向「挂名的」基督徒发出的严肃呼召，深深影响了卫斯理等人。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'presence', title: '与神同在', subtitle: '在日常中时刻亲近神', author: '劳伦斯弟兄（Brother Lawrence）', emoji: '🙏', color: '#34c759', kind: 'epub', epub: '/book/presence.epub', blurb: '修道院厨役劳伦斯弟兄的谈话与书信，教人在最平凡的日常中时刻操练与神同在。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'purpose', title: '标杆人生', subtitle: '明白神所定的人生目的', author: '瑞克·华伦（Rick Warren, The Purpose Driven Life）', emoji: '🎯', color: '#06b6d4', kind: 'epub', epub: '/book/purpose.epub', blurb: '以四十天带你思考「我为什么活着」，发现并活出神所定的五个人生目的。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'mere', title: '返璞归真', subtitle: '理性说明信仰，也滋养心灵', author: 'C.S. 路易斯（C.S. Lewis, Mere Christianity）', emoji: '💡', color: '#818cf8', kind: 'epub', epub: '/book/mere.epub', blurb: '路易斯由广播讲稿整理，向怀疑者理性阐明信仰根基的通俗护教经典。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'whitney', title: '操练敬虔（基督教要义每日灵修）', subtitle: '每日操练亲近神的属灵生活', author: '吕沛渊', emoji: '🏋️', color: '#fb7185', kind: 'epub', epub: '/book/whitney.epub', blurb: '以《基督教要义》为线索的每日灵修，逐日操练读经、祷告与亲近神的属灵生活。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'screwtape', title: '魔鬼家书', subtitle: '从反面视角识破试探', author: 'C.S. 路易斯（C.S. Lewis, The Screwtape Letters）', emoji: '😈', color: '#ef4444', kind: 'epub', epub: '/book/screwtape.epub', blurb: '路易斯以资深魔鬼写给小魔鬼的书信，从反面揭露人受试探、偏离神的种种诡计。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'depression', title: '灵性低潮', subtitle: '灵里消沉的成因与医治', author: '钟马田（Martyn Lloyd-Jones, Spiritual Depression）', emoji: '🌧️', color: '#94a3b8', kind: 'epub', epub: '/book/depression.epub', blurb: '钟马田面对基督徒灵里沮丧消沉的讲道集，逐一诊断成因、以福音给出医治。可在应用内翻页阅读全文并逐页语音朗读。' },
  {
    id: 'bruised', title: '压伤的芦苇', subtitle: '温柔安慰受伤将残的灵魂', author: '理查德·西布斯（Richard Sibbes, The Bruised Reed）',
    emoji: '🌾', color: '#a3e635', kind: 'epub', epub: '/book/bruised-reeds.epub',
    blurb: '清教徒西布斯（人称「天上的医生」）的安慰经典，本于「压伤的芦苇，他不折断；将残的灯火，他不吹灭」（赛42:3），以极温柔的笔触安慰软弱、将残、几乎要放弃的灵魂。可在应用内翻页阅读全文并逐页语音朗读。',
  },
  { id: 'seeking', title: '在清真寺寻找，十字架下寻见', subtitle: '一位穆斯林青年寻见基督的真实历程', author: '纳比·库雷希（Nabeel Qureshi, Seeking Allah, Finding Jesus）', emoji: '🕌', color: '#22d3ee', kind: 'epub', epub: '/book/seeking-allah.epub', blurb: '虔诚的穆斯林青年库雷希，历经多年理性查考与内心挣扎，最终在十字架下寻见耶稣的自传见证。可在应用内翻页阅读全文并逐页语音朗读。' },
  { id: 'kingscross', title: '十架君王', subtitle: '理解耶稣的生与死', author: '提摩太·凯勒（Timothy Keller, King’s Cross）', emoji: '👑', color: '#fbbf24', kind: 'epub', epub: '/book/kingscross.epub', blurb: '凯勒以马可福音默想耶稣生平，展现这位「钉十架的君王」如何重新定义王权、得胜与拯救。可在应用内翻页阅读全文并逐页语音朗读。' },
]

// ── 一本 PDF 书的阅读器（PDF + 可选文字 + TTS）────────────────────────────────
function PdfBookReader({ book, onBack }) {
  const [chap, setChap] = useState(0)
  const chapters = Array.isArray(book.chapters) ? book.chapters : []
  const cur = chapters[chap]
  return (
    <div style={S.page}>
      <header style={S.header}>
        <button onClick={onBack} style={S.back} aria-label="返回书库">‹ 返回书库</button>
        <div style={{ flex: 1 }}>
          <div style={S.hTitle}>{book.emoji} {book.title}</div>
          <div style={S.hSub}>{book.author}</div>
        </div>
        {book.pdf && (
          <a href={book.pdf} target="_blank" rel="noopener noreferrer" style={S.pdfBtn}>📄 PDF</a>
        )}
      </header>

      {/* 文字 + 语音（若提供 chapters）*/}
      {chapters.length > 0 ? (
        <div style={{ padding: '0 16px 40px' }}>
          {chapters.length > 1 && (
            <div style={S.chapRow}>
              {chapters.map((c, i) => (
                <button key={i} onClick={() => setChap(i)}
                  style={{ ...S.chapBtn, ...(i === chap ? S.chapBtnOn(book.color) : {}) }}>
                  {c.title || `第${i + 1}章`}
                </button>
              ))}
            </div>
          )}
          <TTSFullBar buildText={() => `${cur?.title || book.title}。${cur?.text || ''}`} label="全文朗读" />
          <div style={S.chapTitle}>{cur?.title}</div>
          <div style={S.bodyText}>{cur?.text}</div>
        </div>
      ) : book.pdf ? (
        // 只有 PDF、没有文字：内嵌 PDF 阅读器
        <div style={{ flex: 1, minHeight: 0, padding: '8px 12px 16px' }}>
          <iframe title={book.title} src={book.pdf}
            style={{ width: '100%', height: '78vh', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, background: '#fff' }} />
          <div style={{ textAlign: 'center', marginTop: 10 }}>
            <a href={book.pdf} target="_blank" rel="noopener noreferrer" style={S.pdfBtnWide}>在新窗口打开 / 下载 PDF</a>
          </div>
        </div>
      ) : (
        <div style={{ padding: 40, textAlign: 'center', color: 'rgba(255,255,255,0.5)' }}>
          这本书的内容还未添加。把 PDF 放到 <code>public/book/</code> 并在 BOOKS 里配置即可。
        </div>
      )}
    </div>
  )
}

// ── 运行时从 CDN 加载 epub.js（含 JSZip），避免改动 npm 依赖 ─────────────────────
// 多 CDN 回退：cdnjs 的 epub.js 0.3.93 路径已 404，改用 jsdelivr 为主、unpkg/cdnjs 兜底
const JSZIP_SRCS = [
  'https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js',
  'https://unpkg.com/jszip@3.10.1/dist/jszip.min.js',
]
const EPUBJS_SRCS = [
  'https://cdn.jsdelivr.net/npm/epubjs@0.3.93/dist/epub.min.js',
  'https://unpkg.com/epubjs@0.3.93/dist/epub.min.js',
]
let _epubLibPromise = null
function loadEpubLib() {
  if (window.ePub) return Promise.resolve(window.ePub)
  if (_epubLibPromise) return _epubLibPromise
  const inject = (src) => new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src; s.async = true
    s.onload = resolve; s.onerror = () => reject(new Error('加载失败: ' + src))
    document.head.appendChild(s)
  })
  const injectAny = (srcs) => srcs.reduce((p, src) => p.catch(() => inject(src)), Promise.reject(new Error('no source')))
  _epubLibPromise = injectAny(JSZIP_SRCS)
    .then(() => injectAny(EPUBJS_SRCS))
    .then(() => window.ePub)
    .catch((err) => {
      _epubLibPromise = null // 失败不缓存，下次打开可重试
      throw err
    })
  return _epubLibPromise
}

// ── EPUB 全文阅读器（重排 + 翻页 + 逐页语音）──────────────────────────────────
function EpubReader({ book, onBack }) {
  const viewerRef = useRef(null)
  const renditionRef = useRef(null)
  const [status, setStatus] = useState('loading') // loading | ready | error
  const [srcUrl, setSrcUrl] = useState('')
  const [pageText, setPageText] = useState('')
  const [progress, setProgress] = useState(0)
  const bookRef = useRef(null)
  const [locReady, setLocReady] = useState(false)   // 全书位置索引就绪(滚动条可用)
  const seekTimer = useRef(null)
  const touchRef = useRef({ x: 0, y: 0 })

  useEffect(() => {
    let destroyed = false
    let rendition = null
    loadEpubLib()
      .then((ePub) => {
        if (destroyed || !viewerRef.current) return
        // EPUB 全文托管在 R2 公开目录 cdn.holiness.uk/ebook/（不入 git）。
        // 默认始终从该 CDN 加载；可用构建期变量 VITE_BOOK_BASE 覆盖（如本地开发指向 /book 或别的域名）。
        const envBase = (import.meta?.env?.VITE_BOOK_BASE || '').replace(/\/+$/, '')
        const base = envBase || 'https://cdn.holiness.uk/ebook'
        const file = (book.epub || '').replace(/^\/book\//, '')
        const src = /^https?:/i.test(book.epub) ? book.epub : `${base}/${file}`
        setSrcUrl(src)
        const bk = ePub(src)
        bookRef.current = bk
        rendition = bk.renderTo(viewerRef.current, {
          width: '100%', height: '100%', flow: 'paginated', spread: 'none',
        })
        renditionRef.current = rendition
        // 暗色主题
        rendition.themes.default({
          body: { background: '#0d1117', color: '#dfe6f0', 'line-height': '1.9',
            'font-size': '17px', padding: '0 6px' },
          a: { color: '#5ac8fa' }, p: { margin: '0.8em 0' },
        })
        rendition.display().then(() => { if (!destroyed) setStatus('ready') })
        // 翻页后取当页文字（供朗读）+ 进度
        rendition.on('relocated', (loc) => {
          if (loc?.start?.percentage != null) setProgress(Math.round(loc.start.percentage * 100))
          try {
            const cs = rendition.getContents()
            const txt = cs && cs[0] && cs[0].content ? (cs[0].content.innerText || cs[0].content.textContent || '') : ''
            setPageText((txt || '').trim().slice(0, 6000))
          } catch { /* ignore */ }
        })
        // 左右滑动翻页（iframe 内的 touch 事件由 epub.js 转发出来）
        let _tx = 0, _ty = 0
        rendition.on('touchstart', (ev) => {
          const t = ev.changedTouches && ev.changedTouches[0]
          if (t) { _tx = t.screenX; _ty = t.screenY }
        })
        rendition.on('touchend', (ev) => {
          const t = ev.changedTouches && ev.changedTouches[0]
          if (!t) return
          const dx = t.screenX - _tx
          const dy = Math.abs(t.screenY - _ty)
          if (Math.abs(dx) > 50 && dy < 80) {
            if (dx < 0) rendition.next(); else rendition.prev()
          }
        })
        // 生成全书位置索引（供滚动条按百分比跳转；大书需数秒，期间滚动条置灰）
        bk.ready
          .then(() => bk.locations.generate(800))
          .then(() => { if (!destroyed) setLocReady(true) })
          .catch(() => { /* 索引失败仅禁用滚动条 */ })
        bk.ready.catch(() => { if (!destroyed) setStatus('error') })
      })
      .catch(() => { if (!destroyed) setStatus('error') })
    return () => {
      destroyed = true
      if (seekTimer.current) clearTimeout(seekTimer.current)
      bookRef.current = null
      try { rendition && rendition.destroy() } catch { /* ignore */ }
    }
  }, [book.epub])

  const prev = () => renditionRef.current && renditionRef.current.prev()
  const next = () => renditionRef.current && renditionRef.current.next()

  // 滚动条跳转（防抖，松手 150ms 后定位）
  const seekTo = (pct) => {
    setProgress(Math.round(pct))
    if (seekTimer.current) clearTimeout(seekTimer.current)
    seekTimer.current = setTimeout(() => {
      try {
        const bk = bookRef.current
        const r = renditionRef.current
        if (bk && r && bk.locations && bk.locations.length()) {
          const cfi = bk.locations.cfiFromPercentage(pct / 100)
          if (cfi) r.display(cfi)
        }
      } catch { /* ignore */ }
    }, 150)
  }
  // 外层容器手势（覆盖 iframe 外边距区域）
  const onAreaTouchStart = (e) => {
    const t = e.changedTouches && e.changedTouches[0]
    if (t) touchRef.current = { x: t.screenX, y: t.screenY }
  }
  const onAreaTouchEnd = (e) => {
    const t = e.changedTouches && e.changedTouches[0]
    if (!t) return
    const dx = t.screenX - touchRef.current.x
    const dy = Math.abs(t.screenY - touchRef.current.y)
    if (Math.abs(dx) > 50 && dy < 80) { if (dx < 0) next(); else prev() }
  }

  return (
    <div style={{ ...S.page, height: '100%' }}>
      <header style={S.header}>
        <button onClick={onBack} style={S.back} aria-label="返回书库">‹ 返回书库</button>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ ...S.hTitle, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{book.emoji} {book.title}</div>
          <div style={S.hSub}>{book.author}{progress ? ` · ${progress}%` : ''}</div>
        </div>
        {pageText && <TTSButton text={pageText} />}
      </header>

      {status === 'error' ? (
        <div style={{ padding: 32, textAlign: 'center', color: 'rgba(255,255,255,0.6)', lineHeight: 1.9 }}>
          <div style={{ fontSize: 40, marginBottom: 10 }}>📕</div>
          <div style={{ fontWeight: 600, color: '#fff', marginBottom: 8 }}>暂时无法加载《{book.title}》</div>
          <div style={{ fontSize: 13 }}>
            已尝试加载：<br /><code style={{ wordBreak: 'break-all' }}>{srcUrl || book.epub}</code>
          </div>
          <div style={{ fontSize: 12.5, color: 'rgba(255,255,255,0.45)', marginTop: 10 }}>
            请确认该 EPUB 已上传到 <code>cdn.holiness.uk/ebook/</code>，且 CDN 已开启跨域访问（CORS）。
          </div>
          <button onClick={onBack} style={{ ...S.pdfBtnWide, marginTop: 18 }}>‹ 返回书库</button>
        </div>
      ) : (
        <>
          <div style={{ flex: 1, minHeight: 0, position: 'relative', margin: '0 6px' }} onTouchStart={onAreaTouchStart} onTouchEnd={onAreaTouchEnd}>
            <div ref={viewerRef} style={{ position: 'absolute', inset: 0 }} />
            {status === 'loading' && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.5)' }}>载入中…</div>
            )}
          </div>
          {/* 进度滚动条：拖动按百分比跳转 */}
          <div style={{ padding: '8px 16px 0', flexShrink: 0 }}>
            <input
              type="range" min={0} max={100} step={0.5}
              value={progress}
              disabled={!locReady}
              onChange={(e) => seekTo(parseFloat(e.target.value))}
              style={{ width: '100%', accentColor: '#5ac8fa', opacity: locReady ? 1 : 0.4 }}
              aria-label="阅读进度"
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>
              <span>{progress}%</span>
              <span>{locReady ? '拖动跳转 · 左右滑动翻页' : '正在建立页码索引…'}</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, padding: '10px 16px 16px', flexShrink: 0 }}>
            <button onClick={prev} style={S.navBtn}>‹ 上一页</button>
            <button onClick={next} style={S.navBtn}>下一页 ›</button>
          </div>
        </>
      )}
    </div>
  )
}

// ── 书库主组件 ────────────────────────────────────────────────────────────────
const MARK_S = {
  row: { display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  btn: { fontSize: 11, padding: '3px 10px', borderRadius: 14, cursor: 'pointer',
    background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.14)',
    color: 'rgba(255,255,255,0.6)', userSelect: 'none' },
  on: { background: 'rgba(52,199,89,0.18)', border: '1px solid rgba(52,199,89,0.5)', color: '#34c759' },
  stat: { fontSize: 11, color: 'rgba(255,214,10,0.8)' },
}

export default function SpiritualBooksPage({ onBack }) {
  const [openId, setOpenId] = useState(null)
  const [stats, setStats] = useState({})
  const [marks, setMarks] = useState({})
  const token = getToken()
  const book = BOOKS.find(b => b.id === openId)

  useEffect(() => {
    fetch(`${API_BASE}/books/stats`).then(r => r.json()).then(d => setStats(d.stats || {})).catch(() => {})
    if (token) {
      fetch(`${API_BASE}/books/marks`, { headers: { Authorization: `Bearer ${token}` } })
        .then(r => (r.ok ? r.json() : { marks: {} })).then(d => setMarks(d.marks || {})).catch(() => {})
    }
  }, [])

  // 分享深链：/?share=book:<id>
  useEffect(() => {
    const dl = window.__deepLink
    if (dl && dl.kind === 'book' && BOOKS.some(b => b.id === dl.id)) {
      setOpenId(dl.id); window.__deepLink = null
    }
  }, [])

  const saveMark = (bookId, patch) => {
    if (!token) { window.showToast && window.showToast('登录后可标记想读/已读和评分', 'info'); return }
    const cur = marks[bookId] || {}
    const next = {
      status: patch.status !== undefined ? patch.status : (cur.status || ''),
      rating: patch.rating !== undefined ? patch.rating : (cur.rating || 0),
    }
    setMarks(m => ({ ...m, [bookId]: { status: next.status || null, rating: next.rating || null } }))
    fetch(`${API_BASE}/books/mark`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ book_id: bookId, status: next.status || '', rating: next.rating || 0 }),
    }).catch(() => {})
  }

  const shareBook = (b) => {
    const url = `${window.location.origin}/?share=book:${b.id}`
    const data = { title: `《${b.title}》`, text: `《${b.title}》— ${b.author}，在属灵星球免费在线阅读`, url }
    if (navigator.share) { navigator.share(data).catch(() => {}) }
    else if (navigator.clipboard) {
      navigator.clipboard.writeText(`${data.text} ${url}`)
      window.showToast && window.showToast('分享链接已复制', 'success')
    }
  }

  if (book) {
    if (book.kind === 'devotion') {
      // 晨恩日新：复用现有日历阅读器（已含文字 + 整篇/逐段语音）
      return <DailyDevotionPage onBack={() => setOpenId(null)} />
    }
    if (book.kind === 'epub') {
      // EPUB（苹果电子书）全文阅读器：可重排、翻页、逐页语音朗读
      return <EpubReader book={book} onBack={() => setOpenId(null)} />
    }
    return <PdfBookReader book={book} onBack={() => setOpenId(null)} />
  }

  return (
    <div style={S.page}>
      <header style={S.header}>
        {onBack && <button onClick={onBack} style={S.back} aria-label="返回">‹</button>}
        <div style={{ flex: 1 }}>
          <div style={S.hTitle}>📚 属灵书籍</div>
          <div style={S.hSub}>点开一本书，阅读全文并可语音朗读</div>
        </div>
      </header>

      <div style={S.grid}>
        {BOOKS.map(b => (
          <div key={b.id} role="button" tabIndex={0} onClick={() => setOpenId(b.id)}
            style={{ ...S.card, borderColor: b.color + '55', cursor: 'pointer' }}>
            <div style={{ ...S.cover, background: `linear-gradient(150deg, ${b.color}33, ${b.color}11)`, borderColor: b.color + '44' }}>
              <span style={{ fontSize: 40 }}>{b.emoji}</span>
            </div>
            <div style={S.cardBody}>
              <div style={{ ...S.cardTitle, color: b.color }}>{b.title}</div>
              {b.subtitle && <div style={S.cardSub}>{b.subtitle}</div>}
              <div style={S.cardAuthor}>{b.author}</div>
              {b.blurb && <div style={S.cardBlurb}>{b.blurb}</div>}
              <div style={S.cardCta}>
                <span style={{ color: b.color }}>📖 阅读</span>
                <span style={{ color: b.color }}>🔊 朗读</span>
                {b.pdf && <span style={{ color: 'rgba(255,255,255,0.45)' }}>📄 PDF</span>}
              </div>
              {/* 评分 / 想读 / 已读 / 分享 */}
              <div style={MARK_S.row} onClick={e => e.stopPropagation()}>
                <span style={{ display: 'flex', gap: 1 }}>
                  {[1, 2, 3, 4, 5].map(n => (
                    <span key={n}
                      onClick={() => saveMark(b.id, { rating: (marks[b.id]?.rating === n ? 0 : n) })}
                      style={{ cursor: 'pointer', fontSize: 13,
                        filter: (marks[b.id]?.rating || 0) >= n ? 'none' : 'grayscale(1)',
                        opacity: (marks[b.id]?.rating || 0) >= n ? 1 : 0.35 }}>⭐</span>
                  ))}
                </span>
                {stats[b.id]?.rating_count > 0 && (
                  <span style={MARK_S.stat}>{stats[b.id].avg_rating}分·{stats[b.id].rating_count}人</span>
                )}
                <span onClick={() => saveMark(b.id, { status: marks[b.id]?.status === 'want' ? '' : 'want' })}
                  style={{ ...MARK_S.btn, ...(marks[b.id]?.status === 'want' ? MARK_S.on : {}) }}>
                  🔖 想读{stats[b.id]?.want ? ` ${stats[b.id].want}` : ''}
                </span>
                <span onClick={() => saveMark(b.id, { status: marks[b.id]?.status === 'read' ? '' : 'read' })}
                  style={{ ...MARK_S.btn, ...(marks[b.id]?.status === 'read' ? MARK_S.on : {}) }}>
                  ✅ 已读{stats[b.id]?.read_cnt ? ` ${stats[b.id].read_cnt}` : ''}
                </span>
                <span onClick={() => shareBook(b)} style={MARK_S.btn}>↗ 分享</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={S.note}>
        想加新书？把 PDF 放进 <code>emotion-sphere-ui/public/book/</code>，在 <code>SpiritualBooksPage.jsx</code> 的 BOOKS 里加一条即可（可只放 PDF，也可附文字以支持语音朗读）。
      </div>
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S = {
  page: {
    position: 'relative', minHeight: '100%', display: 'flex', flexDirection: 'column',
    background: 'linear-gradient(160deg,#0d1117 0%,#0a1628 60%,#060d1f 100%)',
    color: '#fff', fontFamily: '-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
    overflowY: 'auto', paddingBottom: 'calc(env(safe-area-inset-bottom) + 88px)',  // 避开底部 tab 栏
  },
  header: { display: 'flex', alignItems: 'center', gap: 10, padding: '16px 16px 12px', position: 'sticky', top: 0,
    background: 'rgba(13,17,23,0.92)', backdropFilter: 'blur(8px)', zIndex: 5, borderBottom: '1px solid rgba(255,255,255,0.06)' },
  back: { background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8, color: '#fff', padding: '6px 12px', cursor: 'pointer', fontSize: 16 },
  hTitle: { fontSize: 19, fontWeight: 700 },
  hSub: { fontSize: 12, color: 'rgba(255,255,255,0.5)', marginTop: 2 },
  pdfBtn: { background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 8, color: '#fff', padding: '6px 10px', fontSize: 12, textDecoration: 'none' },
  pdfBtnWide: { display: 'inline-block', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 10, color: '#fff', padding: '9px 16px', fontSize: 13, textDecoration: 'none' },
  grid: { display: 'flex', flexDirection: 'column', gap: 14, padding: '16px' },
  card: { display: 'flex', gap: 14, textAlign: 'left', background: 'rgba(255,255,255,0.04)', border: '1px solid', borderRadius: 16, padding: 14, cursor: 'pointer', fontFamily: 'inherit' },
  cover: { width: 84, height: 110, flexShrink: 0, borderRadius: 10, border: '1px solid', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cardBody: { flex: 1, minWidth: 0 },
  cardTitle: { fontSize: 18, fontWeight: 700 },
  cardSub: { fontSize: 12.5, color: 'rgba(255,255,255,0.7)', marginTop: 3 },
  cardAuthor: { fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4 },
  cardBlurb: { fontSize: 12.5, color: 'rgba(255,255,255,0.6)', marginTop: 8, lineHeight: 1.6 },
  cardCta: { display: 'flex', gap: 14, marginTop: 10, fontSize: 13, fontWeight: 600 },
  note: { margin: '4px 16px 8px', padding: '10px 12px', fontSize: 11.5, lineHeight: 1.6, color: 'rgba(255,255,255,0.4)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 10 },
  chapRow: { display: 'flex', flexWrap: 'wrap', gap: 7, padding: '12px 0' },
  chapBtn: { padding: '6px 12px', fontSize: 13, color: 'rgba(255,255,255,0.6)', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 999, cursor: 'pointer' },
  chapBtnOn: (c) => ({ color: c, background: c + '22', borderColor: c + '66' }),
  chapTitle: { fontSize: 18, fontWeight: 700, margin: '6px 0 12px' },
  bodyText: { fontSize: 16, lineHeight: 2, color: 'rgba(255,255,255,0.9)', whiteSpace: 'pre-wrap' },
  navBtn: { flex: 1, padding: '11px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, color: '#fff', fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' },
}
