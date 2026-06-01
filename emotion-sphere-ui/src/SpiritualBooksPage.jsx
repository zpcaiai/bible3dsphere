/**
 * SpiritualBooksPage — 属灵书籍 书库
 *
 * 灵修 tab 下的「属灵书籍」子页：一个可扩展的书库。
 * - 第一本书《晨恩日新》复用 DailyDevotionPage（已有全文 + 逐段语音朗读）。
 * - 以后新增的书可作为 PDF 放在  public/book/<文件名>.pdf ，在下面 BOOKS 里加一条即可：
 *     · kind:'pdf'  → 显示 PDF 阅读器 + 下载；
 *     · 若同时提供 chapters（文字），则也显示文字 + TTS 语音朗读。
 */
import { useState, lazy, Suspense } from 'react'
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
    pdf: '/book/晨恩日新.pdf',   // 可选：把 PDF 放到 public/book/ 即可在书内「查看/下载 PDF」
    blurb: '按日历每天一篇的福音默想，以基督的福音浇灌每个清晨。点开即可阅读全文，并可整篇或逐段语音朗读。',
  },
  // —— 以后加书的范例（取消注释并放好 PDF / 文字即可）——
  // {
  //   id: 'pilgrim', title: '天路历程', subtitle: '基督徒的属灵旅程', author: '约翰·班扬（John Bunyan）',
  //   emoji: '🧭', color: '#5ac8fa', kind: 'pdf', pdf: '/book/天路历程.pdf',
  //   blurb: '以寓言描绘基督徒走天路的挣扎与得胜。',
  //   chapters: [ { title: '第一章', text: '……正文……' } ],  // 提供文字则可语音朗读
  // },
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

// ── 书库主组件 ────────────────────────────────────────────────────────────────
export default function SpiritualBooksPage({ onBack }) {
  const [openId, setOpenId] = useState(null)
  const book = BOOKS.find(b => b.id === openId)

  if (book) {
    if (book.kind === 'devotion') {
      // 晨恩日新：复用现有日历阅读器（已含文字 + 整篇/逐段语音）
      return <DailyDevotionPage onBack={() => setOpenId(null)} />
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
}
