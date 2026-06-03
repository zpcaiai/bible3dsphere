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

// ── 书库（可扩展）──────────────────────────────────────────────────────────────
export const BOOKS = [
  {
    id: 'daily',
    title: '晨恩日新',
    subtitle: '福音灵修日引 · 全年 365 篇',
    author: '保罗·区普（Paul David Tripp）',
    emoji: '🌅',
    color: '#34c759',
    kind: 'devotion',            // 复用 DailyDevotionPage（日历 + 文字 + 语音）
    blurb: '按日历每天一篇的福音默想，以基督的福音浇灌每个清晨。点开即可阅读全文，并可整篇或逐段语音朗读。',
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
    id: 'bruised', title: '压伤的芦苇（导读）', subtitle: '温柔安慰受伤将残的灵魂', author: '原著 理查德·西布斯（Richard Sibbes, The Bruised Reed）',
    emoji: '🌾', color: '#a3e635', kind: 'pdf', pdf: '/book/压伤的芦苇-导读.pdf',
    blurb: '本应用原创导读：清教徒西布斯以极温柔的笔触安慰软弱将残之人的安慰经典。可阅读、语音朗读、查看导读 PDF。',
    chapters: [
      { title: '关于这本书', text: '《压伤的芦苇》是清教徒西布斯（人称「天上的医生」）的安慰经典，根据「压伤的芦苇，他不折断；将残的灯火，他不吹灭」（赛42:3），以极温柔的笔触安慰软弱、将残、几乎要放弃的灵魂。' },
      { title: '核心信息', text: '对软弱的人，基督不是要压垮，而是扶持、医治、吹旺那将熄的火。纯正的真理可以包着最温柔的心肠——这是清教徒敬虔里最暖的一面。' },
      { title: '怎么读', text: '在你自己「将残」、或身边有人快撑不住时读，领受基督的温柔；也学他以慈心待软弱的人，而非以律法压垮人。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
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
        <button onClick={onBack} style={S.back} aria-label="返回书库">‹ 书库</button>
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
  _epubLibPromise = inject('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js')
    .then(() => inject('https://cdnjs.cloudflare.com/ajax/libs/epub.js/0.3.93/epub.min.js'))
    .then(() => window.ePub)
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

  useEffect(() => {
    let destroyed = false
    let rendition = null
    loadEpubLib()
      .then((ePub) => {
        if (destroyed || !viewerRef.current) return
        // EPUB 原著不入 git（91MB 级大文件）。线上默认从 R2(sabbath 桶 book/ 前缀)经 cdn.holiness.uk 加载；
        // 本地开发用 public/book/。可用构建期变量 VITE_BOOK_BASE 覆盖（如 https://<你的R2域名>/book）。
        const envBase = (import.meta?.env?.VITE_BOOK_BASE || '').replace(/\/+$/, '')
        const isLocalhost = typeof window !== 'undefined' && /^(localhost|127\.0\.0\.1)$/.test(window.location.hostname)
        const base = envBase || (isLocalhost ? '' : 'https://cdn.holiness.uk/ebook')
        const file = (book.epub || '').replace(/^\/book\//, '')
        const src = /^https?:/i.test(book.epub) ? book.epub : (base ? `${base}/${file}` : book.epub)
        setSrcUrl(src)
        const bk = ePub(src)
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
        bk.ready.catch(() => { if (!destroyed) setStatus('error') })
      })
      .catch(() => { if (!destroyed) setStatus('error') })
    return () => {
      destroyed = true
      try { rendition && rendition.destroy() } catch { /* ignore */ }
    }
  }, [book.epub])

  const prev = () => renditionRef.current && renditionRef.current.prev()
  const next = () => renditionRef.current && renditionRef.current.next()

  return (
    <div style={{ ...S.page, height: '100%' }}>
      <header style={S.header}>
        <button onClick={onBack} style={S.back} aria-label="返回书库">‹ 书库</button>
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
            请确认该 EPUB 已上传到 R2（sabbath 桶 <code>book/</code> 前缀），且 CDN 已开启跨域访问（CORS）。
          </div>
          <button onClick={onBack} style={{ ...S.pdfBtnWide, marginTop: 18 }}>‹ 返回书库</button>
        </div>
      ) : (
        <>
          <div style={{ flex: 1, minHeight: 0, position: 'relative', margin: '0 6px' }}>
            <div ref={viewerRef} style={{ position: 'absolute', inset: 0 }} />
            {status === 'loading' && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.5)' }}>载入中…</div>
            )}
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
export default function SpiritualBooksPage({ onBack }) {
  const [openId, setOpenId] = useState(null)
  const book = BOOKS.find(b => b.id === openId)

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
          <button key={b.id} onClick={() => setOpenId(b.id)} style={{ ...S.card, borderColor: b.color + '55' }}>
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
            </div>
          </button>
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
    overflowY: 'auto', paddingBottom: 24,
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
