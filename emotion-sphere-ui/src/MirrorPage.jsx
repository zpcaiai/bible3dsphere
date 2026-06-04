import { useState, useMemo, useCallback, useRef } from 'react'
import { useGlobalAudio, TTSButton as _TTSBtn, TTSFullBar as _TTSFullBar } from './useGlobalAudio.jsx'
import { MIRROR_CHARACTERS, MIRROR_THEMES } from './mirrorData'
import { saveJournal } from './api'
import BibleMap from './BibleMap'
import { CHARACTER_JOURNEYS, buildCharacterMapConfig } from './data/characterJourneys'

const ERAS = ['全部', '族长时代', '出埃及时代', '士师时代', '进入迦南时代', '王国时代', '被掳归回时代', '新约时代', '教会时代']
const ROLES = ['全部', '主&救主', '族长', '君王', '先知', '祭司', '女性', '使徒', '其他']
const TYPES = ['全部', '正面榜样', '警戒为主', '混合型']
const TYPO_FILTER = ['全部', '有预表', '强预表', '中等预表', '弱预表/影子', '反衬预表']
const MOTIF_DEF = {
  '最后的亚当·新人类元首': { id: 'last_adam', names: ['亚当','塞特','挪亚','闪','亚伯拉罕'] },
  '女人的后裔·应许谱系': { id: 'seed_woman', names: ['夏娃','塞特','闪','亚伯拉罕','以撒','雅各','犹大','法勒斯','大卫','所罗巴伯'] },
  '应许之子': { id: 'promised_son', names: ['以撒','雅各','犹大','法勒斯','大卫'] },
  '受苦义人': { id: 'suffering_righteous', names: ['亚伯','约瑟','大卫','约伯','耶利米','拿伯','但以理','以赛亚'] },
  '代替者': { id: 'substitute', names: ['以撒','犹大','波阿斯','摩西'] },
  '先知': { id: 'prophet', names: ['摩西','撒母耳','以利亚','以利沙','以赛亚','耶利米','以西结','但以理','约拿'] },
  '祭司': { id: 'priest', names: ['麦基洗德','亚伦','非尼哈','撒督','以斯拉','约书亚大祭司'] },
  '君王': { id: 'king', names: ['麦基洗德','犹大','大卫','所罗门','希西家','约西亚','所罗巴伯','古列'] },
  '牧者': { id: 'shepherd', names: ['雅各','摩西','大卫','阿摩司','以西结'] },
  '拯救者': { id: 'savior', names: ['挪亚','摩西','约书亚','波阿斯','以斯帖','末底改','尼希米'] },
  '圣殿与建造者': { id: 'temple_builder', names: ['比撒列','所罗门','所罗巴伯','以斯拉','尼希米','哈该','撒迦利亚'] },
  '新郎': { id: 'bridegroom', names: ['亚当','以撒','波阿斯','何西阿','所罗门'] },
  '亲属救赎者': { id: null, names: ['波阿斯'] },
  '士师拯救者': { id: null, names: ['俄陀聂','以笏','底波拉','基甸','耶弗他','参孙'] },
  '外邦蒙恩线索': { id: null, names: ['喇合','路得','撒勒法寡妇','乃缦','约拿'] },
  '被掳归回重建者': { id: null, names: ['古列','所罗巴伯','以斯拉','尼希米'] },
  '反面衬托': { id: null, negative: true, names: ['该隐','法老','可拉','巴兰','扫罗','耶罗波安','亚哈','耶洗别','哈曼'] },
}
const MOTIF_FILTER = ['全部', ...Object.keys(MOTIF_DEF)]
const TYPO_COLOR = { '极强预表': '#ffd60a', '强预表': '#ff9f0a', '中等预表': '#5ac8fa', '弱预表': '#98989d', '反面预表': '#ff6b6b' }
const STRENGTH_LABEL = { explicit_nt: '新约明确指认', strong_canonical: '正典强预表', office_typology: '职分预表', narrative_pattern: '叙事结构预表', genealogical: '谱系性预表', weak_devotional: '灵修性影子', negative_contrast: '反面衬托' }
const MOTIF_LABEL = { last_adam: '末后的亚当', seed_woman: '女人后裔·谱系', promised_son: '应许之子', suffering_righteous: '受苦义人', substitute: '代替者', prophet: '先知', priest: '祭司', king: '君王', shepherd: '牧者', savior: '拯救者', temple_builder: '圣殿建造者', bridegroom: '新郎' }

const typeColor = { '正面榜样': '#34c759', '警戒为主': '#ff3b30', '混合型': '#ff9500' }
const eraColor = {
  '族长时代': '#8e44ad', '出埃及时代': '#2980b9', '士师时代': '#16a085',
  '进入迦南时代': '#27ae60', '王国时代': '#d35400', '被掳归回时代': '#c0392b', '新约时代': '#1abc9c',
  '教会时代': '#7c5cff'
}

const BOOK_MAP = {
  '创':'gen','出':'exo','利':'lev','民':'num','申':'deu','书':'jos','士':'jdg','得':'rut',
  '撒上':'1sa','撒下':'2sa','王上':'1ki','王下':'2ki','代上':'1ch','代下':'2ch',
  '拉':'ezr','尼':'neh','斯':'est','伯':'job','诗':'psa','箴':'pro','传':'ecc',
  '歌':'sng','赛':'isa','耶':'jer','哀':'lam','结':'eze','但':'dan','何':'hos',
  '珥':'joe','摩':'amo','俄':'oba','拿':'jon','弥':'mic','鸿':'nah','哈':'hab',
  '番':'zep','该':'hag','亚':'zec','玛':'mal',
  '太':'mat','可':'mrk','路':'luk','约':'jhn','徒':'act','罗':'rom',
  '林前':'1co','林后':'2co','加':'gal','弗':'eph','腓':'php','西':'col',
  '帖前':'1th','帖后':'2th','提前':'1ti','提后':'2ti','多':'tit','门':'phm',
  '来':'heb','雅':'jas','彼前':'1pe','彼后':'2pe','约一':'1jn','约二':'2jn',
  '约三':'3jn','犹':'jud','启':'rev'
}

function toWdBibleUrl(ref) {
  const cleaned = ref.trim()
  const match = cleaned.match(/^([^\d]+)(\d+)(?:[:：](\d+)(?:[–\-](\d+))?)?/)
  if (!match) return `https://wd.bible/bible`
  const bookZh = match[1].trim()
  const chapter = match[2]
  const verse = match[3]
  const bookCode = BOOK_MAP[bookZh]
  if (!bookCode) return `https://wd.bible/bible`
  if (verse) return `https://wd.bible/verse/${bookCode}.${chapter}.${verse}.cunps`
  return `https://wd.bible/${bookCode}.${chapter}.cunps`
}

function toVerseProxyUrl(ref) {
  const cleaned = ref.trim()
  const match = cleaned.match(/^([^\d]+)(\d+)(?:[:：](\d+)(?:[–\-](\d+))?)?/)
  if (!match) return null
  const bookZh = match[1].trim()
  const chapter = match[2]
  const verse = match[3]
  const bookCode = BOOK_MAP[bookZh]
  if (!bookCode || !verse) return null
  return `/wdbible/verse/${bookCode}.${chapter}.${verse}.cunps`
}

const verseCache = new Map()
let verseCacheJson = null

async function loadVerseCacheJson() {
  if (verseCacheJson !== null) return verseCacheJson
  try {
    const res = await fetch('/verseCache.json')
    verseCacheJson = await res.json()
  } catch { verseCacheJson = {} }
  return verseCacheJson
}

async function fetchVerseText(ref) {
  if (verseCache.has(ref)) return verseCache.get(ref)
  // 1. Try local JSON cache first
  const local = await loadVerseCacheJson()
  if (local[ref]) {
    verseCache.set(ref, local[ref])
    return local[ref]
  }
  // 2. Fallback: fetch from wd.bible proxy
  const url = toVerseProxyUrl(ref)
  if (!url) return null
  try {
    const res = await fetch(url)
    const html = await res.text()
    const m = html.match(/<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']/i)
      || html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:description["']/i)
    if (!m) return null
    const full = m[1].replace(/\s*\|.*$/, '').trim()
    const text = full.replace(/^[^\d]*\d+:\d+\s*/, '').trim()
    verseCache.set(ref, text)
    return text
  } catch { return null }
}

function CharacterAvatar({ name, en, size = 56 }) {
  const initials = name.charAt(0)
  const hue = (name.charCodeAt(0) * 37 + (en.charCodeAt(0) || 0) * 13) % 360
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `hsl(${hue},55%,45%)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.4, fontWeight: 700, color: '#fff', flexShrink: 0
    }}>{initials}</div>
  )
}

function CharacterCard({ char, onClick }) {
  const typeTag = char.tags.find(t => ['正面榜样','警戒为主','混合型'].includes(t)) || char.type
  return (
    <div onClick={() => onClick(char)} style={{
      background: 'rgba(255,255,255,0.06)', borderRadius: 14,
      padding: '16px', cursor: 'pointer', transition: 'transform .15s, background .15s',
      display: 'flex', flexDirection: 'column', gap: 10,
      border: '1px solid rgba(255,255,255,0.08)'
    }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.11)'}
      onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <CharacterAvatar name={char.name} en={char.en} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 16, color: '#fff' }}>{char.name}</div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 2 }}>{char.en}</div>
        </div>
      </div>
      <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.7)', lineHeight: 1.5 }}>
        「{char.lesson}」
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
          background: (eraColor[char.era] || '#555') + '33',
          color: eraColor[char.era] || '#aaa', border: `1px solid ${eraColor[char.era] || '#555'}55` }}>
          {char.era}
        </span>
        <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
          background: (typeColor[typeTag] || '#888') + '22',
          color: typeColor[typeTag] || '#aaa', border: `1px solid ${typeColor[typeTag] || '#888'}44` }}>
          {typeTag}
        </span>
        {char.kingdom && (
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
            background: 'rgba(255,214,10,0.12)', color: '#ffd60a',
            border: '1px solid rgba(255,214,10,0.3)' }}>
            {char.kingdom}
          </span>
        )}
        {char.typology && (
          <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
            background: (TYPO_COLOR[char.typology.level] || '#888') + '22',
            color: TYPO_COLOR[char.typology.level] || '#aaa',
            border: `1px solid ${TYPO_COLOR[char.typology.level] || '#888'}44` }}>
            ✝ {char.typology.level}
          </span>
        )}
      </div>
    </div>
  )
}

function BulletList({ items, color }) {
  if (!items || items.length === 0) return null
  return (
    <ul style={{ margin: 0, padding: '0 0 0 4px', listStyle: 'none' }}>
      {items.map((item, i) => (
        <li key={i} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
          <span style={{ color: color || '#fff', flexShrink: 0, marginTop: 2 }}>•</span>
          <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: 14, lineHeight: 1.65 }}>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function ScriptureChip({ scripture: refStr, color = '#5ac8fa', bg = 'rgba(0,122,255,0.15)', border = 'rgba(0,122,255,0.35)' }) {
  const [text, setText] = useState(null)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [open, setOpen] = useState(false)

  const handleClick = useCallback(async (e) => {
    e.preventDefault()
    if (open) { setOpen(false); return }
    setOpen(true)
    if (!text && !loading) {
      setLoading(true)
      const t = await fetchVerseText(refStr)
      setText(t)
      setLoading(false)
    }
  }, [open, text, loading, refStr])

  const isLong = text && text.length > 100
  const displayText = isLong && !expanded ? text.slice(0, 100) + '…' : text

  return (
    <div style={{ display: 'inline-block', marginBottom: 4 }}>
      <a href={toWdBibleUrl(refStr)} onClick={handleClick}
        target="_blank" rel="noopener noreferrer"
        style={{ display: 'inline-flex', alignItems: 'center', gap: 4,
          fontSize: 12, padding: '3px 10px', borderRadius: 20,
          background: bg, color, border: `1px solid ${border}`,
          textDecoration: 'none', cursor: 'pointer', userSelect: 'none' }}>
        📖 {refStr} {open ? '▲' : '▼'}
      </a>
      {open && (
        <div style={{ marginTop: 6, padding: '10px 14px', borderRadius: 10,
          background: 'rgba(255,255,255,0.06)', border: `1px solid ${border}`,
          fontSize: 13, color: 'rgba(255,255,255,0.88)', lineHeight: 1.75,
          maxWidth: 480 }}>
          {loading ? (
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>加载中…</span>
          ) : text ? (
            <>
              <span>{displayText}</span>
              {isLong && (
                <span onClick={() => setExpanded(e => !e)}
                  style={{ color, cursor: 'pointer', marginLeft: 6, fontSize: 12 }}>
                  {expanded ? '收起' : '展开'}
                </span>
              )}
              <a href={toWdBibleUrl(refStr)} target="_blank" rel="noopener noreferrer"
                style={{ display: 'block', marginTop: 6, fontSize: 11,
                  color: 'rgba(255,255,255,0.35)', textDecoration: 'none' }}>
                新标点和合本 · 在 wd.bible 查看 ↗
              </a>
            </>
          ) : (
            <span style={{ color: 'rgba(255,255,255,0.4)' }}>点击上方链接在 wd.bible 查看 ↗</span>
          )}
        </div>
      )}
    </div>
  )
}

function ScriptureChipList({ refs, color, bg, border }) {
  if (!refs || refs.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {refs.map((r, i) => <ScriptureChip key={i} scripture={r} color={color} bg={bg} border={border} />)}
    </div>
  )
}

function CollapsibleText({ text, limit = 100, color }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = text && text.length > limit
  const displayed = isLong && !expanded ? text.slice(0, limit) + '…' : text
  return (
    <span style={{ color: color || 'rgba(255,255,255,0.75)', fontSize: 13, lineHeight: 1.6 }}>
      {displayed}
      {isLong && (
        <span onClick={() => setExpanded(e => !e)}
          style={{ color: '#5ac8fa', cursor: 'pointer', marginLeft: 4, fontSize: 12, userSelect: 'none' }}>
          {expanded ? '收起' : '展开'}
        </span>
      )}
    </span>
  )
}


// ── Mirror TTS hook ──────────────────────────────────────────────────────────
// Self-contained hook for Google Cloud TTS with native speechSynthesis fallback.

// Full-text builder — strips emoji, joins sections naturally for speech
function buildCharSpeechText(char) {
  const parts = []
  parts.push(`${char.name}，${char.en}。`)
  if (char.summary) parts.push(`人物简介：${char.summary}`)
  if (char.witness) parts.push(`信靠神的核心见证：${char.witness}`)
  if (char.typology) parts.push(`基督预表（${char.typology.level}）：${char.typology.summary}`)
  if (char.follow?.length) parts.push(`可效法的点：${char.follow.join('。')}。`)
  if (char.caution?.length) parts.push(`需要警戒的点：${char.caution.join('。')}。`)
  if (char.lesson) parts.push(`生命功课：${char.lesson}`)
  if (char.applications?.length) parts.push(`今日实际应用：${char.applications.join('。')}。`)
  if (char.prayer) parts.push(`祷告指引：${char.prayer}`)
  return parts.join('\n\n')
}

// Compact TTS control bar shown at the top of CharacterDetail
// TTSBar and SectionTTSButton delegate to the global singleton (useGlobalAudio)
const TTSBar = _TTSFullBar
const SectionTTSButton = _TTSBtn

function CharacterDetail({ char, onBack, user, token }) {
  const [commitment, setCommitment] = useState('')
  const [savingCommitment, setSavingCommitment] = useState(false)
  const [commitmentSaved, setCommitmentSaved] = useState(false)
  const [showMap, setShowMap] = useState(false)
  const journey = CHARACTER_JOURNEYS[char.name]

  async function handleSaveCommitment() {
    if (!commitment.trim() || !user) return
    setSavingCommitment(true)
    try {
      const today = new Date().toISOString().slice(0, 10)
      await saveJournal({
        date: today,
        title: char.type === '警戒' ? `以${char.name}为警戒的立志` : char.type === '混合' ? `从${char.name}身上学习的立志` : `效法${char.name}的立志`,
        scripture: char.scriptures?.slice(0, 2).join('；') || '',
        observation: `圣经人物：${char.name}（${char.en}）\n\n${char.summary || ''}`,
        reflection: char.lesson || '',
        application: commitment.trim(),
        prayer: char.prayer || '',
        mood: '',
      }, token)
      setCommitmentSaved(true)
      setTimeout(() => setCommitmentSaved(false), 3000)
      setCommitment('')
    } catch (err) {
      alert(`保存失败：${err.message}`)
    } finally {
      setSavingCommitment(false)
    }
  }
  return (
    <div style={{ padding: '0 0 40px' }}>
      <button onClick={onBack} style={{
        background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8,
        color: '#fff', padding: '8px 16px', cursor: 'pointer', fontSize: 14, marginBottom: 24
      }}>← 返回列表</button>

      {/* TTS */}
      <_TTSFullBar buildText={() => buildCharSpeechText(char)} label="整体朗读" />

      {/* Header */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', marginBottom: 28, alignItems: 'center' }}>
        <CharacterAvatar name={char.name} en={char.en} size={80} />
        <div>
          <h2 style={{ margin: 0, fontSize: 26, color: '#fff' }}>{char.name}</h2>
          <div style={{ color: 'rgba(255,255,255,0.45)', fontSize: 14, marginTop: 2 }}>{char.en}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            {char.tags.map(t => (
              <span key={t} style={{ fontSize: 11, padding: '2px 10px', borderRadius: 20,
                background: (typeColor[t] || eraColor[char.era] || '#555') + '33',
                color: typeColor[t] || eraColor[char.era] || '#ccc',
                border: `1px solid ${typeColor[t] || eraColor[char.era] || '#555'}55` }}>{t}</span>
            ))}
            <span style={{ fontSize: 11, padding: '2px 10px', borderRadius: 20,
              background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.4)' }}>
              {char.era} · {char.ref}
            </span>
          </div>
        </div>
      </div>

      {/* 1. 人物简介 */}
      <div style={sectionStyle}>
        <div style={{ ...sectionTitle, display: 'flex', alignItems: 'center', gap: 6 }}>
          📖 人物简介 <_TTSBtn text={`人物简介：${char.summary}`} />
        </div>
        <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14, lineHeight: 1.7 }}>{char.summary}</div>
      </div>

      {/* 2. 信靠神的核心见证 */}
      {char.witness && (
        <div style={{ ...sectionStyle, borderLeft: '3px solid #ffd60a', background: 'rgba(255,214,10,0.06)' }}>
          <div style={{ ...sectionTitle, color: '#ffd60a', display: 'flex', alignItems: 'center', gap: 6 }}>⭐ 信靠神的核心见证 <_TTSBtn text={`信靠神的核心见证：${char.witness}`} /></div>
          <CollapsibleText text={char.witness} limit={100} color="rgba(255,255,255,0.82)" />
        </div>
      )}

      {/* 基督预表 */}
      {char.typology && (
        <div style={{ ...sectionStyle, background: 'rgba(255,214,10,0.05)', border: '1px solid rgba(255,214,10,0.18)' }}>
          <div style={{ ...sectionTitle, color: '#e8b04b', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            ✝️ 基督预表
            <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
              background: (TYPO_COLOR[char.typology.level] || '#888') + '26',
              color: TYPO_COLOR[char.typology.level] || '#aaa',
              border: `1px solid ${TYPO_COLOR[char.typology.level] || '#888'}55`, fontWeight: 600 }}>
              {char.typology.level}
            </span>
            {char.typology.strength && (
              <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.45)', fontWeight: 400 }}>
                {STRENGTH_LABEL[char.typology.strength] || char.typology.strength}
              </span>
            )}
            <_TTSBtn text={`基督预表：${char.typology.summary}`} />
          </div>
          {char.typology.motifs && char.typology.motifs.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
              {char.typology.motifs.map(m => (
                <span key={m} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 20,
                  background: 'rgba(192,132,252,0.13)', color: '#c084fc',
                  border: '1px solid rgba(192,132,252,0.35)' }}>
                  {MOTIF_LABEL[m] || m}
                </span>
              ))}
            </div>
          )}
          <CollapsibleText text={char.typology.summary} limit={140} color="rgba(255,255,255,0.82)" />
          {char.typology.scriptures && char.typology.scriptures.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <ScriptureChipList refs={char.typology.scriptures} />
            </div>
          )}
        </div>
      )}

      {/* 三一真神的作为（按位格分组；此条不列效法点）*/}
      {Array.isArray(char.works) && char.works.length > 0 && (
        <div style={{ ...sectionStyle, borderLeft: '3px solid #c084fc', background: 'rgba(192,132,252,0.06)' }}>
          <div style={{ ...sectionTitle, color: '#c084fc', display: 'flex', alignItems: 'center', gap: 6 }}>✨ 三一真神的作为 <_TTSBtn text={char.works.map(g => `${g.group}。${g.items.join('。')}`).join('。')} /></div>
          {char.works.map((g, gi) => (
            <div key={gi} style={{ marginBottom: gi < char.works.length - 1 ? 16 : 0 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#c084fc', margin: '4px 0 8px' }}>{g.group}</div>
              <ul style={{ margin: 0, padding: '0 0 0 4px', listStyle: 'none' }}>
                {g.items.map((item, ii) => (
                  <li key={ii} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
                    <span style={{ color: '#c084fc', flexShrink: 0, marginTop: 2 }}>•</span>
                    <span style={{ color: 'rgba(255,255,255,0.82)', fontSize: 14, lineHeight: 1.7 }}>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {/* 3. 可效法的点 */}
      {char.follow && char.follow.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ ...sectionTitle, color: '#34c759', display: 'flex', alignItems: 'center', gap: 6 }}>✅ 可效法的点 <_TTSBtn text={char.follow?.join('。')} /></div>
          <ul style={{ margin: 0, padding: '0 0 0 4px', listStyle: 'none' }}>
            {char.follow.map((item, i) => {
              const refForItem = char.scriptures && char.scriptures[i]
              return (
                <li key={i} style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <span style={{ color: '#34c759', flexShrink: 0, marginTop: 2 }}>•</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
                    <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: 14, lineHeight: 1.65 }}>{item}</span>
                    {refForItem && (
                      <ScriptureChip scripture={refForItem}
                        color="#34c759" bg="rgba(52,199,89,0.12)" border="rgba(52,199,89,0.3)" />
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* 4. 需要警戒的点 */}
      {char.caution && char.caution.length > 0 && (
        <div style={{ ...sectionStyle, background: 'rgba(255,59,48,0.06)' }}>
          <div style={{ ...sectionTitle, color: '#ff6b6b', display: 'flex', alignItems: 'center', gap: 6 }}>⚠️ 需要警戒的点 <_TTSBtn text={char.caution?.join('。')} /></div>
          <ul style={{ margin: 0, padding: '0 0 0 4px', listStyle: 'none' }}>
            {char.caution.map((item, i) => {
              const refForItem = char.scriptures && char.scriptures[(char.follow?.length || 0) + i]
              return (
                <li key={i} style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                  <span style={{ color: '#ff6b6b', flexShrink: 0, marginTop: 2 }}>•</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
                    <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: 14, lineHeight: 1.65 }}>{item}</span>
                    {refForItem && (
                      <ScriptureChip scripture={refForItem}
                        color="#ff6b6b" bg="rgba(255,59,48,0.12)" border="rgba(255,59,48,0.3)" />
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* 5. 今日实际应用 */}
      {char.applications && char.applications.length > 0 && (
        <div style={{ ...sectionStyle, background: 'rgba(90,200,250,0.06)' }}>
          <div style={{ ...sectionTitle, color: '#5ac8fa', display: 'flex', alignItems: 'center', gap: 6 }}>🌱 今日实际应用 <_TTSBtn text={char.applications?.join('。')} /></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {char.applications.map((app, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ width: 22, height: 22, borderRadius: '50%', background: 'rgba(90,200,250,0.25)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, color: '#5ac8fa', flexShrink: 0, marginTop: 1 }}>{i+1}</span>
                <span style={{ color: 'rgba(255,255,255,0.78)', fontSize: 14, lineHeight: 1.65 }}>{app}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. 相关经文 */}
      {char.scriptures && char.scriptures.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ ...sectionTitle, color: '#5ac8fa' }}>📜 相关经文（点击展开和合本）</div>
          <ScriptureChipList refs={char.scriptures} />
        </div>
      )}

      {/* 生平活动轨迹地图 */}
      {journey && journey.stops && journey.stops.length > 0 && (
        <div style={sectionStyle}>
          <div style={{ ...sectionTitle, color: '#e8b04b' }}>🗺️ 生平活动轨迹</div>
          <button onClick={() => setShowMap(true)}
            style={{ width: '100%', padding: '13px 12px', background: 'rgba(232,176,75,0.13)',
              border: '1px solid rgba(232,176,75,0.42)', borderRadius: 10, color: '#e8b04b',
              fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex',
              alignItems: 'center', justifyContent: 'center', gap: 8 }}>
            🗺️ 点开地图 · 跟随{char.name}的脚踪（{journey.stops.length}站）
          </button>
        </div>
      )}
      {showMap && journey && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 200, background: '#0b1026' }}>
          <BibleMap config={buildCharacterMapConfig(char, journey)}
            onBack={() => setShowMap(false)} />
        </div>
      )}

      {/* 7. 祷告指引 */}
      <div style={{ ...sectionStyle, background: 'rgba(0,122,255,0.06)' }}>
        <div style={{ ...sectionTitle, color: '#007aff', display: 'flex', alignItems: 'center', gap: 6 }}>🙏 祷告指引 <_TTSBtn text={`祷告指引：${char.prayer}`} /></div>
        <div style={{ ...quoteStyle, borderLeftColor: '#007aff', background: 'rgba(0,122,255,0.05)',
          padding: '12px 14px', borderRadius: '0 8px 8px 0' }}>
          {char.prayer}
        </div>
      </div>

      {/* 8. 立志输入框 */}
      <div style={{ ...sectionStyle, background: 'rgba(52,199,89,0.05)', border: '1px solid rgba(52,199,89,0.2)' }}>
        <div style={{ ...sectionTitle, color: '#34c759' }}>✍️ 我的立志</div>
        <div style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)', marginBottom: 10 }}>
          {char.type === '警戒' ? `以${char.name}为警戒，今天我立志：`
            : char.type === '混合' ? `效法${char.name}的长处、以其失败为警戒，今天我立志：`
            : `效法${char.name}，今天我立志：`}
        </div>
        <textarea
          value={commitment}
          onChange={e => setCommitment(e.target.value)}
          placeholder={char.type === '警戒' ? `例：不像${char.name}那样，当面对试探时，我要警醒祷告，远离罪...` : `例：像${char.name}一样，当面对恐惧时，我要先求问神，再行动...`}
          style={{
            width: '100%', minHeight: 80, background: 'rgba(255,255,255,0.07)',
            border: '1px solid rgba(52,199,89,0.3)', borderRadius: 8, color: '#fff',
            fontSize: 14, padding: '10px 12px', resize: 'vertical', outline: 'none',
            fontFamily: 'inherit', lineHeight: 1.6, boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10, gap: 8, alignItems: 'center' }}>
          {commitmentSaved && <span style={{ fontSize: 12, color: '#34c759' }}>✅ 已存入灵修日记</span>}
          {user ? (
            <button
              onClick={handleSaveCommitment}
              disabled={!commitment.trim() || savingCommitment}
              style={{
                background: 'rgba(52,199,89,0.25)', border: '1px solid rgba(52,199,89,0.5)',
                borderRadius: 8, color: '#34c759', fontSize: 13, fontWeight: 600,
                padding: '7px 16px', cursor: 'pointer',
              }}
            >
              {savingCommitment ? '保存中...' : '📔 存入灵修日记'}
            </button>
          ) : (
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.4)' }}>登录后可保存立志</span>
          )}
        </div>
      </div>
    </div>
  )
}

const sectionStyle = { marginBottom: 20, background: 'rgba(255,255,255,0.05)', borderRadius: 12, padding: '16px 18px' }
const sectionTitle = { fontWeight: 700, fontSize: 15, color: '#fff', marginBottom: 10 }
const quoteStyle = { borderLeft: '3px solid #34c759', paddingLeft: 14, color: 'rgba(255,255,255,0.75)', fontSize: 14, lineHeight: 1.7, fontStyle: 'italic' }

function Section({ title, children }) {
  return (
    <div style={sectionStyle}>
      <div style={sectionTitle}>{title}</div>
      <div style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14, lineHeight: 1.7 }}>{children}</div>
    </div>
  )
}

function ThemeDetail({ theme, characters, onBack, onCharClick }) {
  const themeChars = characters.filter(c => theme.characterIds.includes(c.id))
  return (
    <div style={{ padding: '0 0 40px' }}>
      <button onClick={onBack} style={{
        background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8,
        color: '#fff', padding: '8px 16px', cursor: 'pointer', fontSize: 14, marginBottom: 24
      }}>← 返回主题</button>

      <div style={{ textAlign: 'center', marginBottom: 28 }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>{theme.emoji}</div>
        <h2 style={{ margin: 0, fontSize: 26, color: '#fff' }}>{theme.title}</h2>
        <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 13, marginTop: 8, fontStyle: 'italic' }}>
          {theme.scripture}
        </div>
      </div>

      <Section title="导言">{theme.intro}</Section>

      <div style={{ marginBottom: 20 }}>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#fff', marginBottom: 12 }}>相关人物</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(180px,1fr))', gap: 12 }}>
          {themeChars.map(c => <CharacterCard key={c.id} char={c} onClick={onCharClick} />)}
        </div>
      </div>

      <Section title="📌 主题总结">{theme.summary}</Section>

      <div style={sectionStyle}>
        <div style={sectionTitle}>🔑 如何应用</div>
        {theme.howToApply.map((step, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
            <span style={{ width: 22, height: 22, borderRadius: '50%', background: '#007aff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 700, color: '#fff', flexShrink: 0 }}>{i+1}</span>
            <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 14, lineHeight: 1.6 }}>{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function MirrorPage({ user, token, guidance, onBack }) {
  const [view, setView] = useState('list') // 'list' | 'themes' | 'character' | 'theme'
  const [selectedChar, setSelectedChar] = useState(null)
  const [selectedTheme, setSelectedTheme] = useState(null)
  const [search, setSearch] = useState('')
  const [filterEra, setFilterEra] = useState('全部')
  const [filterRole, setFilterRole] = useState('全部')
  const [filterType, setFilterType] = useState('全部')
  const [filterTypo, setFilterTypo] = useState('全部')
  const [filterMotif, setFilterMotif] = useState('全部')
  const [sort, setSort] = useState('era')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [filterKingdom, setFilterKingdom] = useState('全部')

  const KINGDOMS = ['全部', '统一王国', '南国犹大', '北国以色列', '外邦君王']
  // Succession order IDs for kings
  const KING_ORDER = [
    24,25,29,158, // 统一王国
    82,219,121,31,220,221,222,169,130,187,123,124,34,125,223,188,224,225,226,227, // 南国
    195,228,229,30,126,230,231,232,127, // 北国
    233,94,234,203,117 // 外邦（法老/古列/尼布甲尼撒/亚哈随鲁/希律）
  ]

  const filtered = useMemo(() => {
    let list = [...MIRROR_CHARACTERS]
    if (search) {
      const q = search.toLowerCase()
      list = list.filter(c =>
        c.name.includes(q) ||
        (c.en || '').toLowerCase().includes(q) ||
        (c.era || '').includes(q) ||
        (c.role || '').includes(q) ||
        (c.lesson || '').includes(q) ||
        (c.summary || '').includes(q) ||
        (c.witness || '').includes(q) ||
        (c.ref || '').toLowerCase().includes(q) ||
        (c.tags || []).some(t => t.includes(q))
      )
    }
    if (filterEra !== '全部') list = list.filter(c => c.era === filterEra)
    if (filterRole !== '全部') list = list.filter(c => c.role === filterRole)
    if (filterType !== '全部') list = list.filter(c => c.tags.includes(filterType))
    if (filterTypo !== '全部') {
      if (filterTypo === '有预表') list = list.filter(c => c.typology)
      else if (filterTypo === '强预表') list = list.filter(c => c.typology && (c.typology.level === '强预表' || c.typology.level === '极强预表'))
      else if (filterTypo === '弱预表/影子') list = list.filter(c => c.typology && c.typology.level === '弱预表')
      else if (filterTypo === '反衬预表') list = list.filter(c => c.typology && c.typology.level === '反面预表')
      else list = list.filter(c => c.typology && c.typology.level === filterTypo)
    }
    if (filterMotif !== '全部') {
      const def = MOTIF_DEF[filterMotif]
      if (def) list = list.filter(c =>
        (def.id && ((c.typology && c.typology.motifs) || []).includes(def.id)) ||
        def.names.includes(c.name) ||
        (def.negative && c.typology && c.typology.strength === 'negative_contrast'))
    }
    if (filterRole === '君王' && filterKingdom !== '全部') list = list.filter(c => c.kingdom === filterKingdom)
    const eraOrder = ['族长时代','出埃及时代','士师时代','进入迦南时代','王国时代','被掳归回时代','新约时代']
    if (filterRole === '君王') {
      list.sort((a, b) => {
        const ai = KING_ORDER.indexOf(a.id), bi = KING_ORDER.indexOf(b.id)
        if (ai === -1 && bi === -1) return 0
        if (ai === -1) return 1
        if (bi === -1) return -1
        return ai - bi
      })
    } else if (sort === 'name') {
      list.sort((a, b) => {
        const eraDiff = eraOrder.indexOf(a.era) - eraOrder.indexOf(b.era)
        if (eraDiff !== 0) return eraDiff
        return a.name.localeCompare(b.name, 'zh')
      })
    } else {
      list.sort((a, b) => {
        const eraDiff = eraOrder.indexOf(a.era) - eraOrder.indexOf(b.era)
        if (eraDiff !== 0) return eraDiff
        return a.id - b.id
      })
    }
    return list
  }, [search, filterEra, filterRole, filterType, filterTypo, filterMotif, filterKingdom, sort])

  const openChar = (char) => { setSelectedChar(char); setView('character') }
  const openTheme = (theme) => { setSelectedTheme(theme); setView('theme') }

  // 情绪/引导推荐人物
  const recommendedChars = useMemo(() => {
    if (!guidance) return []
    const emotions = guidance.core_emotions || []
    const tagMap = {
      '焦虑': ['信心', '平安'], '恐惧': ['信心', '勇气'], '悲伤': ['盼望', '安慰'],
      '愤怒': ['饶恕', '谦卑'], '孤独': ['信靠', '同行'], '迷茫': ['智慧', '引导'],
      '内疚': ['恩典', '饶恕', '悔改'], '绝望': ['盼望', '拯救'], '感恩': ['赞美', '信靠'],
    }
    const wantedTags = new Set()
    emotions.forEach(e => (tagMap[e] || []).forEach(t => wantedTags.add(t)))
    if (wantedTags.size === 0) return []
    return MIRROR_CHARACTERS
      .filter(c => c.tags.some(t => wantedTags.has(t)) && c.type !== '警戒为主')
      .sort((a, b) => b.tags.filter(t => wantedTags.has(t)).length - a.tags.filter(t => wantedTags.has(t)).length)
      .slice(0, 3)
  }, [guidance])

  if (view === 'character' && selectedChar) {
    return (
      <div style={{ padding: '20px 16px' }}>
        <CharacterDetail char={selectedChar} onBack={() => setView('list')} user={user} token={token} />
      </div>
    )
  }

  if (view === 'theme' && selectedTheme) {
    return (
      <div style={{ padding: '20px 16px' }}>
        <ThemeDetail
          theme={selectedTheme}
          characters={MIRROR_CHARACTERS}
          onBack={() => setView('themes')}
          onCharClick={openChar}
        />
      </div>
    )
  }

  if (view === 'themes') {
    return (
      <div style={{ padding: '20px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <button onClick={() => setView('list')} style={{
            background: 'rgba(255,255,255,0.1)', border: 'none', borderRadius: 8,
            color: '#fff', padding: '8px 16px', cursor: 'pointer', fontSize: 14
          }}>← 人物列表</button>
          <h2 style={{ margin: 0, fontSize: 20, color: '#fff' }}>主题合集</h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(240px,1fr))', gap: 14 }}>
          {MIRROR_THEMES.map(t => (
            <div key={t.id} onClick={() => openTheme(t)} style={{
              background: 'rgba(255,255,255,0.06)', borderRadius: 14, padding: '18px',
              cursor: 'pointer', border: '1px solid rgba(255,255,255,0.08)',
              transition: 'background .15s'
            }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.11)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.06)'}
            >
              <div style={{ fontSize: 32, marginBottom: 8 }}>{t.emoji}</div>
              <div style={{ fontWeight: 700, fontSize: 16, color: '#fff', marginBottom: 6 }}>{t.title}</div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', lineHeight: 1.5 }}>{t.intro.slice(0, 60)}…</div>
              <div style={{ marginTop: 10, fontSize: 11, color: 'rgba(255,255,255,0.3)' }}>
                {t.characterIds.length} 位人物
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Main list view
  return (
    <div style={{ display: 'flex', gap: 0, minHeight: '100%' }}>
      {/* Sidebar */}
      <div style={{
        flexShrink: 0,
        background: 'rgba(0,0,0,0.2)', borderRight: '1px solid rgba(255,255,255,0.06)',
        padding: sidebarOpen ? '12px 10px' : '12px 6px',
        width: sidebarOpen ? 'max-content' : 'auto',
        minWidth: sidebarOpen ? 80 : 'auto',
      }}>
        <button onClick={() => setSidebarOpen(!sidebarOpen)} style={{
          background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)',
          cursor: 'pointer', fontSize: 14, marginBottom: sidebarOpen ? 12 : 0, padding: 0,
          whiteSpace: 'nowrap'
        }}>{sidebarOpen ? '◀ 筛选' : <span style={{ writingMode: 'vertical-rl', letterSpacing: 2, fontSize: 12 }}>筛选</span>}</button>
        {sidebarOpen && (
          <>
            <FilterGroup label="时代" value={filterEra} options={ERAS} onChange={setFilterEra} />
            <FilterGroup label="身份" value={filterRole} options={ROLES} onChange={v => { setFilterRole(v); setFilterKingdom('全部') }} />
            {filterRole === '君王' && (
              <FilterGroup label="王国" value={filterKingdom} options={KINGDOMS} onChange={setFilterKingdom} />
            )}
            <FilterGroup label="类型" value={filterType} options={TYPES} onChange={setFilterType} />
            <FilterGroup label="预表强度" value={filterTypo} options={TYPO_FILTER} onChange={setFilterTypo} />
            <FilterGroup label="预表母题/类别 · 基督是" value={filterMotif} options={MOTIF_FILTER} onChange={setFilterMotif} />
            <button onClick={() => { setFilterEra('全部'); setFilterRole('全部'); setFilterType('全部'); setFilterTypo('全部'); setFilterMotif('全部'); setFilterKingdom('全部'); setSearch('') }}
              style={{ width: '100%', marginTop: 8, padding: '6px 8px', borderRadius: 8, border: 'none',
                background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 12,
                whiteSpace: 'nowrap' }}>
              重置筛选
            </button>
          </>
        )}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, padding: '16px', overflow: 'auto' }}>
        {/* Top bar */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="搜索人物"
            style={{ flex: 1, minWidth: 160, padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)',
              background: 'rgba(255,255,255,0.08)', color: '#fff', fontSize: 14, outline: 'none' }}
          />
          <select value={sort} onChange={e => setSort(e.target.value)} style={{
            padding: '8px 10px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)',
            background: 'rgba(30,30,40,0.9)', color: '#fff', fontSize: 13, cursor: 'pointer'
          }}>
            <option value="era">按年代</option>
            <option value="name">按名字</option>
          </select>
          <button onClick={() => setView('themes')} style={{
            padding: '8px 14px', borderRadius: 8, border: 'none',
            background: '#007aff', color: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 600
          }}>主题合集 ✨</button>
        </div>

        {recommendedChars.length > 0 && (
          <div style={{
            marginBottom: 18, padding: '14px 16px',
            background: 'linear-gradient(135deg,rgba(88,86,214,0.18),rgba(0,122,255,0.1))',
            border: '1px solid rgba(88,86,214,0.35)', borderRadius: 12,
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#c4b5fd', marginBottom: 10, letterSpacing: '0.05em' }}>
              ✨ 根据你的情绪，推荐认识这几位圣经人物
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {recommendedChars.map(c => (
                <button key={c.id} onClick={() => openChar(c)} style={{
                  background: 'rgba(88,86,214,0.2)', border: '1px solid rgba(88,86,214,0.4)',
                  borderRadius: 20, padding: '5px 14px', color: '#e0d4ff', fontSize: 13,
                  cursor: 'pointer', fontWeight: 600,
                }}>
                  {c.name} <span style={{ fontSize: 11, opacity: 0.6, fontWeight: 400 }}>{c.en}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', marginBottom: 12 }}>
          共 {filtered.length} 位人物
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))',
          gap: 14
        }}>
          {filtered.map(c => <CharacterCard key={c.id} char={c} onClick={openChar} />)}
        </div>
      </div>
    </div>
  )
}

function FilterGroup({ label, value, options, onChange }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', marginBottom: 5, fontWeight: 600, letterSpacing: 1 }}>
        {label}
      </div>
      {options.map(o => (
        <div key={o} onClick={() => onChange(o)} style={{
          padding: '4px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 12,
          color: value === o ? '#fff' : 'rgba(255,255,255,0.5)',
          background: value === o ? 'rgba(0,122,255,0.3)' : 'transparent',
          marginBottom: 2, whiteSpace: 'nowrap'
        }}>{o}</div>
      ))}
    </div>
  )
}

