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
  {
    id: 'pilgrim',
    title: '天路历程（导读）',
    subtitle: '基督徒的属灵旅程',
    author: '原著 约翰·班扬（John Bunyan, 1678）',
    emoji: '🧭',
    color: '#5ac8fa',
    kind: 'pdf',
    pdf: '/book/天路历程-导读.pdf',
    blurb: '本应用原创导读：介绍这部仅次于圣经流传最广的属灵寓言——其旅程、人物、主题与读法。可阅读、语音朗读、并查看导读 PDF。（原著全文 PDF 可自行放入 public/book/）',
    chapters: [
      { title: '关于这本书', text: '《天路历程》是约翰·班扬在十二年牢狱中写成的属灵寓言，被誉为英语世界仅次于圣经、流传最广的基督教经典。全书以「一个梦」的形式，讲述一位名叫「基督徒」的人，背负沉重的罪担、逃离「将亡城」，踏上天路、奔向「天城」的旅程。' },
      { title: '旅程中的地点与人物（皆有寓意）', text: '沿途的地名都是你属灵旅程会遇到的处境：灰心潭、窄门、十字架前重担脱落之处、艰难山、华美宫、屈辱谷、死荫幽谷、名利场、由巨人「绝望」把守的怀疑堡、欢喜山，直到最后渡过死河、进入天城。一路遇见传道者、帮助、世故先生、忠信、盼望等同伴与拦阻。' },
      { title: '主要属灵主题', text: '重生与悔改；罪担因十字架而脱落的释放；天路上的试炼、跌倒与重新起来；同伴同行的重要；恒忍到底；警惕世故与名利的诱惑；在怀疑与绝望中靠「盼望」站立。' },
      { title: '怎么读', text: '把自己代入「基督徒」：每到一处，就问「我现在走在天路的哪一段？」让每个地点照见你此刻的属灵光景。慢慢读、默想着读，重在被光照、被激励向前。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'imitation',
    title: '效法基督（导读）',
    subtitle: '内在生命与谦卑舍己',
    author: '原著 托马斯·肯培（Thomas à Kempis, 约15世纪）',
    emoji: '🕊️',
    color: '#c084fc',
    kind: 'pdf',
    pdf: '/book/效法基督-导读.pdf',
    blurb: '本应用原创导读：介绍这部仅次于圣经流传最广的灵修经典——四卷主题、核心精神与读法。可阅读、语音朗读、并查看导读 PDF。（原著全文 PDF 可自行放入 public/book/）',
    chapters: [
      { title: '关于这本书', text: '《效法基督》是托马斯·肯培约在十五世纪初写成的灵修经典，分为四卷，被誉为仅次于圣经、流传最广的灵修书之一。全书的主题只有一个：离弃世界的虚浮，注重内在的生命，以谦卑舍己的心单单效法基督。' },
      { title: '四卷的主题', text: '卷一·论属灵生活的劝勉：轻看世界的虚荣，追求谦卑、顺服与认识自己。卷二·论内在的生命：亲近基督、背起十字架、看顾内心。卷三·论内心的安慰：以基督与门徒对话的方式，讲述顺服、忍耐与在神里的平安。卷四·论圣餐：以敬畏感恩的心领受主的身体。' },
      { title: '核心精神', text: '内在胜于外在，谦卑胜于知识，行出来胜于只是知道。它一再提醒人：真正的智慧不在高言大智，而在效法基督的谦卑与舍己，以及一颗真实痛悔、单单亲近神的心。' },
      { title: '怎么读', text: '不必贪多，每天读一小段，安静默想，把读到的化为今天的一个顺服与亲近神的行动。重在「行」而非「知」。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'owen-spirit', title: '论圣灵（导读）', subtitle: '认识圣灵的位格与工作', author: '原著 约翰·欧文（John Owen, Pneumatologia）',
    emoji: '🕯️', color: '#fbbf24', kind: 'pdf', pdf: '/book/论圣灵-导读.pdf',
    blurb: '本应用原创导读：介绍欧文论圣灵之位格与工作的鸿篇巨著。可阅读、语音朗读、查看导读 PDF。（原著全文 PDF 可自行放入 public/book/）',
    chapters: [
      { title: '关于这本书', text: '《论圣灵》(Pneumatologia) 是清教徒神学巨擘约翰·欧文系统论述圣灵之位格与工作的鸿篇巨著，是英语世界论圣灵最深入、最丰厚的著作之一。' },
      { title: '主要内容', text: '全面阐述圣灵在创造、重生、成圣、赐恩、引导、安慰中的工作：祂如何叫死在罪中的人重生、如何在信徒里逐渐成圣、如何赐下各样恩赐并作得基业的凭据。' },
      { title: '核心信息', text: '圣灵不是一种「力量」，而是一位「神」——三一神的第三位格，亲自住在信徒里面、与我们同在、在我们里面动工。正确认识圣灵，敬拜与生活就有了根基。' },
      { title: '怎么读', text: '带着「认识这位与我同在的圣灵」的渴慕去读；读时常常祷告，求祂亲自光照、引导你进入真理。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'owen-mortif', title: '治死信徒身上的罪（导读）', subtitle: '靠圣灵天天治死罪', author: '原著 约翰·欧文（John Owen, Mortification of Sin）',
    emoji: '⚔️', color: '#f97316', kind: 'pdf', pdf: '/book/治死罪-导读.pdf',
    blurb: '本应用原创导读：欧文论成圣最实际的一本小书——「你若不天天治死罪，罪必天天害你」。可阅读、语音朗读、查看导读 PDF。',
    chapters: [
      { title: '关于这本书', text: '本书是欧文论成圣最著名、最实际的一本小书，以「你们若靠着圣灵治死身体的恶行必要活着」（罗8:13）为根。' },
      { title: '核心信息', text: '欧文那句广为人知的话点明全书：「你若不天天治死罪，罪必天天害你。」他教导信徒：内在残余的罪必须被持续地、主动地治死，不容它得地步。' },
      { title: '关键在哪里', text: '治死罪不是靠律法的恐吓、也不是靠自己的意志硬撑，乃是倚靠圣灵——既看见基督十架的赦免与能力，又靠圣灵从心里对付罪根，而非只压制外在的行为。' },
      { title: '怎么读', text: '边读边对付一个具体的、你一直纵容的罪：向神承认它，倚靠圣灵天天治死它。重在去行，而非只是读懂。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'baxter-pastor', title: '改革牧师（导读）', subtitle: '先顾己，再逐一牧养群羊', author: '原著 理查德·巴克斯特（Richard Baxter, The Reformed Pastor）',
    emoji: '🐑', color: '#34d399', kind: 'pdf', pdf: '/book/改革牧师-导读.pdf',
    blurb: '本应用原创导读：巴克斯特的牧养经典，写给传道人与带领者。可阅读、语音朗读、查看导读 PDF。',
    chapters: [
      { title: '关于这本书', text: '《改革牧师》是清教徒牧者巴克斯特的牧养经典，以「你们要为自己谨慎，也要为全群谨慎」（徒20:28）为骨架，写给传道人与教会带领者。' },
      { title: '核心信息', text: '两大主题：先看顾你自己的灵命，再去看顾群羊；并要逐一地、按名地牧养、教导、关心每个灵魂，而非只面对人群讲道。' },
      { title: '最扎心的一句', text: '巴克斯特以「我传道，像将死之人对将死之人」的迫切，提醒牧者对灵魂当有真实的负担——牧养不是职业，而是为永恒看顾人。' },
      { title: '怎么读', text: '带领者读来自省：我先顾自己的灵命了吗？我在逐一牧养身边的人，还是只在「办聚会」？把感动化为对某一个具体灵魂的关心。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'watson-divinity', title: '系统神学·身体的神学（导读）', subtitle: '人生首要目的——荣耀神、以神为乐', author: '原著 托马斯·沃森（Thomas Watson, A Body of Divinity）',
    emoji: '📘', color: '#60a5fa', kind: 'pdf', pdf: '/book/系统神学沃森-导读.pdf',
    blurb: '本应用原创导读：沃森依据《威斯敏斯特小要理问答》的讲道集，把要道讲得清楚甘甜。可阅读、语音朗读、查看导读 PDF。',
    chapters: [
      { title: '关于这本书', text: '本书是清教徒讲道家沃森根据《威斯敏斯特小要理问答》而作的讲道集，把基本要道讲得清楚、生动、满有应用，数百年来广受喜爱。' },
      { title: '开篇的大问题', text: '以「人生的首要目的是什么」开场——答案是「荣耀神，并以祂为乐，直到永远」。全书围绕着认识神、创造、护理、人的目的、信心与顺服等根基真理展开。' },
      { title: '特点', text: '沃森文笔生动、比喻丰富，把深奥的教义讲得人人能懂、又句句扎心——证明真理可以又清楚、又甘甜、又实际。' },
      { title: '怎么读', text: '一次读一小段，把教义读成「可应用、可敬拜」的真理；读完问：这条真理今天怎样改变我的生活与敬拜？（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
  {
    id: 'gurnall-armour', title: '基督徒全备军装（导读）', subtitle: '穿戴全副军装，靠主站立得胜', author: '原著 威廉·格纳尔（William Gurnall, The Christian in Complete Armour）',
    emoji: '🛡️', color: '#a78bfa', kind: 'pdf', pdf: '/book/全备军装-导读.pdf',
    blurb: '本应用原创导读：格纳尔以弗所书6章为骨架的属灵争战经典，司布真极力推崇。可阅读、语音朗读、查看导读 PDF。',
    chapters: [
      { title: '关于这本书', text: '《基督徒全备军装》是清教徒牧师格纳尔的巨著，以以弗所书6章「要穿戴神所赐的全副军装」为骨架，逐件解说属灵的军装与争战。司布真极为推崇此书。' },
      { title: '核心信息', text: '信徒的一生是一场真实的属灵争战。得胜不靠血气，乃靠穿戴神所赐的全备军装——真理的腰带、公义的护心镜、信德的盾牌、救恩的头盔、圣灵的宝剑（神的话），并靠儆醒祷告，靠主站立得稳。' },
      { title: '它帮助你', text: '识破并抵挡魔鬼的诡计，不在争战中天真大意；又指出每件军装的实际用法，叫你知道如何抵挡、如何站立。' },
      { title: '怎么读', text: '逐件检视：真理、公义、信德、救恩、神的话——哪一件你松懈了？读后操练「站立得稳、儆醒祷告」，而非凭血气硬扛。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）' },
    ],
  },
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
