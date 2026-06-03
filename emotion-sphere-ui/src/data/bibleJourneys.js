// 圣经地图集 · 行程类数据集（复用 BibleMapPage 行程 UI：站点+事件+路线+年代轴+动画播放）。
// 坐标 [lng, lat]。事件 {title, ref, summary}。confidence 缺省 identified。
// 每个数据集 descriptor：{ id, title, subtitle, icon, variantLabel, cities[], variants[] }
// variant：{ id, label, color, description, stationIds[], startYear?, endYear? }（有 startYear 则显示年代轴）

export const JOURNEY_DATASETS = [
  // ── 1. 耶稣生平 ─────────────────────────────────────────────
  {
    id: 'jesus', title: '耶稣生平', subtitle: '从伯利恒到耶路撒冷 · 出生→受洗→传道→受难→复活',
    icon: '✝️', variantLabel: '生平',
    cities: [
      { id: 'bethlehem', name_zh: '伯利恒', name_en: 'Bethlehem', lng: 35.20, lat: 31.70, events: [
        { title: '道成肉身降生', ref: '路2:4-7', summary: '约瑟与马利亚回大卫的城伯利恒报名上册，耶稣降生在马槽里。' } ] },
      { id: 'nazareth', name_zh: '拿撒勒', name_en: 'Nazareth', lng: 35.30, lat: 32.70, events: [
        { title: '在拿撒勒长大', ref: '路2:51-52', summary: '耶稣在拿撒勒顺从父母、智慧身量并神人喜爱他的心一齐增长。' },
        { title: '会堂宣读以赛亚书', ref: '路4:16-21', summary: '耶稣在家乡会堂宣告「主的灵在我身上……今天这经应验在你们耳中」。' } ] },
      { id: 'jordan', name_zh: '约旦河（受洗）', name_en: 'Jordan River', lng: 35.55, lat: 31.84, events: [
        { title: '受洗、圣灵如鸽降临', ref: '太3:13-17', summary: '约翰为耶稣施洗，天开了，圣灵仿佛鸽子降下，有声音说「这是我的爱子」。' } ] },
      { id: 'capernaum', name_zh: '迦百农', name_en: 'Capernaum', lng: 35.575, lat: 32.88, events: [
        { title: '传道的中心', ref: '太4:13-22', summary: '耶稣以迦百农为加利利事工基地，呼召彼得、安得烈等门徒，医病赶鬼传天国福音。' } ] },
      { id: 'galilee', name_zh: '加利利海', name_en: 'Sea of Galilee', lng: 35.59, lat: 32.82, events: [
        { title: '平静风浪与神迹', ref: '太8:23-27; 太14', summary: '在加利利海边行许多神迹：平静风浪、五饼二鱼喂饱五千人、海面行走。' } ] },
      { id: 'jerusalem', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.23, lat: 31.78, events: [
        { title: '受难被钉十架', ref: '路23:33-46', summary: '耶稣在耶路撒冷被审判、钉于各各他十字架，为世人的罪舍命。' },
        { title: '第三日复活', ref: '路24:1-7', summary: '七日的头一日清晨，妇女发现坟墓空了，主已照他所说的复活了。' } ] },
    ],
    variants: [ { id: 'life', label: '生平历程', color: '#fbbf24', description: '依出生→受洗→传道→受难→复活的顺序，行程可动画播放。',
      stationIds: ['bethlehem', 'nazareth', 'jordan', 'capernaum', 'galilee', 'jerusalem'], startYear: -5, endYear: 33 } ],
  },

  // ── 2. 亚伯拉罕迁徙 ─────────────────────────────────────────
  {
    id: 'abraham', title: '亚伯拉罕迁徙', subtitle: '从乌珥到应许之地 · 蒙召、立约、筑坛',
    icon: '🐫', variantLabel: '迁徙',
    cities: [
      { id: 'ur', name_zh: '吾珥', name_en: 'Ur', lng: 46.10, lat: 30.96, confidence: 'approximate', events: [
        { title: '神的呼召', ref: '徒7:2-3; 创11:31', summary: '荣耀的神向在迦勒底吾珥的亚伯兰显现，呼召他离开本地本族。' } ] },
      { id: 'haran', name_zh: '哈兰', name_en: 'Haran', lng: 39.03, lat: 36.86, events: [
        { title: '七十五岁奉命起行', ref: '创12:4', summary: '父亲他拉死在哈兰；亚伯兰七十五岁时照耶和华的吩咐起行往迦南去。' } ] },
      { id: 'shechem', name_zh: '示剑', name_en: 'Shechem', lng: 35.28, lat: 32.21, events: [
        { title: '第一座坛 · 赐地的应许', ref: '创12:6-7', summary: '到示剑摩利橡树，耶和华应许「我要把这地赐给你的后裔」，他筑了第一座坛。' } ] },
      { id: 'bethel', name_zh: '伯特利', name_en: 'Bethel', lng: 35.22, lat: 31.93, events: [
        { title: '筑坛求告耶和华的名', ref: '创12:8', summary: '在伯特利与艾的中间支搭帐棚、筑坛，求告耶和华的名。' } ] },
      { id: 'egypt', name_zh: '埃及', name_en: 'Egypt', lng: 31.20, lat: 30.05, events: [
        { title: '因饥荒下埃及', ref: '创12:10-20', summary: '迦南遭遇饥荒，亚伯兰下埃及暂居，因惧怕称撒莱为妹，后蒙神保守归回。' } ] },
      { id: 'hebron', name_zh: '希伯仑（幔利）', name_en: 'Hebron', lng: 35.10, lat: 31.53, events: [
        { title: '立约 · 后裔如星', ref: '创13:18; 15:5-6', summary: '定居幔利橡树筑坛；神领他观看众星，应许后裔如星之多，他就信神，神算为他的义。' } ] },
      { id: 'moriah', name_zh: '摩利亚山', name_en: 'Mount Moriah', lng: 35.235, lat: 31.778, events: [
        { title: '献以撒 · 耶和华以勒', ref: '创22:1-14', summary: '神试验亚伯拉罕献独生子以撒；他顺服到底，神预备公羊代替，称那地为「耶和华以勒」。' } ] },
    ],
    variants: [ { id: 'journey', label: '蒙召之旅', color: '#34d399', description: '一生的信心旅程，可动画播放；点站点看应许与筑坛。',
      stationIds: ['ur', 'haran', 'shechem', 'bethel', 'egypt', 'hebron', 'moriah'], startYear: -2091, endYear: -1991 } ],
  },

  // ── 3. 约书亚征服迦南 ───────────────────────────────────────
  {
    id: 'joshua', title: '约书亚征服迦南', subtitle: '中部 / 南方 / 北方三大战役',
    icon: '⚔️', variantLabel: '战役',
    cities: [
      { id: 'gilgal', name_zh: '吉甲（基地）', name_en: 'Gilgal', lng: 35.50, lat: 31.85 },
      { id: 'jericho', name_zh: '耶利哥', name_en: 'Jericho', lng: 35.44, lat: 31.87, events: [
        { title: '城墙倒塌', ref: '书6:20', summary: '绕城七日、第七日七次，祭司吹角、百姓呐喊，耶利哥城墙塌陷，全城被取。' } ] },
      { id: 'ai', name_zh: '艾城', name_en: 'Ai', lng: 35.26, lat: 31.92, events: [
        { title: '伏兵得胜', ref: '书8:18-26', summary: '初因亚干犯罪失败；除罪后设伏兵，约书亚伸出短枪，一举攻取艾城。' } ] },
      { id: 'gibeon', name_zh: '基遍', name_en: 'Gibeon', lng: 35.18, lat: 31.85, events: [
        { title: '基遍人的诡计', ref: '书9:3-15', summary: '基遍人假扮远方来客，骗以色列与他们立约存留性命。' },
        { title: '日头停留', ref: '书10:12-14', summary: '为援救基遍迎战五王联盟，约书亚祷告，日头与月亮停住约一日，耶和华为以色列争战。' } ] },
      { id: 'jarmuth', name_zh: '耶末', name_en: 'Jarmuth', lng: 34.97, lat: 31.70 },
      { id: 'lachish', name_zh: '拉吉', name_en: 'Lachish', lng: 34.85, lat: 31.56 },
      { id: 'eglon', name_zh: '伊矶伦', name_en: 'Eglon', lng: 34.70, lat: 31.60 },
      { id: 'hebron', name_zh: '希伯仑', name_en: 'Hebron', lng: 35.10, lat: 31.53, events: [
        { title: '南方战役攻取', ref: '书10:36-37', summary: '约书亚率军上到希伯仑攻打，夺取这城与属它的城邑。' } ] },
      { id: 'jerusalem', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.23, lat: 31.78 },
      { id: 'makkedah', name_zh: '玛基大', name_en: 'Makkedah', lng: 34.85, lat: 31.62, events: [
        { title: '五王败亡', ref: '书10:16-27', summary: '南方五王联盟（耶路撒冷、希伯仑、耶末、拉吉、伊矶伦）败逃藏于洞中，终被处死。' } ] },
      { id: 'merom', name_zh: '米伦水', name_en: 'Waters of Merom', lng: 35.45, lat: 32.93, events: [
        { title: '北方联军大败', ref: '书11:1-9', summary: '夏琐王耶宾召集北方诸王于米伦水边，约书亚突袭大获全胜。' } ] },
      { id: 'hazor', name_zh: '夏琐', name_en: 'Hazor', lng: 35.57, lat: 33.02, events: [
        { title: '火烧夏琐', ref: '书11:10-13', summary: '夏琐素为列国之首，约书亚攻取并用火焚烧这城。' } ] },
    ],
    variants: [
      { id: 'central', label: '中部战役', color: '#fbbf24', description: '渡约旦后从吉甲出击：耶利哥→艾城，并与基遍立约。',
        stationIds: ['gilgal', 'jericho', 'ai', 'gibeon'] },
      { id: 'southern', label: '南方战役', color: '#38bdf8', description: '为救基遍迎战南方五王联盟，日头停留，直取诸城。',
        stationIds: ['gibeon', 'jerusalem', 'jarmuth', 'lachish', 'eglon', 'makkedah', 'hebron'] },
      { id: 'northern', label: '北方战役', color: '#a78bfa', description: '北上米伦水边大败联军，攻取并焚烧夏琐。',
        stationIds: ['gilgal', 'merom', 'hazor'] },
    ],
  },

  // ── 4. 大卫王国 ─────────────────────────────────────────────
  {
    id: 'david', title: '大卫王国', subtitle: '从牧童到一国之君 · 统一与扩张',
    icon: '🛡️', variantLabel: '历程',
    cities: [
      { id: 'bethlehem', name_zh: '伯利恒', name_en: 'Bethlehem', lng: 35.20, lat: 31.70, events: [
        { title: '撒母耳膏立', ref: '撒上16:13', summary: '撒母耳照神指示在伯利恒膏耶西的小儿子大卫，耶和华的灵大大感动他。' } ] },
      { id: 'elah', name_zh: '以拉谷', name_en: 'Valley of Elah', lng: 34.96, lat: 31.69, events: [
        { title: '击杀歌利亚', ref: '撒上17:48-50', summary: '少年大卫奉耶和华的名，用机弦甩石击倒非利士巨人歌利亚。' } ] },
      { id: 'ziklag', name_zh: '洗革拉', name_en: 'Ziklag', lng: 34.60, lat: 31.30, events: [
        { title: '逃避扫罗 · 寄居非利士', ref: '撒上27:1-7', summary: '为躲避扫罗追杀，大卫投奔非利士迦特王，驻守洗革拉。' } ] },
      { id: 'hebron', name_zh: '希伯仑', name_en: 'Hebron', lng: 35.10, lat: 31.53, events: [
        { title: '作犹大王七年半', ref: '撒下2:4; 5:5', summary: '扫罗死后，大卫在希伯仑受膏作犹大王，统治七年六个月。' } ] },
      { id: 'jerusalem', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.23, lat: 31.78, events: [
        { title: '攻取锡安定都', ref: '撒下5:6-9', summary: '大卫攻取耶布斯人的保障锡安，称为「大卫的城」，定为全以色列的京都。' },
        { title: '迎约柜 · 扩张王国', ref: '撒下6; 8', summary: '将约柜迎入京城；四围争战得胜，败非利士、摩押、亚兰，疆域大大扩张。' } ] },
    ],
    variants: [ { id: 'rise', label: '兴起与统一', color: '#f59e0b', description: '从受膏、战胜歌利亚到定都耶路撒冷，可动画播放。',
      stationIds: ['bethlehem', 'elah', 'ziklag', 'hebron', 'jerusalem'], startYear: -1010, endYear: -970 } ],
  },

  // ── 5. 所罗门王国 ───────────────────────────────────────────
  {
    id: 'solomon', title: '所罗门王国', subtitle: '黄金时代 · 圣殿与古代贸易网络',
    icon: '🏛️', variantLabel: '主题',
    cities: [
      { id: 'jerusalem', name_zh: '耶路撒冷（圣殿）', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, events: [
        { title: '建造第一圣殿', ref: '王上6:1', summary: '所罗门在位第四年动工，历七年建成耶和华的圣殿，成为以色列敬拜中心。' } ] },
      { id: 'tyre', name_zh: '推罗', name_en: 'Tyre', lng: 35.20, lat: 33.27, events: [
        { title: '推罗王供应香柏木', ref: '王上5:1-12', summary: '推罗王希兰与所罗门立约，供应黎巴嫩香柏木与巧匠，换取粮油。' } ] },
      { id: 'ezion-geber', name_zh: '以旬迦别（红海港）', name_en: 'Ezion-geber', lng: 34.976, lat: 29.540, events: [
        { title: '红海船队往俄斐', ref: '王上9:26-28', summary: '所罗门在红海边以旬迦别建船队，往俄斐运回大量黄金。' } ] },
      { id: 'sheba', name_zh: '示巴', name_en: 'Sheba', lng: 45.30, lat: 15.40, confidence: 'approximate', events: [
        { title: '示巴女王来访', ref: '王上10:1-13', summary: '示巴女王慕所罗门的智慧与财富，带香料金银宝石远道来访、叹为观止。' } ] },
      { id: 'ophir', name_zh: '俄斐', name_en: 'Ophir', lng: 43.00, lat: 17.00, confidence: 'unknown' },
      { id: 'egypt', name_zh: '埃及', name_en: 'Egypt', lng: 31.20, lat: 30.05, events: [
        { title: '联姻与马匹贸易', ref: '王上3:1; 10:28-29', summary: '所罗门娶法老女儿为妻；从埃及进口马匹战车，转售赫人与亚兰诸王，居中获利。' } ] },
    ],
    variants: [
      { id: 'temple', label: '圣殿与京畿', color: '#ffd700', description: '与推罗结盟，建造圣殿与宫室。', stationIds: ['jerusalem', 'tyre'] },
      { id: 'redsea', label: '红海·示巴贸易', color: '#38bdf8', description: '红海船队远航俄斐运金；示巴女王来访。', stationIds: ['jerusalem', 'ezion-geber', 'ophir', 'sheba'] },
      { id: 'egypt', label: '埃及联姻贸易', color: '#fb7185', description: '与埃及联姻，垄断马匹战车转口贸易。', stationIds: ['jerusalem', 'egypt'] },
    ],
  },

  // ── 6. 启示录七教会 ─────────────────────────────────────────
  {
    id: 'seven-churches', title: '启示录七教会', subtitle: '亚西亚七间教会 · 优点 / 责备 / 应许',
    icon: '🕯️', variantLabel: '巡回',
    cities: [
      { id: 'ephesus', name_zh: '以弗所', name_en: 'Ephesus', lng: 27.34, lat: 37.94, events: [
        { title: '失去起初的爱心', ref: '启2:1-7', summary: '优点：为主名劳苦、恨恶尼哥拉党的行为。责备：离弃了起初的爱心。应许：得胜的得吃神乐园中生命树的果子。' } ] },
      { id: 'smyrna', name_zh: '士每拿', name_en: 'Smyrna', lng: 27.14, lat: 38.42, events: [
        { title: '至死忠心', ref: '启2:8-11', summary: '优点：在患难贫穷中却是富足，主未加责备。应许：务要至死忠心，必得生命的冠冕，不受第二次死的害。' } ] },
      { id: 'pergamum', name_zh: '别迦摩', name_en: 'Pergamum', lng: 27.18, lat: 39.13, events: [
        { title: '在撒但座位之处持守', ref: '启2:12-17', summary: '优点：在撒但座位之处仍持守主名。责备：容让巴兰与尼哥拉党的教训。应许：赐隐藏的吗哪与写新名的白石。' } ] },
      { id: 'thyatira', name_zh: '推雅推喇', name_en: 'Thyatira', lng: 27.84, lat: 38.92, events: [
        { title: '爱心增长却容让假师', ref: '启2:18-29', summary: '优点：爱心、信心、服事、忍耐越来越多。责备：容让自称女先知的耶洗别引诱人。应许：赐权柄制伏列国、并赐晨星。' } ] },
      { id: 'sardis', name_zh: '撒狄', name_en: 'Sardis', lng: 28.04, lat: 38.49, events: [
        { title: '按名是活的其实是死的', ref: '启3:1-6', summary: '责备：徒有活的名声，行为却未完全。优点：仍有几名未污秽衣服。应许：得胜的必穿白衣，名字不从生命册涂抹。' } ] },
      { id: 'philadelphia', name_zh: '非拉铁非', name_en: 'Philadelphia', lng: 28.52, lat: 38.36, events: [
        { title: '敞开的门', ref: '启3:7-13', summary: '优点：略有能力却遵守主道、未弃绝主名，主未加责备。应许：在主前有敞开的门，免去普天下的试炼，成为神殿中的柱子。' } ] },
      { id: 'laodicea', name_zh: '老底嘉', name_en: 'Laodicea', lng: 29.11, lat: 37.84, events: [
        { title: '不冷不热', ref: '启3:14-22', summary: '责备：不冷不热，自以为富足却不知贫穷、瞎眼、赤身。应许：当悔改开门，主必进来同席，得与主同坐宝座。' } ] },
    ],
    variants: [ { id: 'circuit', label: '七教会巡回', color: '#f97316', description: '依书信顺序的邮路巡回；点城市看优点、责备与应许。',
      stationIds: ['ephesus', 'smyrna', 'pergamum', 'thyatira', 'sardis', 'philadelphia', 'laodicea'] } ],
  },

  // ── 7. 受难周步行轨迹 ───────────────────────────────────────
  {
    id: 'passion-week', title: '受难周', subtitle: '耶稣在耶路撒冷最后一周的步行轨迹',
    icon: '🌿', variantLabel: '受难周',
    cities: [
      { id: 'bethany', name_zh: '伯大尼', name_en: 'Bethany', lng: 35.26, lat: 31.77, events: [
        { title: '受膏（受难周前夕）', ref: '约12:1-8', summary: '逾越节前六日，耶稣在伯大尼，马利亚用真哪哒香膏抹主，为安葬之日存留。' } ] },
      { id: 'olives', name_zh: '橄榄山', name_en: 'Mount of Olives', lng: 35.245, lat: 31.778, events: [
        { title: '荣入圣城（棕枝主日）', ref: '太21:1-11', summary: '耶稣骑驴驹从橄榄山下来进耶路撒冷，众人铺衣摇棕枝高呼「和散那」。' } ] },
      { id: 'temple', name_zh: '圣殿', name_en: 'Temple', lng: 35.2354, lat: 31.778, events: [
        { title: '洁净圣殿与教训', ref: '太21:12-13', summary: '耶稣赶出殿里做买卖的人，连日在殿中教训人、与宗教领袖辩论。' } ] },
      { id: 'upper-room', name_zh: '马可楼（最后晚餐）', name_en: 'Upper Room', lng: 35.229, lat: 31.771, events: [
        { title: '设立圣餐 · 洗脚', ref: '路22:7-20; 约13', summary: '在楼房与门徒守逾越节，为门徒洗脚，擘饼分杯设立主的圣餐。' } ] },
      { id: 'gethsemane', name_zh: '客西马尼', name_en: 'Gethsemane', lng: 35.240, lat: 31.779, events: [
        { title: '祷告与被捕', ref: '太26:36-56', summary: '耶稣在客西马尼园极其忧伤地祷告「不要照我的意思」，随后被犹大出卖、被捕。' } ] },
      { id: 'caiaphas', name_zh: '大祭司院（该亚法）', name_en: "Caiaphas's House", lng: 35.228, lat: 31.771, events: [
        { title: '宗教审判 · 彼得不认主', ref: '太26:57-75', summary: '在大祭司该亚法面前受审被定亵渎之罪；彼得在院中三次不认主，鸡叫想起主的话。' } ] },
      { id: 'pilate', name_zh: '彼拉多衙门', name_en: "Pilate's Praetorium", lng: 35.226, lat: 31.779, events: [
        { title: '罗马审判 · 定罪', ref: '约18:28-19:16', summary: '众人把耶稣解到巡抚彼拉多处；彼拉多查不出罪来却顺从众意，把他交去钉十字架。' } ] },
      { id: 'golgotha', name_zh: '各各他', name_en: 'Golgotha', lng: 35.229, lat: 31.778, events: [
        { title: '钉十字架 · 断气', ref: '路23:33-46', summary: '在各各他被钉十字架，午正遍地黑暗，耶稣喊「成了」，将灵魂交于父手中。' } ] },
      { id: 'tomb', name_zh: '园中坟墓', name_en: 'Garden Tomb', lng: 35.230, lat: 31.789, events: [
        { title: '安葬与复活', ref: '太27:59-28:6', summary: '约瑟将主葬在新坟墓里；七日的头一日，天使宣告「他不在这里，已照所说的复活了」。' } ] },
    ],
    variants: [ { id: 'week', label: '受难周路线', color: '#fb7185', description: '从伯大尼到园中坟墓，循受难周时序步行轨迹，可动画播放。',
      stationIds: ['bethany', 'olives', 'temple', 'upper-room', 'gethsemane', 'caiaphas', 'pilate', 'golgotha', 'tomb'] } ],
  },
]
