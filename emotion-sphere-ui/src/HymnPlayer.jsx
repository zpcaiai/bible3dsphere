import { useEffect, useRef, useState } from 'react'
import TIMINGS from './hymnTimings'

// 诗歌音频托管在 Cloudflare R2（不放进 git，避免 HF 对二进制的限制）。
// 在前端构建环境设置 VITE_HYMN_AUDIO_BASE，例如 https://<你的R2公开域名>/hymns
// 未设置时回退到本地 /hymns（开发用）。
// mp3 托管在 R2（cdn.holiness.uk/hymns/，由 scripts/hymns/generate_hymn_audio.py 合成后上传）。
// 默认走 CDN；本地开发想用 public/hymns/ 时设 VITE_HYMN_AUDIO_BASE=/hymns。
const HYMN_AUDIO_BASE = (import.meta.env.VITE_HYMN_AUDIO_BASE || 'https://cdn.holiness.uk/hymns').replace(/\/+$/, '')
const hymnAudioUrl = (h) => `${HYMN_AUDIO_BASE}/${encodeURIComponent(h.file || (h.id + '.mp3'))}`

/**
 * HymnPlayer — 诗歌播放子页
 *
 * 内置经典圣诗(均为公有领域)。替换/新增资源只需：
 *   1) 把 mp3 放到  public/hymns/<id>.mp3
 *   2) 把曲谱图片放到 public/hymns/<id>.png  (五线谱/简谱皆可)
 * 缺资源时优雅降级：音频显示「待添加」，曲谱显示内置 SVG 占位。
 */

const HYMNS = [
  {
    id: 'amazing-grace',
    file: '075p2-奇異恩典-AMAZING-GRACE.mp3',
    title: '奇异恩典',
    en: 'Amazing Grace',
    author: '词 John Newton, 1779',
    note: '全球流传最广的圣诗。前贩奴船长约翰·牛顿悔改后所写，真实表达从罪恶中被拯救的感恩。',
    lyrics: [
      '奇异恩典 何等甘甜\n我罪已得赦免\n前我失丧 今被寻回\n瞎眼今得看见',
      '如此恩典 使我敬畏\n使我心得安慰\n初信之时 即蒙恩惠\n真是何等宝贵',
      '许多危险 试炼网罗\n我已安然经过\n靠主恩典 安全不怕\n更引导我归家',
      '将来在天 安居万年\n光明灿烂如日\n好像最初 蒙恩景况\n赞美永不减少',
    ],
  },
  {
    id: 'it-is-well',
    file: '359p2-我心靈得安寧-IT-IS-WELL-WITH-MY-SOUL.mp3',
    title: '我心灵得安宁',
    en: 'It Is Well with My Soul',
    author: '词 Horatio Spafford, 1873',
    note: '芝加哥律师斯帕福德在家产毁于大火、四个女儿于海难全部丧生后，行经出事海域写下此歌。充满安慰的力量。',
    lyrics: [
      '有时享平安 如江河平又稳\n有时忧伤来似浪滚\n不论何环境 主已教导我说\n我心灵得安宁 得安宁',
      '我心灵 得安宁\n我心灵得安宁 得安宁',
      '撒但虽搅扰 试炼虽来侵\n主已应许必看顾我\n基督既看顾 何必再忧愁\n主流出宝血 为救我',
      '我罪虽多 但我已蒙救赎\n何等荣耀 一念及此\n我罪钉十架 不再归我负\n赞美主 赞美主 我心灵',
    ],
  },
  {
    id: 'how-great-thou-art',
    file: '002p-祢真偉大-HOW-GREAT-THOU-ART.mp3',
    title: '你真伟大',
    en: 'How Great Thou Art',
    author: '词 Carl Boberg, 1885',
    note: '气势磅礴，常用于崇拜赞美的高潮，颂赞上帝创造宇宙万物的伟大。',
    lyrics: [
      '主啊我神 我每逢举目观看\n你手所造 一切奇妙大工\n看见星宿 又听到隆隆雷声\n你的大能 遍满了宇宙中',
      '我灵歌唱 赞美救主我神\n你真伟大 何等伟大\n我灵歌唱 赞美救主我神\n你真伟大 何等伟大',
      '当我想到 神竟愿差祂儿子\n降世舍命 我几乎不领会\n主在十架 甘愿背我的重担\n流血舍身 为要赦免我罪',
      '当主再来 欢呼声响彻天空\n何等喜乐 主接我回天家\n我要跪下 谦恭地崇拜敬奉\n并要颂扬 神啊你真伟大',
    ],
  },
  {
    id: 'holy-holy-holy',
    file: '圣域三一歌.mp3',
    title: '圣哉三一歌',
    en: 'Holy, Holy, Holy! Lord God Almighty',
    author: '词 Reginald Heber, 1826',
    note: '极其庄严，是主日崇拜（尤其传统教会）宣召或开会时最常唱的传统圣诗之一。',
    lyrics: [
      '圣哉 圣哉 圣哉\n全能大主宰\n清晨我众歌颂\n同声赞美主名',
      '圣哉 圣哉 圣哉\n慈悲与全能\n三位同荣一体\n万古永远长存',
      '圣哉 圣哉 圣哉\n众圣都崇敬\n放下黄金冠冕\n环绕在主宝座',
      '圣哉 圣哉 圣哉\n全能大主宰\n你的化工尽都\n颂赞主名荣耀',
    ],
  },
  {
    id: 'blessed-assurance',
    file: '050b-有福的確據-BLESSED-ASSURANCE-JESUS-IS-MINE.mp3',
    title: '有福确知',
    en: 'Blessed Assurance',
    author: '词 Fanny Crosby, 1873',
    note: '盲眼诗人克罗斯比最著名的作品，全球主日聚会最常唱的宣信诗歌之一。旋律欢快坚定，唱出对救恩的把握与喜乐。',
    lyrics: [
      '有福确知 耶稣属我\n何等荣耀 向我显明\n我是后嗣 已蒙救赎\n圣灵重生 宝血洗净',
      '这是我信息 我的诗歌\n赞美我救主 昼夜唱和\n这是我信息 我的诗歌\n赞美我救主 昼夜唱和',
      '完全的顺服 完全的喜乐\n荣耀异象现我心中\n天使临格 带下慈爱\n慈声细语 由天传颂',
      '完全的顺服 平安无虑\n有主同在 满有福气\n时刻儆醒 时刻等候\n仰望荣耀 充满我心',
    ],
  },
  {
    id: 'safe-in-arms',
    file: 'safe-in-arms.mp3',
    title: '安全在耶稣手中',
    en: 'Safe in the Arms of Jesus',
    author: '词 Fanny Crosby, 1868',
    note: '谱曲家弹出一段旋律问克罗斯比听到什么，盲眼的她立刻说「我听到了安全在耶稣手中」，几分钟内写下歌词。常于追思礼拜或患难中唱起，带来极大安慰。',
    lyrics: [
      '安全在耶稣手中\n安全在主怀里\n有主慈爱的膀臂\n时常环绕保护',
      '安全在耶稣手中\n安全在主怀里\n听啊救恩的声音\n响彻在天庭里',
      '在主怀中安息\n免受试探苦害\n脱离一切的忧愁\n远离罪恶网罗',
      '只略等候些时\n不久黑夜过去\n只略等候些时\n直到主再降临',
    ],
  },
  {
    id: 'joy-to-the-world',
    file: '117o-普世歡騰-Joy-To-The-World.mp3',
    title: '普世欢腾',
    en: 'Joy to the World',
    author: '词 Isaac Watts, 1719',
    note: '全球最著名的圣诞赞美诗，欢腾迎接救主降临。',
    lyrics: [
      '普世欢腾 救主下降\n大地接她君王\n惟愿众心 预备地方\n诸天万物歌唱\n诸天万物歌唱\n诸天 诸天万物歌唱',
      '普世欢腾 主治万方\n民众都当歌唱\n沃野洪涛 山石平原\n响应歌声嘹亮\n响应歌声嘹亮\n响应 响应歌声嘹亮',
      '主以真理 恩治万方\n要使万邦证明\n上主公义 无限荣光\n主爱奇妙莫名\n主爱奇妙莫名\n主爱 主爱奇妙莫名',
    ],
  },
  {
    id: 'when-i-survey',
    file: '9-奇妙十架.mp3',
    title: '当我思念奇妙十架',
    en: 'When I Survey the Wondrous Cross',
    author: '词 Isaac Watts, 1707',
    note: '被许多神学家评为「英语世界中最伟大的圣诗」。受难节、圣餐礼拜时全场齐唱，往往令人动容。',
    lyrics: [
      '每逢思念奇妙十架\n荣耀之主在上悬挂\n从前所夸 今觉空虚\n甘心舍弃 当作粪土',
      '愿主禁我别有所夸\n惟夸我主舍身十架\n前所珍爱 虚荣浮华\n为主之故 全都撇下',
      '看主圣首 圣手圣足\n慈爱忧愁 融成一处\n如此奇恩 如此宏爱\n何等荣冠 何等苦楚',
      '尽献所有 尚觉菲薄\n主爱如此 奇妙广博\n愿献我心 我命所有\n感谢主恩 永无止息',
    ],
  },
  {
    id: 'mighty-fortress',
    file: '081b-堅固保障-A-MIGHTY-FORTRESS-IS-OUR-GOD.mp3',
    title: '坚固保障',
    en: 'A Mighty Fortress Is Our God',
    author: '词 Martin Luther, 1529',
    note: '宗教改革时期的「战歌」。旋律充满力量，唱起来如军队前行，震撼人心，是新教教会的基石之作。',
    lyrics: [
      '上主是我坚固保障\n庄严稳固永坚强\n上主使我安稳前航\n助我乘风破巨浪',
      '惟靠我们自己力量\n我们斗争必失败\n但有一位适时兴起\n是主耶稣亲拣选',
      '我神乃是大能堡垒\n抵御世仇敌侵犯\n世仇仍在向我夸胜\n奸狡兼有大权能',
      '主言更比万事坚强\n纵有撒但显凶猛\n我们不怕因神为我\n靠主得胜建永恒',
    ],
  },
  {
    id: 'o-to-be-like-thee',
    file: '342-主我願像祢-O-TO-BE-LIKE-THEE.mp3',
    title: '主我愿像祢',
    en: 'O To Be Like Thee',
    author: '词 Thomas O. Chisholm, 1897',
    note: '诗人渴望生命被塑造、完全像基督：柔和谦卑、圣洁有怜悯。',
    lyrics: [
      '荣耀的救主 我深愿像祢\n这是我祷告 我的盼望\n我甘愿舍弃 世上的财宝\n披戴主基督 完美形像',
      '（副歌）\n主我愿像祢 主我愿像祢\n荣耀的救主 像祢纯洁\n愿祢的甘甜 愿祢的丰满\n愿祢的圣形 深印我灵',
      '主我愿像祢 有怜悯心肠\n温柔和宽恕 慈爱善良\n帮助孤苦者 鼓励灰心者\n领人归基督 寻找亡羊',
      '主我愿像祢 谦卑且圣洁\n忍耐并勇敢 恭顺虔诚\n甘心受苦难 恶待或讥诮\n宁可受痛苦 使人得救',
      '主我愿像祢 求主来浇灌\n将爱与圣灵 充满我心\n使我成圣殿 合乎祢居住\n使我的生命 配祢荣形',
    ],
  },
  {
    id: 'all-the-way',
    file: '一路引导歌.mp3',
    title: '一路引导歌',
    en: 'All the Way My Savior Leads Me',
    author: '词 Fanny Crosby, 1875',
    note: '盲眼女诗人芬妮·克罗斯比的感恩之作：救主一路引导，我还要求什么？',
    lyrics: [
      '一路我蒙救主引导\n陈腐事何须计较\n难道我还疑祂爱心\n毕生既由祂领导\n神圣安慰 属天生活\n凭信我可安然享受\n我深知道 凡事临到\n主必为我安排妥',
      '一路我蒙救主引导\n鼓励我走每一步\n赐我灵粮使我饱足\n帮助我胜过试炼\n我灵虽然疲倦干渴\n举步艰难几乎跌倒\n看哪眼前有一磐石\n喜乐活泉向我涌流',
      '一路我蒙救主引导\n主爱何等丰富甘甜\n祂曾应许在父家里\n为我备有安息地点\n当我灵魂披上荣体\n飞进天府快乐无边\n千秋万岁我仍传扬\n耶稣一路引导我',
    ],
  },
  {
    id: 'amazing-grace-choir',
    file: '奇异恩典-合唱（四声部）.mp3',
    title: '奇异恩典（四声部合唱）',
    en: 'Amazing Grace (SATB)',
    author: '词 John Newton, 1779',
    note: '奇异恩典的四声部合唱版本，声部交织更显恩典的丰盛。',
    lyrics: [
      '奇异恩典 何等甘甜\n我罪已得赦免\n前我失丧 今被寻回\n瞎眼今得看见',
      '如此恩典 使我敬畏\n使我心得安慰\n初信之时 即蒙恩惠\n真是何等宝贵',
      '许多危险 试炼网罗\n我已安然经过\n靠主恩典 安全不怕\n更引导我归家',
      '将来在天 安居万年\n光明灿烂如日\n好像最初 蒙恩景况\n赞美永不减少',
    ],
  },
]

function fmtTime(s) {
  if (!s || isNaN(s) || !isFinite(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}

// 内置曲谱占位：一段简单的五线谱 SVG，资源缺失时显示
function ScorePlaceholder({ title }) {
  const lineY = [22, 34, 46, 58, 70]
  return (
    <svg className="hymn-score-svg" viewBox="0 0 320 110" preserveAspectRatio="xMidYMid meet">
      <text x="160" y="14" textAnchor="middle" className="hymn-score-svg-title">{title}</text>
      {lineY.map((y) => (
        <line key={y} x1="16" y1={y} x2="304" y2={y} stroke="rgba(255,255,255,0.28)" strokeWidth="1" />
      ))}
      <text x="24" y="62" className="hymn-score-svg-clef">𝄞</text>
      {[70, 110, 150, 190, 230, 270].map((x, i) => (
        <g key={x}>
          <ellipse cx={x} cy={58 - (i % 4) * 12} rx="6" ry="4.2" fill="rgba(255,215,0,0.85)" transform={`rotate(-18 ${x} ${58 - (i % 4) * 12})`} />
          <line x1={x + 5.5} y1={58 - (i % 4) * 12} x2={x + 5.5} y2={58 - (i % 4) * 12 - 24} stroke="rgba(255,215,0,0.85)" strokeWidth="1.4" />
        </g>
      ))}
      <text x="160" y="98" textAnchor="middle" className="hymn-score-svg-hint">曲谱占位 · 放入 public/hymns 后自动替换</text>
    </svg>
  )
}

export default function HymnPlayer() {
  const [idx, setIdx] = useState(() => {
    const dl = typeof window !== 'undefined' ? window.__deepLink : null
    if (dl && dl.kind === 'hymn') {
      const i = HYMNS.findIndex(h => h.id === dl.id)
      if (i >= 0) { window.__deepLink = null; return i }
    }
    return 0
  })
  const [playing, setPlaying] = useState(false)
  const [cur, setCur] = useState(0)
  const [dur, setDur] = useState(0)
  const [audioErr, setAudioErr] = useState(false)
  const [scoreErr, setScoreErr] = useState(false)
  const audioRef = useRef(null)

  const hymn = HYMNS[idx]

  useEffect(() => {
    setPlaying(false)
    setCur(0)
    setDur(0)
    setAudioErr(false)
    setScoreErr(false)
    const a = audioRef.current
    if (a) { a.pause(); a.currentTime = 0 }
  }, [idx])

  const togglePlay = () => {
    const a = audioRef.current
    if (!a || audioErr) return
    if (playing) { a.pause() } else { a.play().catch(() => setAudioErr(true)) }
  }

  const seek = (e) => {
    const a = audioRef.current
    if (!a || !dur) return
    a.currentTime = (Number(e.target.value) / 100) * dur
  }

  const pct = dur ? (cur / dur) * 100 : 0

  const kLines = (!hymn.file && TIMINGS[hymn.id] && TIMINGS[hymn.id].lines) || []  // 真实录音与合成版时间轴不匹配，停用逐字高亮
  let activeLine = -1
  if (playing || cur > 0) {
    for (let i = 0; i < kLines.length; i++) if (cur >= kLines[i].t) activeLine = i
  }

  return (
    <div className="hymn-page">
      {/* 诗歌选择 */}
      <div className="hymn-chips">
        {HYMNS.map((h, i) => (
          <button
            key={h.id}
            className={`hymn-chip ${i === idx ? 'active' : ''}`}
            onClick={() => setIdx(i)}
          >
            {h.title}
          </button>
        ))}
      </div>

      {/* 标题信息 */}
      <div className="hymn-meta">
        <div className="hymn-meta-title">
          {hymn.title}
          <span
            onClick={() => {
              const url = `${window.location.origin}/?share=hymn:${hymn.id}`
              const data = { title: `圣诗《${hymn.title}》`, text: `圣诗《${hymn.title}》— 在属灵星球在线听唱（五线谱+逐句跟唱）`, url }
              if (navigator.share) { navigator.share(data).catch(() => {}) }
              else if (navigator.clipboard) {
                navigator.clipboard.writeText(`${data.text} ${url}`)
                if (window.showToast) window.showToast('分享链接已复制', 'success')
              }
            }}
            style={{ marginLeft: 10, fontSize: 12, padding: '3px 10px', borderRadius: 14, cursor: 'pointer',
              background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.16)',
              color: 'rgba(255,255,255,0.65)', verticalAlign: 'middle', userSelect: 'none' }}>↗ 分享</span>
        </div>
        <div className="hymn-meta-en">{hymn.en}</div>
        <div className="hymn-meta-author">{hymn.author}</div>
        {hymn.note && <div className="hymn-meta-note">{hymn.note}</div>}
      </div>

      {/* 曲谱展示 */}
      <div className="hymn-score">
        {!scoreErr ? (
          <img
            src={`/hymns/${hymn.id}.png`}
            alt={`${hymn.title} 曲谱`}
            className="hymn-score-img"
            onError={() => setScoreErr(true)}
          />
        ) : (
          <ScorePlaceholder title={hymn.title} />
        )}
      </div>

      {/* 播放器 */}
      <div className="hymn-player">
        <audio
          ref={audioRef}
          src={hymnAudioUrl(hymn)}
          onTimeUpdate={(e) => setCur(e.target.currentTime)}
          onLoadedMetadata={(e) => setDur(e.target.duration)}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
          onError={() => setAudioErr(true)}
          preload="metadata"
        />
        <button className="hymn-play-btn" onClick={togglePlay} disabled={audioErr} aria-label={playing ? '暂停' : '播放'}>
          {playing ? (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1" /><rect x="14" y="5" width="4" height="14" rx="1" /></svg>
          ) : (
            <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z" /></svg>
          )}
        </button>
        <span className="hymn-time">{fmtTime(cur)}</span>
        <input
          className="hymn-seek"
          type="range" min="0" max="100" step="0.1"
          value={pct}
          onChange={seek}
          disabled={audioErr}
          style={{ '--pct': `${pct}%` }}
        />
        <span className="hymn-time">{fmtTime(dur)}</span>
      </div>
      {audioErr && (
        <div className="hymn-audio-hint">🎵 音频待添加：把文件放到 <code>public/hymns/{hymn.id}.mp3</code></div>
      )}

      {/* 跟唱(逐行 + 逐字高亮，跟随音频) */}
      {kLines.length > 0 && (
        <div className="hymn-karaoke">
          {kLines.map((ln, i) => (
            <div key={i} className={`hymn-kline ${i === activeLine ? 'active' : ''}`}>
              {i === activeLine && ln.syls
                ? ln.syls.map((sy, j) => {
                    const next = ln.syls[j + 1]
                    const sungDone = cur >= (next ? next.t : ln.t + 99)
                    const singing = cur >= sy.t && !sungDone
                    return (
                      <span key={j} className={`hymn-kchar ${sungDone ? 'done' : ''} ${singing ? 'now' : ''}`}>{sy.ch}</span>
                    )
                  })
                : ln.text}
            </div>
          ))}
        </div>
      )}

      {/* 完整歌词 */}
      <div className="hymn-lyrics-label">完整歌词</div>
      <div className="hymn-lyrics">
        {hymn.lyrics.map((stanza, i) => (
          <div className="hymn-stanza" key={i}>
            <div className="hymn-stanza-no">{i + 1}</div>
            <div className="hymn-stanza-text">{stanza}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
