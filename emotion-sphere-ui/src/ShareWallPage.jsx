import { useCallback, useEffect, useRef, useState } from 'react'
import jsPDF from 'jspdf'
import { TTSButton } from './useGlobalAudio.jsx'
import html2canvas from 'html2canvas'
import usePullToRefresh from './hooks/usePullToRefresh'
import { escapeHtml, escapeHtmlWithBr } from './sanitize'
import { fetchSharedNotes, toggleShareNote, amenSharedNote, toggleShareSermonJournal, fetchSundaySchoolVideos } from './api'
import { getToken } from './auth'

// 读取旧的 localStorage 分享记录（来自 ChatPage / DevotionNotePage / SermonJournalPage）
function getLegacySharedNotes() {
  try {
    const data = localStorage.getItem('devotion_notes_shared')
    const notes = data ? JSON.parse(data) : []
    // 标记来源并转换为 ShareWallPage 所期望的格式
    return notes
      .filter(n => n.shared !== false)
      .map(n => ({
        id: n.id || String(n.createdAt || Date.now()),
        email: '',
        date: n.date || '',
        scripture: n.scripture || '',
        observation: n.observation || '',
        reflection: n.reflection || '',
        application: n.application || '',
        prayer: n.prayer || '',
        mood: n.mood || '',
        shared: true,
        author: n.author || '匿名',
        avatar: n.avatar || '',
        createdAt: n.createdAt ? new Date(n.createdAt).toISOString() : null,
        updatedAt: n.sharedAt ? new Date(n.sharedAt).toISOString() : null,
        is_own: false,
        _source: 'local',
      }))
  } catch {
    return []
  }
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return dateStr
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

function exportSelectedToTxt(note) {
  if (!note) return
  let content = `属灵星球 - 灵修分享\n`
  content += `作者：${note.author || '匿名'}\n`
  content += `日期：${formatDate(note.date)}\n`
  if (note.mood) content += `心情：${note.mood}\n`
  content += `\n━━━━━━━━━━━━━━━━━━━━━━━\n  经文\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
  content += `${note.scripture || '未记录'}\n\n`
  
  if (note.observation) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  观察\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.observation}\n\n`
  }
  if (note.reflection) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  反思\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.reflection}\n\n`
  }
  if (note.application) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  应用\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.application}\n\n`
  }
  if (note.prayer) {
    content += `━━━━━━━━━━━━━━━━━━━━━━━\n  祷告\n━━━━━━━━━━━━━━━━━━━━━━━\n\n`
    content += `${note.prayer}\n\n`
  }
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  const title = (note.scripture || '灵修分享').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
  a.download = `${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

async function exportSelectedToPdf(note) {
  if (!note) return
  const pdf = new jsPDF('p', 'mm', 'a4')
  const PW = pdf.internal.pageSize.getWidth()
  const PH = pdf.internal.pageSize.getHeight()
  const M = 12, cw = PW - M * 2
  let curY = M
  pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F')

  const el = document.createElement('div')
  el.style.cssText = `position:fixed;left:-9999px;top:0;width:${Math.round(cw * 3.78)}px;background:#0e1726;padding:0;font-family:"Microsoft YaHei","PingFang SC",sans-serif;line-height:1.7;color:#e8e8e8;`
  document.body.appendChild(el)

  async function addBlock(html) {
    el.innerHTML = html
    const canvas = await html2canvas(el, { scale: 2, useCORS: true, logging: false, backgroundColor: '#0e1726' })
    const imgH = (canvas.height / canvas.width) * cw
    if (curY + imgH > PH - 10 && curY > M + 5) { pdf.addPage(); pdf.setFillColor(14, 23, 38); pdf.rect(0, 0, PW, PH, 'F'); curY = M }
    pdf.addImage(canvas.toDataURL('image/jpeg', 0.92), 'JPEG', M, curY, cw, imgH)
    curY += imgH + 3
  }

  try {
    await addBlock(`
      <div style="text-align:center;margin-bottom:10px;border-bottom:1px solid #2e3c52;padding-bottom:10px;">
        <h1 style="color:#007aff;font-size:20px;margin:0 0 6px 0;">属灵星球 - 灵修分享</h1>
        <div style="color:#9a9a9a;font-size:13px;">作者：${escapeHtml(note.author) || '匿名'} | 日期：${formatDate(note.date)}${note.mood ? ' | ' + escapeHtml(note.mood) : ''}</div>
      </div>
    `)
    await addBlock(`
      <div style="margin:6px 0;">
        <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">经文</div>
        <div style="font-size:15px;color:#f0f0f0;font-weight:600;margin:5px 0;">${escapeHtml(note.scripture) || '未记录'}</div>
      </div>
    `)
    if (note.observation) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">观察</div>
          <div style="background:#1a2433;padding:10px;border-radius:6px;color:#e8e8e8;white-space:pre-wrap;">${escapeHtmlWithBr(note.observation)}</div>
        </div>
      `)
    }
    if (note.reflection) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">反思</div>
          <div style="background:#1a2433;padding:10px;border-radius:6px;color:#e8e8e8;white-space:pre-wrap;">${escapeHtmlWithBr(note.reflection)}</div>
        </div>
      `)
    }
    if (note.application) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">应用</div>
          <div style="background:rgba(48,209,88,0.1);padding:10px;border-radius:6px;border:1px solid rgba(48,209,88,0.3);color:#1a6b2a;white-space:pre-wrap;">${escapeHtmlWithBr(note.application)}</div>
        </div>
      `)
    }
    if (note.prayer) {
      await addBlock(`
        <div style="margin:6px 0;">
          <div style="font-size:14px;font-weight:bold;color:#444;margin-bottom:5px;border-bottom:1px solid #2e3c52;padding-bottom:3px;">祷告</div>
          <div style="background:rgba(255,159,10,0.1);padding:10px;border-radius:6px;border:1px solid rgba(255,159,10,0.3);color:#7a4800;white-space:pre-wrap;font-style:italic;">${escapeHtmlWithBr(note.prayer)}</div>
        </div>
      `)
    }
    const n = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= n; p++) {
      pdf.setPage(p); pdf.setFontSize(9); pdf.setTextColor(180, 180, 180)
      pdf.text('https://holiness.uk/', PW / 2, PH - 4, { align: 'center' })
    }
    const title = (note.scripture || '灵修分享').replace(/[\\/:*?"<>|]/g, '').slice(0, 20)
    pdf.save(`${title}_${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2,'0')}${String(new Date().getDate()).padStart(2,'0')}.pdf`)
  } catch (err) { console.error('PDF generation failed:', err); alert('PDF 生成失败，请重试') }
  finally { document.body.removeChild(el) }
}


// ─────────────────────────────────────────────────────────────
// 信仰宣言与持守信经 — Statement of Faith
// ─────────────────────────────────────────────────────────────
const FAITH_DATA = {
  anchor: { ref: '犹大书 1:3', text: '亲爱的弟兄啊，我想尽心写信给你们，论我们同得救恩的时候，就不得不写信劝你们，要为从前一次交付圣徒的真道竭力地争辩。' },
  sections: [
    {
      title: '一、核心教义与神学基石',
      icon: '📜',
      items: [
        {
          heading: '圣经',
          body: '我们相信圣经旧约与新约全书是神所默示的，是无误、无谬的上帝之言，是信仰与生活一切事务的最高权威（提摩太后书 3:16-17）。',
        },
        {
          heading: '三位一体神',
          body: '我们相信独一真神永恒地以三个位格存在——圣父、圣子、圣灵，三位同质、同等、同荣（申命记 6:4；马太福音 28:19）。',
        },
        {
          heading: '耶稣基督',
          body: '我们相信耶稣基督是完全的神、完全的人，由圣灵感孕、童贞女所生，过无罪的一生，在十字架上为我们的罪死，肉身复活，升天坐在父神右边，并将再来审判活人死人（约翰福音 1:1,14；哥林多前书 15:3-4）。',
        },
        {
          heading: '人与救恩',
          body: '我们相信人是按上帝形象所造，因亚当堕落而全然败坏。救恩唯独出于恩典，唯独藉着信心，唯独在基督里——任何人悔改相信耶稣基督，便因他的宝血得蒙赦免、被称为义，与神和好（以弗所书 2:8-9；罗马书 3:23-24）。',
        },
        {
          heading: '教会',
          body: '我们相信普世教会是基督的身体，由一切重生信徒组成；地方教会应当忠实传讲圣道、施行洗礼与圣餐、彼此相顾、差遣宣教（马太福音 16:18；使徒行传 2:42）。',
        },
      ],
    },
    {
      title: '二、当代保守派伦理声明',
      icon: '⚖️',
      items: [
        {
          heading: '性别与身份',
          body: '上帝创造人类为男性与女性，性别是由神所赐、不可更改的礼物。我们肯定每一个人按照神所赋予的生理性别生活的尊严（创世记 1:27）。',
        },
        {
          heading: '婚姻',
          body: '婚姻是一男一女在神面前所立的终身圣约，是家庭与社会的基本单元，也是基督与教会关系的象征（创世记 2:24；以弗所书 5:31-32）。',
        },
        {
          heading: '男女互补',
          body: '男女在价值与尊严上完全平等，在家庭与教会中蒙召扮演互补的角色——男性有爱妻如己、服事领导的责任；女性有智慧帮助、同工建造的呼召（以弗所书 5:22-33；提摩太前书 2:12-13）。',
        },
        {
          heading: '生命神圣',
          body: '人的生命自受孕起即是神的形象，应当受到保护。我们反对一切剥夺无辜生命的行为，并呼召教会为弱势群体发声、提供关怀（诗篇 139:13-16；箴言 31:8）。',
        },
      ],
    },
    {
      title: '三、历代信经信条',
      icon: '🕊️',
      subsections: [
        {
          subtitle: '普世公认信经',
          creed: true,
          items: [
            { heading: '使徒信经（约 2世纪）', body: '我信上帝，全能的父，创造天地的主。\n我信我主耶稣基督，上帝的独生子；因圣灵感孕，由童贞女马利亚所生；在本丢彼拉多手下受难，被钉于十字架，受死，埋葬；降在阴间；第三天从死人中复活；升天，坐在全能父上帝的右边；将来必从那里降临，审判活人死人。\n我信圣灵；我信圣而公之教会；我信圣徒相通；我信罪得赦免；我信身体复活；我信永生。阿们。' },
            { heading: '尼西亚信经（325 / 381年）', body: '我信独一上帝，全能的父，创造天地和有形无形万物的主。\n我信独一主耶稣基督，上帝的独生子，在万世以前为父所生：出于神而为神，出于光而为光，出于真神而为真神，被生非被造，与父同质，万物都是藉着他造的。他为要拯救我们世人，从天降临，因着圣灵，并从童贞女马利亚取了肉身成为人，在本丢彼拉多手下为我们钉十字架，受难受葬，照圣经第三天复活，并升上天，坐在父的右边，将来必有荣耀再降临，审判活人死人，他的国没有穷尽。\n我信圣灵，赐生命的主，从父（和子）出来，与父及子同受敬拜，同受尊荣，他曾藉众先知说话。\n我信独一、圣洁、公教、使徒的教会，我认使罪得赦的独一洗礼，我望死人复活，并来世的生命。阿们。' },
            { heading: '迦克墩信经（451年）', body: '我们同声教导人承认同一位子、我们的主耶稣基督，是完全的神、完全的人，真实具有理性的灵魂与肉体；按神性与父同质，按人性与我们同质，在各方面与我们相同，只是没有罪。\n按神性，在万世之先为父所生；按人性，在末后这些日子，为了我们和我们的救恩，从童贞女、上帝之母马利亚而生。\n是同一基督、子、主、独生的，具有两个本性，不相混乱、不相交换、不能分开、不能离散；两性的区别不因联合而消除，各性的特质反得以保全，汇合于一个位格、一个本体之内，并不分裂或分离为两个位格，乃是同一位子、独生的、道、主耶稣基督——正如从太初先知论及他的，主耶稣基督自己所教导我们的，并圣教父的信经所传递给我们的。' },
            { heading: '亚他那修信经（约 5世纪，节选）', body: '凡人若要得救，首先必须持守公教信仰；若不完整无误地持守，必永远灭亡。\n公教信仰是这样的：我们敬拜三位一体中的独一真神，以及独一真神中的三位一体，不混淆三个位格，也不分裂神的本质。圣父是一个位格，圣子是一个位格，圣灵是一个位格；然而圣父、圣子、圣灵的神性是同一的，荣耀相等，威严同永恒。\n圣父怎样，圣子也怎样，圣灵也怎样：圣父是无受造的，圣子是无受造的，圣灵也是无受造的；圣父是永恒的，圣子是永恒的，圣灵也是永恒的；然而并非三个永恒者，乃是一个永恒者。\n更多，为要得救，必须笃信我们的主耶稣基督成肉身之事：正确的信仰就是相信并承认我们的主耶稣基督，上帝之子，是神，也是人……' },
          ],
        },
        {
          subtitle: '历代改革宗与福音派宣言',
          creed: false,
          items: [
            { heading: '海德堡要理问答（1563年）', body: '第一问：你活着和死的时候，你惟一的安慰是什么？\n答：我的灵魂和身体，不论活着还是死的，不属于我自己，乃属于我忠实的救主耶稣基督。他用自己宝贵的血赎买了我，使我从魔鬼一切的权势中得释放……' },
            { heading: '威斯敏斯特信条（1646年）', body: '【论圣经（第一章）】圣经旧约与新约全书，是上帝所默示的，是信仰和生活的法则。圣经的权威不依赖任何人或教会的见证，完全依赖于上帝本身——祂是真理，也是圣经的作者。\n【论上帝与三位一体（第二章）】只有一位活的真神，祂是无限完全的灵，全知、全能、全善、至圣、至公；在上帝的独一性里，有三个位格：圣父、圣子和圣灵，本质相同，权能荣耀相等。\n【论基督的中保工作（第八章）】上帝在永恒的拣选中，指定祂的独生子主耶稣基督作神人之间的中保，先知、祭司和君王；他取了人性，完全遵行了律法，在十字架上作了挽回祭，胜过了死亡，并在荣耀里升天，以拯救所有父神赐给祂的人。\n【论称义（第十一章）】上帝称凡有效蒙召之人为义，不是因为在他们里面注入了义，也不是因为他们的任何行为，只是因为赦免了他们的罪，认为并接受他们为义——只因归算给他们的基督的顺服与受苦偿还，单靠信心接受称义，这信心本身不是他们自己所能生出的。' },
            { heading: '洛桑信约（1974年）', body: '【上帝的旨意与我们的使命】我们宣认上帝在创造、护理、审判、救赎和赐恩等方面的主权，同时为祂向世人所赐的救恩而感恩。我们宣称，教会被召出来，是要在人类各族中荣耀上帝，并宣告福音直到地极。\n【圣经的权威与能力】我们肯定圣经的神圣默示、真实性和权威性，宣认圣经是判断一切事物的最高准则，是引导我们认识上帝旨意的无误向导。\n【基督的独特性与普世性】只有一位救主，只有一篇福音。我们宣认耶稣基督是主，是救主；祂的救恩既是普世性的，也是排他的——除他以外，别无拯救。\n【传福音与社会责任】传福音与基督徒社会关怀，两者都是我们的基督徒职责。我们呼召教会不仅传讲和好的福音，也要用行动彰显上帝对公义的关怀。\n【教会与宣教】我们宣认教会是宣教的核心，并承诺效法基督、舍己服务，进入一切文化，藉着圣灵能力向万国传扬耶稣基督。' },
            { heading: '芝加哥圣经无误宣言（1978年）', body: '【默示与无误】我们肯定，圣经的整体以及每一部分，直到原文的每一个字，都是出于上帝的默示；我们否认，上帝的默示只是局限于某些部分，或圣经的某些命题不是无误的。\n【真理与诚实】我们肯定，圣经是无误和无谬的——在它所确认的一切事上是真实的，不会误导人；我们否认，圣经的无误性与无谬性仅限于属灵或宗教的事物，而不延伸至历史和科学领域。\n【解释与权威】我们肯定，圣经整体及各个部分的意思，包括预言性的内容，是单义的，虽然其应用可以是多元的；我们否认，解释者可以透过任何理由合法地将自己的意思加于经文。\n【圣经的充足性】我们肯定，圣经包含了所有关乎救恩和所有信仰生活所必须知道、相信和遵守的事；我们否认，任何教会、传统或个人经历可以在权威上与圣经并驾齐驱。' },
          ],
        },
      ],
    },
  ],
}

function FaithDocumentView() {
  const [openItems, setOpenItems] = useState({})
  function toggle(key) { setOpenItems(prev => ({ ...prev, [key]: !prev[key] })) }

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 40px' }}>
      {/* Anchor verse */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(90,200,250,0.12), rgba(118,75,162,0.12))',
        border: '1px solid rgba(90,200,250,0.25)',
        borderRadius: 14, padding: '16px 18px', marginBottom: 22, textAlign: 'center',
      }}>
        <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', letterSpacing: '0.08em', marginBottom: 8 }}>✝️ {FAITH_DATA.anchor.ref}</div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.88)', lineHeight: 1.75, fontStyle: 'italic' }}>
          「{FAITH_DATA.anchor.text}」
        </div>
      </div>

      {FAITH_DATA.sections.map((section, si) => (
        <div key={si} style={{ marginBottom: 24 }}>
          {/* Section header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <span style={{ fontSize: 18 }}>{section.icon}</span>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'rgba(255,255,255,0.95)' }}>{section.title}</div>
          </div>

          {/* Flat items */}
          {section.items && section.items.map((item, ii) => {
            const key = `s${si}i${ii}`
            const open = openItems[key]
            return (
              <div key={ii} style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: 12, marginBottom: 8, overflow: 'hidden',
              }}>
                <button
                  onClick={() => toggle(key)}
                  style={{
                    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 14px', background: 'none', border: 'none',
                    color: 'rgba(255,255,255,0.9)', fontSize: 14, fontWeight: 600,
                    cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                  }}
                >
                  <span>{item.heading}</span>
                  <span style={{ color: 'rgba(255,255,255,0.35)', fontSize: 12, flexShrink: 0, marginLeft: 8 }}>{open ? '▲' : '▼'}</span>
                </button>
                {open && (
                  <div style={{ padding: '0 14px 14px', fontSize: 13, color: 'rgba(255,255,255,0.72)', lineHeight: 1.8 }}>
                    {item.body}
                  </div>
                )}
              </div>
            )
          })}

          {/* Subsections (for section 3) */}
          {section.subsections && section.subsections.map((sub, subi) => (
            <div key={subi} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'rgba(90,200,250,0.8)', letterSpacing: '0.06em', marginBottom: 10, paddingLeft: 4 }}>
                {sub.subtitle}
              </div>
              {sub.items.map((item, ii) => {
                const key = `s${si}sub${subi}i${ii}`
                const open = openItems[key]
                return (
                  <div key={ii} style={{
                    background: sub.creed ? 'rgba(90,200,250,0.05)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${sub.creed ? 'rgba(90,200,250,0.15)' : 'rgba(255,255,255,0.07)'}`,
                    borderRadius: 12, marginBottom: 8, overflow: 'hidden',
                  }}>
                    <button
                      onClick={() => toggle(key)}
                      style={{
                        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '11px 14px', background: 'none', border: 'none',
                        color: sub.creed ? 'rgba(90,200,250,0.9)' : 'rgba(255,255,255,0.85)',
                        fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left',
                      }}
                    >
                      <span>{item.heading}</span>
                      <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 11, flexShrink: 0, marginLeft: 8 }}>{open ? '▲' : '▼'}</span>
                    </button>
                    {open && (
                      <div style={{ padding: '0 14px 14px', fontSize: 12.5, color: 'rgba(255,255,255,0.65)', lineHeight: 1.85, whiteSpace: 'pre-wrap', fontStyle: sub.creed ? 'italic' : 'normal' }}>
                        {item.body}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          ))}
        </div>
      ))}

      <div style={{ textAlign: 'center', fontSize: 11, color: 'rgba(255,255,255,0.25)', marginTop: 8 }}>
        属灵星球 · 持守古道 · 传扬真道
      </div>
    </div>
  )
}

const MAX_LINES = 8
const LINE_HEIGHT = 1.6
const FONT_SIZE = 13
const COLLAPSED_HEIGHT = MAX_LINES * FONT_SIZE * LINE_HEIGHT

function NoteDetailOverlay({ note, onClose, onUnshare, onAmen, token }) {
  const [amenLoading, setAmenLoading] = useState(false)
  const [amenCount, setAmenCount] = useState(note.amen_count || 0)
  const [amenByMe, setAmenByMe] = useState(note.amen_by_me || false)

  async function handleAmen() {
    if (amenLoading || !token) return
    setAmenLoading(true)
    try {
      const res = await amenSharedNote(note.id, token)
      setAmenCount(res.amen_count)
      setAmenByMe(res.amen_by_me)
      onAmen(note.id, res.amen_count, res.amen_by_me)
    } catch (e) {
      console.warn('[amen]', e)
    } finally {
      setAmenLoading(false)
    }
  }

  async function handleUnshare() {
    if (!window.confirm('确定要从分享墙撤回这篇内容吗？')) return
    onUnshare(note.id)
    onClose()
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      display: 'flex', flexDirection: 'column', overflowY: 'auto',
    }}>
      {/* Detail header */}
      <div style={{ position: 'sticky', top: 0, zIndex: 1, background: 'rgba(22,33,62,0.95)', backdropFilter: 'blur(10px)', borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={onClose} style={{ background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8, color: '#fff', padding: '6px 12px', cursor: 'pointer', fontSize: 13 }}>← 返回</button>
        <div style={{ flex: 1 }} />
        {/* Amen button in header */}
        <button
          onClick={handleAmen}
          disabled={amenLoading}
          style={{
            display: 'flex', alignItems: 'center', gap: 5, padding: '6px 14px',
            background: amenByMe ? 'rgba(52,199,89,0.25)' : 'rgba(255,255,255,0.08)',
            border: `1px solid ${amenByMe ? 'rgba(52,199,89,0.5)' : 'rgba(255,255,255,0.18)'}`,
            borderRadius: 20, color: amenByMe ? '#34c759' : 'rgba(255,255,255,0.7)',
            fontSize: 13, cursor: 'pointer', fontWeight: amenByMe ? 600 : 400,
          }}
        >
          🙌 阿们 {amenCount > 0 && <span style={{ fontWeight: 700 }}>{amenCount}</span>}
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '20px 18px', maxWidth: 600, margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
        {/* Author row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, paddingBottom: 16, borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          {note.avatar ? (
            <img src={note.avatar} alt="" style={{ width: 44, height: 44, borderRadius: '50%', objectFit: 'cover' }} />
          ) : (
            <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'linear-gradient(135deg,#667eea,#764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
              {note.author?.[0] || '?'}
            </div>
          )}
          <div>
            <div style={{ fontSize: 16, fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>{note.author || '匿名'}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>
              {note.mood && <span style={{ marginRight: 6 }}>{note.mood}</span>}
              {formatDate(note.sharedAt || note.date)}
            </div>
          </div>
        </div>

        {/* TTS */}
        {(note.scripture || note.observation || note.reflection || note.application || note.prayer) && (
          <TTSButton text={[note.scripture, note.observation, note.reflection, note.application, note.prayer].filter(Boolean).join('　')} />
        )}

        {/* Scripture */}
        <div style={{ fontSize: 18, fontWeight: 700, color: '#fff', marginBottom: 20, lineHeight: 1.5 }}>{note.scripture}</div>

        {[['👁️ 观察', note.observation], ['💭 反思', note.reflection], ['✨ 应用', note.application], ['🙏 祷告', note.prayer]]
          .filter(([, v]) => v)
          .map(([label, text]) => (
            <div key={label} style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', marginBottom: 6, fontWeight: 600, letterSpacing: '0.04em' }}>{label}</div>
              <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.85)', lineHeight: 1.75, whiteSpace: 'pre-wrap', fontStyle: label.includes('祷告') ? 'italic' : 'normal' }}>{text}</div>
            </div>
          ))}

        {/* Action Buttons */}
        <div style={{ marginTop: 32, paddingTop: 20, borderTop: '1px solid rgba(255,255,255,0.08)', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {note.is_own && (
            <button
              onClick={handleUnshare}
              style={{ width: '100%', padding: '11px', marginBottom: 6, background: 'rgba(255,59,48,0.12)', border: '1px solid rgba(255,59,48,0.35)', borderRadius: 10, color: '#ff6b6b', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
            >
              ↩️ 从分享墙撤回
            </button>
          )}
          <button
            onClick={e => window.busyBtn(e, () => exportSelectedToTxt(note), "导出 TXT 中…", "✅ TXT 已导出")}
            style={{ flex: 1, padding: '10px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10, color: 'rgba(255,255,255,0.8)', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            TXT
          </button>
          <button
            onClick={e => window.busyBtn(e, () => exportSelectedToPdf(note), "生成 PDF 中…", "✅ PDF 已导出")}
            style={{ flex: 1, padding: '10px', background: 'rgba(0,122,255,0.18)', border: '1px solid rgba(0,122,255,0.35)', borderRadius: 10, color: '#5ac8fa', fontSize: 13, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5 }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15l3 3 3-3"/><path d="M12 18V9"/></svg>
            PDF
          </button>
        </div>
      </div>
    </div>
  )
}


// ── SundaySchoolView — 主日学视频列表 + 行内播放器 ─────────────────────────────
function fmtModified(ts) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
}

function SundaySchoolView() {
  const [videos, setVideos] = useState(null)
  const [err, setErr] = useState('')
  const [playing, setPlaying] = useState(null)   // video_url of currently playing

  useEffect(() => {
    fetchSundaySchoolVideos()
      .then(d => setVideos(d.videos || []))
      .catch(() => setErr('视频加载失败，请稍后重试'))
  }, [])

  if (err) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,100,100,0.7)', fontSize: 14, padding: 32 }}>
      {err}
    </div>
  )

  if (!videos) return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.3)', fontSize: 14 }}>
      加载中…
    </div>
  )

  if (videos.length === 0) return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 12 }}>
      <div style={{ fontSize: 44 }}>🎬</div>
      <div style={{ fontSize: 16, color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>暂无主日学视频</div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.35)', textAlign: 'center', lineHeight: 1.7 }}>
        视频上传到 cdn.holiness.uk/videos/ 后将自动显示
      </div>
    </div>
  )

  return (
    <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
      {videos.map(v => {
        const isPlaying = playing === v.video_url
        return (
          <div key={v.video_url} style={{
            marginBottom: 14, borderRadius: 14,
            background: 'rgba(255,255,255,0.04)',
            border: isPlaying ? '1px solid rgba(90,200,250,0.45)' : '1px solid rgba(255,255,255,0.08)',
            overflow: 'hidden', transition: 'border 0.2s',
          }}>
            {/* ── Inline player (mounted only when this video is active) ── */}
            {isPlaying ? (
              <video
                src={v.video_url}
                controls autoPlay playsInline
                style={{ width: '100%', display: 'block', background: '#000', maxHeight: 280 }}
                onEnded={() => setPlaying(null)}
              />
            ) : (
              /* ── Play-button thumbnail ── */
              <div
                onClick={() => setPlaying(v.video_url)}
                style={{
                  position: 'relative', cursor: 'pointer',
                  background: 'linear-gradient(135deg,#12122a,#0d0d20)',
                  height: 150,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}
              >
                <div style={{ fontSize: 36, opacity: 0.25 }}>🎬</div>
                {/* Centred play circle */}
                <div style={{
                  position: 'absolute', inset: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <div style={{
                    width: 56, height: 56, borderRadius: '50%',
                    background: 'rgba(90,200,250,0.82)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    boxShadow: '0 4px 22px rgba(90,200,250,0.38)',
                  }}>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="#fff">
                      <polygon points="6,3 20,12 6,21" />
                    </svg>
                  </div>
                </div>
              </div>
            )}

            {/* ── Meta row ── */}
            <div style={{ padding: '10px 14px 12px', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.92)', lineHeight: 1.4, marginBottom: 3 }}>
                  {v.title || v.filename || '未命名'}
                </div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                  {v.filename}
                  {v.modified_ts > 0 && <span style={{ marginLeft: 8 }}>📅 {fmtModified(v.modified_ts)}</span>}
                </div>
              </div>
              {isPlaying && (
                <button
                  onClick={() => setPlaying(null)}
                  style={{ flexShrink: 0, background: 'rgba(255,255,255,0.08)', border: 'none', borderRadius: 6, color: 'rgba(255,255,255,0.45)', fontSize: 12, padding: '4px 10px', cursor: 'pointer' }}
                >✕</button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function ShareWallPage({ user, onBack }) {
  const [notes, setNotes] = useState([])
  const [selectedNote, setSelectedNote] = useState(null)
  const [expandedCards, setExpandedCards] = useState({})
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [faithTab, setFaithTab] = useState('share')
  const listRef = useRef(null)
  const token = getToken()

  function toggleExpand(id) {
    setExpandedCards(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const loadNotes = useCallback(async (pg = 1) => {
    if (!user) return
    setLoading(true)
    try {
      const data = await fetchSharedNotes(token, pg, 20)
      if (data.requireLogin) { setLoading(false); return }
      const apiNotes = data.items || []

      if (pg === 1) {
        // First load: also merge legacy localStorage notes (one-time migration)
        const legacyNotes = getLegacySharedNotes()
        if (legacyNotes.length > 0) {
          const seenIds = new Set(apiNotes.map(n => n.id))
          const extra = legacyNotes.filter(n => !seenIds.has(n.id))
          setNotes([...apiNotes, ...extra])
          // Auto-clear legacy after successful API load
          localStorage.removeItem('devotion_notes_shared')
          console.log('[sharewall] migrated & cleared', extra.length, 'legacy notes')
        } else {
          setNotes(apiNotes)
        }
      } else {
        setNotes(prev => [...prev, ...data.items])
      }
      setPage(pg)
      setTotalPages(data.pages || 1)
      setTotal(data.total || 0)
    } catch (err) {
      console.error('[sharewall] load error:', err)
    } finally {
      setLoading(false)
    }
  }, [user, token])

  useEffect(() => { loadNotes(1) }, [loadNotes])

  const { indicatorStyle, indicatorText } = usePullToRefresh(() => loadNotes(1), listRef)

  async function handleUnshare(noteId) {
    const note = notes.find(n => n.id === noteId)
    if (note?._source === 'local') {
      setNotes(prev => prev.filter(n => n.id !== noteId))
      return
    }
    try {
      if (note?.type === 'sermon_journal') {
        const journalId = parseInt(noteId.replace('sermon-', ''), 10)
        await toggleShareSermonJournal(journalId, token)
      } else {
        await toggleShareNote(noteId, token)
      }
      setNotes(prev => prev.filter(n => n.id !== noteId))
      setTotal(t => Math.max(0, t - 1))
    } catch (err) {
      alert(err.message || '操作失败')
    }
  }

  function handleAmenUpdate(noteId, amen_count, amen_by_me) {
    setNotes(prev => prev.map(n => n.id === noteId ? { ...n, amen_count, amen_by_me } : n))
  }

  if (!user) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'linear-gradient(135deg,#1a1a2e,#16213e)' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🌟</div>
        <div style={{ fontSize: 18, color: 'rgba(255,255,255,0.9)', marginBottom: 8 }}>分享墙</div>
        <div style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', marginBottom: 24 }}>登录后查看分享墙内容</div>
        <button onClick={onBack} style={{ padding: '10px 24px', background: 'rgba(0,122,255,0.3)', border: '1px solid rgba(0,122,255,0.5)', borderRadius: 8, color: '#5ac8fa', fontSize: 14, cursor: 'pointer' }}>← 返回</button>
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'linear-gradient(135deg,#1a1a2e,#16213e)' }}>
      {/* Detail overlay (mobile full-screen + desktop full-screen) */}
      {selectedNote && (
        <NoteDetailOverlay
          note={selectedNote}
          onClose={() => setSelectedNote(null)}
          onUnshare={handleUnshare}
          onAmen={handleAmenUpdate}
          token={token}
        />
      )}

      {/* Header */}
      <header style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'rgba(13,13,26,0.85)', backdropFilter: 'blur(10px)' }}>
        <div style={{ padding: '12px 18px 0', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.7)', cursor: 'pointer', padding: 8 }}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="15 18 9 12 15 6" /></svg>
          </button>
          <div style={{ flex: 1, textAlign: 'center' }}>
            <div style={{ fontSize: 17, fontWeight: 600, color: 'rgba(255,255,255,0.95)' }}>🌟 分享墙</div>
            {faithTab === 'share' && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>{total > 0 ? `${total} 篇分享` : ''}</div>}
            {faithTab === 'sunday' && <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>主日学视频</div>}
          </div>
          {faithTab === 'share' ? (
            <button
              onClick={() => loadNotes(1)}
              style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', padding: 8, fontSize: 16 }}
              title="刷新"
            >↻</button>
          ) : <div style={{ width: 36 }} />}
        </div>
        {/* Sub-tab switcher */}
        <div style={{ display: 'flex', padding: '0 18px', gap: 4, marginTop: 8 }}>
          {[
            { key: 'share', label: '社区分享', emoji: '🌟' },
            { key: 'faith', label: '信仰宣言', emoji: '✝️' },
            { key: 'sunday', label: '主日学', emoji: '🎬' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setFaithTab(tab.key)}
              style={{
                flex: 1, padding: '8px 4px',
                background: 'none', border: 'none',
                borderBottom: faithTab === tab.key ? '2px solid #5ac8fa' : '2px solid transparent',
                color: faithTab === tab.key ? '#5ac8fa' : 'rgba(255,255,255,0.45)',
                fontSize: 13, fontWeight: faithTab === tab.key ? 600 : 400,
                cursor: 'pointer', fontFamily: 'inherit',
                transition: 'all 0.15s',
              }}
            >
              {tab.emoji} {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Faith document view */}
      {faithTab === 'faith' && <FaithDocumentView />}

      {/* Sunday school video view */}
      {faithTab === 'sunday' && <SundaySchoolView />}

      {/* Note list */}
      <div ref={listRef} style={{ flex: 1, overflowY: 'auto', padding: '12px 14px', position: 'relative', display: faithTab === 'share' ? 'block' : 'none' }}>
        <div style={indicatorStyle}>{indicatorText}</div>

        {loading && notes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.4)' }}>加载中...</div>
        ) : notes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 0', color: 'rgba(255,255,255,0.4)' }}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>📝</div>
            <div style={{ fontSize: 15 }}>暂无分享</div>
            <div style={{ fontSize: 13, marginTop: 8, opacity: 0.6 }}>在日记页面分享你的灵修心得</div>
          </div>
        ) : (
          <>
            {notes.map(note => {
              const text = note.reflection || note.observation || ''
              const lines = text.split('\n')
              const isLong = lines.length > MAX_LINES || text.length > MAX_LINES * 38
              const expanded = expandedCards[note.id]
              return (
                <div
                  key={note.id}
                  onClick={() => setSelectedNote(note)}
                  style={{
                    padding: '14px 14px 10px',
                    marginBottom: 10,
                    background: 'rgba(255,255,255,0.05)',
                    borderRadius: 14,
                    cursor: 'pointer',
                    border: '1px solid rgba(255,255,255,0.08)',
                    transition: 'background 0.15s',
                  }}
                >
                  {/* Author row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 9 }}>
                    {note.avatar ? (
                      <img src={note.avatar} alt="" style={{ width: 30, height: 30, borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }} />
                    ) : (
                      <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'linear-gradient(135deg,#667eea,#764ba2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>
                        {note.author?.[0] || '?'}
                      </div>
                    )}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 13, fontWeight: 500, color: 'rgba(255,255,255,0.9)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{note.author || '匿名'}</div>
                      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>{note.mood && <span style={{ marginRight: 5 }}>{note.mood}</span>}{formatDate(note.sharedAt || note.date)}</div>
                    </div>
                    {/* Inline amen count badge */}
                    {(note.amen_count > 0) && (
                      <span style={{ fontSize: 11, color: note.amen_by_me ? '#34c759' : 'rgba(255,255,255,0.4)', flexShrink: 0 }}>🙌 {note.amen_count}</span>
                    )}
                  </div>

                  {/* Scripture */}
                  {note.scripture && (
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'rgba(255,255,255,0.95)', marginBottom: 6, lineHeight: 1.5 }}>{note.scripture}</div>
                  )}

                  {/* Preview text */}
                  {text ? (
                    <div style={{ position: 'relative' }}>
                      <div style={{
                        fontSize: FONT_SIZE, color: 'rgba(255,255,255,0.65)', lineHeight: LINE_HEIGHT,
                        whiteSpace: 'pre-wrap', overflow: 'hidden',
                        maxHeight: (!expanded && isLong) ? `${COLLAPSED_HEIGHT}px` : 'none',
                      }}>
                        {text}
                        {!expanded && isLong && (
                          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: 40, background: 'linear-gradient(transparent, rgba(26,26,46,0.95))' }} />
                        )}
                      </div>
                      {isLong && (
                        <button
                          onClick={e => { e.stopPropagation(); toggleExpand(note.id) }}
                          style={{ background: 'none', border: 'none', padding: '4px 0', color: '#5ac8fa', fontSize: 12, cursor: 'pointer', fontFamily: 'inherit' }}
                        >
                          {expanded ? '收起 ▲' : '展开全文 ▼'}
                        </button>
                      )}
                    </div>
                  ) : null}
                </div>
              )
            })}

            {/* Load more */}
            {page < totalPages && (
              <div style={{ textAlign: 'center', padding: '16px 0' }}>
                <button
                  onClick={() => loadNotes(page + 1)}
                  disabled={loading}
                  style={{ padding: '10px 28px', background: 'rgba(0,122,255,0.2)', border: '1px solid rgba(0,122,255,0.35)', borderRadius: 20, color: '#5ac8fa', fontSize: 13, cursor: 'pointer' }}
                >
                  {loading ? '加载中...' : '加载更多'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
