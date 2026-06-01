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

  {"id": "utmost", "title": "至高无上的奉献（导读）", "subtitle": "挑战彻底奉献的每日灵粮", "author": "原著 奥斯瓦尔德·钱伯斯（Oswald Chambers, My Utmost for His Highest）", "emoji": "⭐", "color": "#f59e0b", "kind": "pdf", "pdf": "/book/至高无上的奉献-导读.pdf", "blurb": "介绍钱伯斯这部挑战彻底降服、毫无保留献给神的每日灵修经典，许多宣教士的案头灵粮。", "chapters": [{"title": "关于这本书", "text": "《至高无上的奉献》是奥斯瓦尔德·钱伯斯的每日灵修经典（由其妻整理其讲道编成），全年三百六十五篇，以简短有力的篇章挑战信徒彻底降服、毫无保留地献给神。一个多世纪以来，被无数宣教士与信徒视为案头灵粮。"}, {"title": "核心信息", "text": "不是追求自己的「至高」，而是把自己的「至上」献给神的「至高」。它一再呼召人离开以经历、感觉、成就为中心的信仰，进入以神为中心的舍己、顺服与全然摆上。"}, {"title": "怎么读", "text": "每天读一篇，安静默想，把「彻底降服」落实为今天一个具体的顺服。它的话常常扎心，重在被挑战、被对付，而非只是被感动。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "presence", "title": "与神同在（导读）", "subtitle": "在日常中时刻亲近神", "author": "原著 劳伦斯弟兄（Brother Lawrence, Practicing the Presence of God）", "emoji": "🙏", "color": "#34c759", "kind": "pdf", "pdf": "/book/与神同在书-导读.pdf", "blurb": "介绍劳伦斯弟兄教人在最平凡日常中时刻操练与神同在的简短而深刻的经典。", "chapters": [{"title": "关于这本书", "text": "《与神同在》是十七世纪修道院厨役劳伦斯弟兄的谈话与书信集，篇幅短小却极其深刻，教导人如何在最平凡的日常（洗碗、做工、走路）中，时刻操练与神同在。"}, {"title": "核心信息", "text": "亲近神不必等到「属灵时刻」，而是以爱在每一件小事中转向神，渐渐养成时刻活在神面前的习惯。最隐藏、最琐碎的工作，照样可以充满神的同在。"}, {"title": "怎么读", "text": "选一件你最普通的日常事，一边做一边与神说话，今天就开始操练「与神同在」。重在去行，而非只是读。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "purpose", "title": "标杆人生（导读）", "subtitle": "明白神所定的人生目的", "author": "原著 瑞克·华伦（Rick Warren, The Purpose Driven Life）", "emoji": "🎯", "color": "#06b6d4", "kind": "pdf", "pdf": "/book/标杆人生-导读.pdf", "blurb": "介绍华伦以四十天带人思考「我为什么活着」、发现神所定五个人生目的的畅销灵修书。", "chapters": [{"title": "关于这本书", "text": "《标杆人生》是瑞克·华伦的畅销灵修书，以四十天带领读者从神的角度思考一个根本问题：「我究竟为什么活着？」全书帮助人发现并活出神所定的人生目的。"}, {"title": "五个人生目的", "text": "它把人生目的归纳为五方面：为讨神喜悦而受造（敬拜）、为加入神的家而成形（团契）、被造为要像基督（门徒成长）、被塑造为要服事神（事奉）、为完成神的使命而被造（宣教）。"}, {"title": "怎么读", "text": "一天一章、四十天读完，借每章后的思考要点，把「人生目的」落实为生活中的取舍与行动。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "mere", "title": "返璞归真（导读）", "subtitle": "理性说明信仰，也滋养心灵", "author": "原著 C.S. 路易斯（C.S. Lewis, Mere Christianity）", "emoji": "💡", "color": "#818cf8", "kind": "pdf", "pdf": "/book/返璞归真-导读.pdf", "blurb": "介绍路易斯由广播讲稿整理、向怀疑者理性阐明信仰根基的通俗护教经典。", "chapters": [{"title": "关于这本书", "text": "《返璞归真》由 C.S. 路易斯二战时期的广播讲稿整理而成，向怀疑者与寻求者理性地阐明基督信仰的根基，既清晰严谨，又滋养心灵，是二十世纪最有影响的通俗护教经典。"}, {"title": "思路脉络", "text": "它从人人心里都有的「是非感（道德律）」出发，推向一位设立道德律的神；再讲到基督信仰的核心宣告——基督是谁、为何道成肉身受死复活；最后谈基督徒品格的塑造。"}, {"title": "怎么读", "text": "像与一位睿智诚恳的朋友对话，带着你的疑问读，让理性与心灵一同被说服。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "bruised", "title": "压伤的芦苇（导读）", "subtitle": "温柔安慰受伤将残的灵魂", "author": "原著 理查德·西布斯（Richard Sibbes, The Bruised Reed）", "emoji": "🌾", "color": "#a3e635", "kind": "pdf", "pdf": "/book/压伤的芦苇-导读.pdf", "blurb": "介绍清教徒西布斯以极温柔的笔触安慰软弱将残之人的安慰经典。", "chapters": [{"title": "关于这本书", "text": "《压伤的芦苇》是清教徒西布斯（人称「天上的医生」）的安慰经典，根据「压伤的芦苇，他不折断；将残的灯火，他不吹灭」（赛42:3），以极温柔的笔触安慰软弱、将残、几乎要放弃的灵魂。"}, {"title": "核心信息", "text": "对软弱的人，基督不是要压垮，而是扶持、医治、吹旺那将熄的火。纯正的真理可以包着最温柔的心肠——这是清教徒敬虔里最暖的一面。"}, {"title": "怎么读", "text": "在你自己「将残」、或身边有人快撑不住时读，领受基督的温柔；也学他以慈心待软弱的人，而非以律法压垮人。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "valley", "title": "谷中异象（导读）", "subtitle": "清教徒祷告与默想范文", "author": "原著 清教徒祷告默想选集（The Valley of Vision）", "emoji": "⛰️", "color": "#38bdf8", "kind": "pdf", "pdf": "/book/谷中异象-导读.pdf", "blurb": "介绍这部以丰富真挚的属灵语言示范祷告、认罪、感恩、仰望的祷告默想选集。", "chapters": [{"title": "关于这本书", "text": "《谷中异象》是清教徒与福音派属灵传统的祷告、默想范文选集，以丰富而真挚的属灵语言，示范如何向神倾心吐意——认罪、感恩、仰望、降服。"}, {"title": "它的特点", "text": "既深知自己的卑微与罪，又高举神的恩典与荣耀，常在「低谷」里仰望「高处」的神。它是极佳的灵修辅助，帮助人学会祷告。"}, {"title": "怎么读", "text": "每天选一篇当作自己祷告的引子，照着向神倾诉，再渐渐化为你自己的话。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "whitney", "title": "操练敬虔（导读）", "subtitle": "基于圣经的实用属灵操练", "author": "原著 唐纳德·惠特尼（Donald Whitney, Spiritual Disciplines for the Christian Life）", "emoji": "🏋️", "color": "#fb7185", "kind": "pdf", "pdf": "/book/操练敬虔-导读.pdf", "blurb": "介绍惠特尼逐一讲解读经、祷告、禁食、独处等属灵操练的实用手册。", "chapters": [{"title": "关于这本书", "text": "《操练敬虔》是唐纳德·惠特尼基于圣经的属灵操练实用指南，逐一讲解读经、祷告、敬拜、禁食、独处、记录、事奉、奉献、学习等操练，是健康属灵生活的实用手册。"}, {"title": "核心信息", "text": "属灵操练不是赚取功德的律法，而是「为敬虔而操练自己」（提前4:7）的恩典管道——借着这些操练，神使我们更亲近祂、更像基督。"}, {"title": "怎么读", "text": "一次专注操练一项，循序渐进地建立健康的属灵习惯，不求一次做全。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "foster", "title": "庆祝纪律（导读）", "subtitle": "内外平衡的属灵操练路径", "author": "原著 理查德·福斯特（Richard Foster, Celebration of Discipline）", "emoji": "🎉", "color": "#f472b6", "kind": "pdf", "pdf": "/book/庆祝纪律-导读.pdf", "blurb": "介绍福斯特把属灵操练分为内在、外在、团体三组，注重平衡的经典。", "chapters": [{"title": "关于这本书", "text": "《庆祝纪律》是理查德·福斯特的属灵操练经典，把操练分为三组：内在的（默想、祷告、禁食、研读）、外在的（简朴、独处、顺服、服事）、团体的（认罪、敬拜、引导、庆祝）。"}, {"title": "核心信息", "text": "它把属灵操练称为「通向自由的门」，注重内在与外在、个人与群体的平衡，让神的恩典借着操练在生命中真实地作工。"}, {"title": "怎么读", "text": "从一两项你最需要的操练开始，慢慢体会、循序渐进，重在让操练把你带到神面前，而非完成清单。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "missbio", "title": "宣教士传记（导读）", "subtitle": "戴德生 / 吉姆·艾略特", "author": "《戴德生的属灵秘诀》《通过死亡之门》等", "emoji": "🌏", "color": "#2dd4bf", "kind": "pdf", "pdf": "/book/宣教士传记-导读.pdf", "blurb": "介绍真实宣教士传记，戴德生「以神的信实为安息」、吉姆·艾略特彻底摆上的生命激励。", "chapters": [{"title": "关于这类书", "text": "真实宣教士的生命传记（如记述戴德生的《戴德生的属灵秘诀》，或记述吉姆·艾略特殉道的相关传记），记录他们如何凭信心、舍己、彻底摆上，回应神的呼召。"}, {"title": "戴德生的秘诀", "text": "戴德生属灵生命的核心，是「以神的信实为安息」——得胜不在于更努力，而在于更深地住在基督里、单单倚靠祂的供应（约15「常在我里面」）。"}, {"title": "吉姆·艾略特的摆上", "text": "吉姆·艾略特那句广为传诵的话点出彻底奉献的价值观：为不能保留的，舍弃他不能存留的，绝非愚拙。他的殉道激励了无数青年献身宣教。"}, {"title": "怎么读", "text": "把他们的生命当作镜子，问自己：「我愿不愿这样信靠、这样摆上？」让真实的榜样激励你回应神。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
  {"id": "piety", "title": "实践敬虔（导读）", "subtitle": "清教徒的日常敬虔生活指南", "author": "原著 刘易斯·贝利（Lewis Bayly, The Practice of Piety）", "emoji": "🏠", "color": "#fbbf24", "kind": "pdf", "pdf": "/book/实践敬虔-导读.pdf", "blurb": "介绍贝利曾极畅销、影响班扬的日常敬虔指南，含晨昏祷告、家庭崇拜等。", "chapters": [{"title": "关于这本书", "text": "《实践敬虔》是清教徒刘易斯·贝利所写的日常敬虔生活指南，曾极为畅销、再版无数，深深影响了约翰·班扬等人。它教导人如何在一天的起居与家庭中，过一种敬虔的生活。"}, {"title": "主要内容", "text": "默想神的属性、晨昏的祷告、守安息日、家庭崇拜、面对疾病与死亡的属灵预备等，把敬虔落实到日常的每个环节，尤其重视家庭中的敬拜。"}, {"title": "怎么读", "text": "取其中一项（如建立每日晨昏祷告，或开始家庭崇拜）在你家中实行，把敬虔从观念变成日常的习惯。（本页为本应用原创导读；原著全文可放入 public/book/ 目录。）"}]},
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
