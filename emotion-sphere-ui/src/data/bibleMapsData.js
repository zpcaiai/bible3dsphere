// bibleMapsData.js — 全部圣经地图的统一数据
// 坐标为 [lng, lat]。年代多采用传统圣经年代学（早期出埃及说），仅供教学示意。
// 每个 config: { id, title, subtitle, era, badge, bounds, mode, layerSelect, layers[], years?, eras? }
// point: { id, name_zh, name_en, lng, lat, order, confidence, year?, age?, scriptureRef, altar?, promise?, note?, events[] }
import { exodusStations, exodusRoute } from './exodusStations'

// —— 1. 亚伯拉罕迁徙 ——
const abraham = {
  id: 'abraham',
  title: '亚伯拉罕迁徙地图',
  subtitle: '从吾珥到应许之地 · 信心之父的旅程',
  era: '约公元前 2100–1990',
  badge: '★★★★★',
  bounds: { minLng: 30, maxLng: 47, minLat: 28, maxLat: 38 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [{
    id: 'route', label: '迁徙路线', color: '#e8b04b', route: true,
    points: [
      { id: 'ur', name_zh: '吾珥', name_en: 'Ur', lng: 46.10, lat: 30.96, order: 1, confidence: 'identified', year: -2166, age: 0, scriptureRef: '创11:28-31；徒7:2-4', note: '亚伯兰的本家之地。司提反说："荣耀的神向我们的祖宗亚伯拉罕显现，那时他在美索不达米亚。"', events: [
        { title: '蒙召的起点', ref: '徒7:2-3', summary: '神在吾珥向亚伯兰显现，呼召他离开本地、本族、父家，往神所要指示的地方去。' },
      ] },
      { id: 'haran', name_zh: '哈兰', name_en: 'Haran', lng: 39.03, lat: 36.86, order: 2, confidence: 'identified', year: -2091, age: 75, scriptureRef: '创11:31-12:4', note: '父亲他拉率家族至此居住，死于哈兰。', events: [
        { title: '七十五岁再蒙召', ref: '创12:1-4', summary: '"你要离开本地、本族、父家，往我所要指示你的地去。"亚伯兰七十五岁照耶和华的吩咐起行，带着罗得同去。' },
      ] },
      { id: 'shechem', name_zh: '示剑', name_en: 'Shechem', lng: 35.28, lat: 32.21, order: 3, confidence: 'identified', year: -2091, age: 75, scriptureRef: '创12:6-7', altar: '摩利橡树旁，为向他显现的耶和华筑坛', promise: '"我要把这地赐给你的后裔。"', events: [
        { title: '进入迦南的第一座坛', ref: '创12:6-7', summary: '亚伯兰到了示剑的摩利橡树，耶和华向他显现，应许把这地赐给他的后裔；他就在那里筑了一座坛。' },
      ] },
      { id: 'bethel', name_zh: '伯特利', name_en: 'Bethel', lng: 35.22, lat: 31.93, order: 4, confidence: 'identified', year: -2090, age: 75, scriptureRef: '创12:8；13:3-4', altar: '在伯特利与艾城之间筑坛，求告耶和华的名', events: [
        { title: '求告耶和华的名', ref: '创12:8', summary: '亚伯兰在此支搭帐棚，筑坛求告耶和华的名。日后从埃及上来仍回到这坛前敬拜。' },
        { title: '与罗得分开', ref: '创13:8-12', summary: '为牧人相争，亚伯兰让罗得先选；罗得选了约旦河平原往所多玛去，亚伯兰留在迦南地。' },
      ] },
      { id: 'egypt', name_zh: '埃及', name_en: 'Egypt', lng: 31.20, lat: 30.10, order: 5, confidence: 'approximate', year: -2089, age: 76, scriptureRef: '创12:10-20', note: '地有饥荒，下到埃及暂居。', events: [
        { title: '因饥荒下埃及', ref: '创12:10-20', summary: '亚伯兰称撒莱为妹子，法老因此受灾；神保守撒莱，法老把他们送走，亚伯兰带着许多牲畜财物回迦南。' },
      ] },
      { id: 'hebron', name_zh: '希伯仑（幔利）', name_en: 'Hebron', lng: 35.10, lat: 31.53, order: 6, confidence: 'identified', year: -2085, age: 80, scriptureRef: '创13:18；23章', altar: '在幔利的橡树那里为耶和华筑坛', promise: '"地上万国都要因你的后裔得福。"', events: [
        { title: '立约与应许重申', ref: '创15;17', summary: '神与亚伯兰立约，应许后裔如天上的星；改名亚伯拉罕，立割礼为约的记号。' },
        { title: '麦比拉洞', ref: '创23', summary: '撒拉死后，亚伯拉罕在希伯仑买下麦比拉洞作坟地——他在应许之地拥有的第一块产业。' },
      ] },
      { id: 'beersheba', name_zh: '别是巴', name_en: 'Beersheba', lng: 34.79, lat: 31.25, order: 7, confidence: 'identified', year: -2080, age: 86, scriptureRef: '创21:31-33', altar: '栽种垂丝柳树，求告永生神耶和华的名', events: [
        { title: '与亚比米勒立约', ref: '创21:22-34', summary: '为水井之争，亚伯拉罕与基拉耳王亚比米勒起誓立约，故名"别是巴"（盟誓之井）。' },
        { title: '以撒出生', ref: '创21:1-7', summary: '神照应许使撒拉生以撒，亚伯拉罕一百岁得应许之子。' },
      ] },
      { id: 'moriah', name_zh: '摩利亚山（耶路撒冷）', name_en: 'Mount Moriah', lng: 35.235, lat: 31.778, order: 8, confidence: 'approximate', year: -2050, age: 115, scriptureRef: '创22:1-18', altar: '在山上筑坛，预备献以撒；耶和华以勒', promise: '"地上万国都必因你的后裔得福，因为你听从了我。"', events: [
        { title: '献以撒', ref: '创22:1-14', summary: '神试验亚伯拉罕，吩咐献独生子以撒为燔祭；亚伯拉罕顺服举刀时，天使拦阻，神预备公羊代替。他称那地为"耶和华以勒"。' },
      ] },
    ],
  }],
}

// —— 2. 出埃及（复用民数记33章 42站数据）——
const exodus = {
  id: 'exodus',
  title: '出埃及与旷野漂流',
  subtitle: '从兰塞到摩押平原 · 民数记33章 42个安营站',
  era: '约公元前 1446–1406（旷野四十年）',
  badge: '★★★★★',
  bounds: { minLng: 31, maxLng: 36.5, minLat: 27.5, maxLat: 32.5 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [{
    id: 'route', label: '以色列人路线', color: '#5ec2e8', route: true,
    points: exodusStations.features.map(f => ({
      id: f.properties.id,
      name_zh: f.properties.name_zh,
      name_en: f.properties.name_en,
      lng: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1],
      order: f.properties.order,
      confidence: f.properties.confidence,
      scriptureRef: f.properties.scriptureRef,
      events: f.properties.events || [],
    })),
  }],
}

// —— 3. 约书亚征服迦南 ——
const joshua = {
  id: 'joshua',
  title: '约书亚征服迦南地图',
  subtitle: '渡约旦河 · 中部 / 南方 / 北方三大战役',
  era: '约公元前 1406–1400',
  badge: '★★★★★',
  bounds: { minLng: 34.2, maxLng: 35.9, minLat: 31.2, maxLat: 33.2 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [
    { id: 'central', label: '渡河与中部战役', color: '#e8b04b', route: true, points: [
      { id: 'gilgal', name_zh: '吉甲', name_en: 'Gilgal', lng: 35.50, lat: 31.85, order: 1, confidence: 'approximate', scriptureRef: '书4-5', altar: '立十二块石头为记念；行割礼、守逾越节', events: [
        { title: '约旦河分开', ref: '书3:14-17', summary: '祭司抬约柜脚踏入水，约旦河水在亚当城停住立起成垒，全民走干地过河进入应许之地。' },
      ] },
      { id: 'jericho', name_zh: '耶利哥', name_en: 'Jericho', lng: 35.44, lat: 31.87, order: 2, confidence: 'identified', scriptureRef: '书6', events: [
        { title: '城墙倒塌', ref: '书6:20', summary: '绕城七日，第七日绕七次、吹角呐喊，城墙塌陷；惟妓女喇合一家因信得救。' },
      ] },
      { id: 'ai', name_zh: '艾城', name_en: 'Ai', lng: 35.27, lat: 31.92, order: 3, confidence: 'approximate', scriptureRef: '书7-8', events: [
        { title: '亚干的罪与得胜', ref: '书7-8', summary: '亚干私取当灭之物致初战败北；除罪后用伏兵之计攻取艾城。' },
      ] },
      { id: 'ebal', name_zh: '以巴路山', name_en: 'Mt Ebal', lng: 35.27, lat: 32.23, order: 4, confidence: 'identified', scriptureRef: '书8:30-35', altar: '在以巴路山为耶和华筑坛，宣读律法的祝福与咒诅', events: [] },
    ] },
    { id: 'south', label: '南方战役（五王联盟）', color: '#ff6b6b', route: true, points: [
      { id: 'gibeon', name_zh: '基遍', name_en: 'Gibeon', lng: 35.18, lat: 31.85, order: 5, confidence: 'identified', scriptureRef: '书9-10', events: [
        { title: '基遍人的诡计与日月停住', ref: '书10:12-14', summary: '基遍人骗得和约；五王联军围攻基遍，约书亚驰援，神降大冰雹，日头停在基遍约一日之久。' },
      ] },
      { id: 'makkedah', name_zh: '玛基大', name_en: 'Makkedah', lng: 34.95, lat: 31.62, order: 6, confidence: 'approximate', scriptureRef: '书10:16-27', events: [
        { title: '五王藏洞被擒', ref: '书10:16-27', summary: '亚摩利五王逃入玛基大洞，被约书亚擒杀。' },
      ] },
      { id: 'lachish', name_zh: '拉吉', name_en: 'Lachish', lng: 34.85, lat: 31.56, order: 7, confidence: 'identified', scriptureRef: '书10:31-32', events: [] },
      { id: 'hebron-s', name_zh: '希伯仑', name_en: 'Hebron', lng: 35.10, lat: 31.53, order: 8, confidence: 'identified', scriptureRef: '书10:36-37', events: [] },
    ] },
    { id: 'north', label: '北方战役（夏琐）', color: '#4ade80', route: true, points: [
      { id: 'merom', name_zh: '米伦水边', name_en: 'Waters of Merom', lng: 35.45, lat: 32.93, order: 9, confidence: 'approximate', scriptureRef: '书11:5-9', events: [
        { title: '北方联军覆没', ref: '书11:7-8', summary: '夏琐王耶宾联合北方诸王，多如海边的沙；约书亚在米伦水边突袭得胜，砍断马蹄筋、焚烧战车。' },
      ] },
      { id: 'hazor', name_zh: '夏琐', name_en: 'Hazor', lng: 35.57, lat: 33.02, order: 10, confidence: 'identified', scriptureRef: '书11:10-13', events: [
        { title: '焚烧夏琐', ref: '书11:10-11', summary: '夏琐素来是这诸国的首；约书亚攻取并用火焚烧，使北方诸城归服。' },
      ] },
    ] },
  ],
}

// —— 4. 十二支派分地 ——
const tribes = {
  id: 'tribes',
  title: '十二支派分地地图',
  subtitle: '约书亚记13–19章 · 迦南地的产业分配',
  era: '约公元前 1400',
  badge: '★★★★★',
  bounds: { minLng: 34.2, maxLng: 36.5, minLat: 30.0, maxLat: 33.6 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [
    { id: 'west', label: '约旦河西', color: '#e8b04b', route: false, points: [
      { id: 'asher', name_zh: '亚设', name_en: 'Asher', lng: 35.18, lat: 33.05, confidence: 'approximate', scriptureRef: '书19:24-31', note: '西北沿海，近推罗、西顿。' , events: [] },
      { id: 'naphtali', name_zh: '拿弗他利', name_en: 'Naphtali', lng: 35.50, lat: 32.95, confidence: 'approximate', scriptureRef: '书19:32-39', note: '加利利海以北山地。', events: [] },
      { id: 'zebulun', name_zh: '西布伦', name_en: 'Zebulun', lng: 35.20, lat: 32.70, confidence: 'approximate', scriptureRef: '书19:10-16', note: '加利利下游，拿撒勒一带。', events: [] },
      { id: 'issachar', name_zh: '以萨迦', name_en: 'Issachar', lng: 35.45, lat: 32.55, confidence: 'approximate', scriptureRef: '书19:17-23', note: '耶斯列平原。', events: [] },
      { id: 'manasseh-w', name_zh: '玛拿西（西半）', name_en: 'Manasseh (W)', lng: 35.25, lat: 32.35, confidence: 'approximate', scriptureRef: '书17:1-13', note: '撒玛利亚山地。', events: [] },
      { id: 'ephraim', name_zh: '以法莲', name_en: 'Ephraim', lng: 35.25, lat: 32.10, confidence: 'approximate', scriptureRef: '书16:1-10', note: '中部山地，示罗会幕所在。', events: [
        { title: '示罗设立会幕', ref: '书18:1', summary: '以色列全会众在示罗（以法莲境内）设立会幕，此后成为敬拜中心，直到撒母耳时代。' },
      ] },
      { id: 'dan', name_zh: '但', name_en: 'Dan', lng: 34.90, lat: 31.95, confidence: 'approximate', scriptureRef: '书19:40-48', note: '原分沿海，后部分北迁至拉亿（但城）。', events: [] },
      { id: 'benjamin', name_zh: '便雅悯', name_en: 'Benjamin', lng: 35.22, lat: 31.85, confidence: 'approximate', scriptureRef: '书18:11-28', note: '耶路撒冷、伯特利、基遍一带。', events: [] },
      { id: 'judah', name_zh: '犹大', name_en: 'Judah', lng: 35.05, lat: 31.45, confidence: 'approximate', scriptureRef: '书15章', note: '最大的产业，南方山地与旷野；日后南国的核心。', events: [] },
      { id: 'simeon', name_zh: '西缅', name_en: 'Simeon', lng: 34.80, lat: 31.25, confidence: 'approximate', scriptureRef: '书19:1-9', note: '在犹大境内，别是巴一带。', events: [] },
    ] },
    { id: 'east', label: '约旦河东', color: '#5ec2e8', route: false, points: [
      { id: 'reuben', name_zh: '流便', name_en: 'Reuben', lng: 35.75, lat: 31.55, confidence: 'approximate', scriptureRef: '书13:15-23', note: '死海以东摩押高原。', events: [] },
      { id: 'gad', name_zh: '迦得', name_en: 'Gad', lng: 35.80, lat: 32.10, confidence: 'approximate', scriptureRef: '书13:24-28', note: '基列中部。', events: [] },
      { id: 'manasseh-e', name_zh: '玛拿西（东半）', name_en: 'Manasseh (E)', lng: 35.95, lat: 32.70, confidence: 'approximate', scriptureRef: '书13:29-31', note: '巴珊与基列北部。', events: [] },
    ] },
    { id: 'levi', label: '利未（无地业）', color: '#c084fc', route: false, points: [
      { id: 'shiloh', name_zh: '示罗（会幕）', name_en: 'Shiloh', lng: 35.29, lat: 32.05, confidence: 'identified', scriptureRef: '书18:1；21章', altar: '会幕设立之地', note: '利未人不得地业，耶和华是他们的产业；他们分得48座利未人的城（含6座逃城）散居各支派中。', events: [] },
    ] },
  ],
}

// —— 5. 大卫王统一王国 ——
const david = {
  id: 'david',
  title: '大卫王统一王国地图',
  subtitle: '从伯利恒牧童到耶路撒冷君王 · 疆域的扩张',
  era: '约公元前 1010–970',
  badge: '★★★★★',
  bounds: { minLng: 33.5, maxLng: 37.0, minLat: 29.5, maxLat: 34.2 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [
    { id: 'rise', label: '兴起之路', color: '#e8b04b', route: true, points: [
      { id: 'bethlehem-d', name_zh: '伯利恒', name_en: 'Bethlehem', lng: 35.20, lat: 31.70, order: 1, confidence: 'identified', year: -1040, scriptureRef: '撒上16', events: [
        { title: '撒母耳膏立少年大卫', ref: '撒上16:13', summary: '耶和华拣选耶西最小的儿子；撒母耳用角里的膏油膏他，耶和华的灵从那日起感动大卫。' },
      ] },
      { id: 'elah', name_zh: '以拉谷', name_en: 'Valley of Elah', lng: 34.96, lat: 31.69, order: 2, confidence: 'approximate', scriptureRef: '撒上17', events: [
        { title: '击杀歌利亚', ref: '撒上17:49-50', summary: '少年大卫凭信心奉万军之耶和华的名，用机弦甩石击倒非利士巨人歌利亚。' },
      ] },
      { id: 'adullam', name_zh: '亚杜兰洞', name_en: 'Adullam', lng: 34.99, lat: 31.65, order: 3, confidence: 'approximate', scriptureRef: '撒上22:1-2', events: [
        { title: '逃避扫罗、聚集勇士', ref: '撒上22:1-2', summary: '凡受窘迫、欠债、心里苦恼的都聚到大卫那里，约四百人，他作他们的首领。' },
      ] },
      { id: 'engedi', name_zh: '隐基底', name_en: 'En-gedi', lng: 35.39, lat: 31.46, order: 4, confidence: 'identified', scriptureRef: '撒上24', events: [
        { title: '不杀扫罗', ref: '撒上24:4-7', summary: '扫罗入洞，大卫只割其外袍衣襟，不肯害耶和华的受膏者。' },
      ] },
      { id: 'ziklag', name_zh: '洗革拉', name_en: 'Ziklag', lng: 34.62, lat: 31.40, order: 5, confidence: 'approximate', scriptureRef: '撒上27;30', events: [
        { title: '寄居非利士与追回掳物', ref: '撒上30', summary: '大卫暂居非利士地洗革拉；亚玛力人焚城掳人，大卫求问神后追击，尽数夺回。' },
      ] },
    ] },
    { id: 'reign', label: '建都与扩张', color: '#ff6b6b', route: true, points: [
      { id: 'hebron-d', name_zh: '希伯仑', name_en: 'Hebron', lng: 35.10, lat: 31.53, order: 6, confidence: 'identified', year: -1010, scriptureRef: '撒下2;5', events: [
        { title: '作犹大王七年半', ref: '撒下5:5', summary: '大卫先在希伯仑作犹大王，后众支派来归，膏他作全以色列的王。' },
      ] },
      { id: 'jerusalem-d', name_zh: '耶路撒冷（锡安）', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, order: 7, confidence: 'identified', year: -1003, scriptureRef: '撒下5:6-9;6', altar: '迎约柜进城，在亚劳拿禾场筑坛', events: [
        { title: '攻取耶布斯、定为京城', ref: '撒下5:6-9', summary: '大卫攻取耶布斯人的锡安保障，称为"大卫的城"，统一王国的政治与敬拜中心。' },
        { title: '迎约柜、神立永约', ref: '撒下6;7', summary: '大卫将约柜接进城；神借拿单应许大卫的国位必坚定到永远（弥赛亚之约）。' },
      ] },
      { id: 'philistia', name_zh: '非利士（迦特）', name_en: 'Philistia', lng: 34.85, lat: 31.70, order: 8, confidence: 'approximate', scriptureRef: '撒下5:17-25', events: [
        { title: '制伏世仇非利士', ref: '撒下5:25', summary: '大卫两次在利乏音谷击败非利士人，解除西方威胁。' },
      ] },
      { id: 'rabbah', name_zh: '拉巴（亚扪）', name_en: 'Rabbah', lng: 35.93, lat: 31.95, order: 9, confidence: 'identified', scriptureRef: '撒下12:26-31', events: [
        { title: '征服亚扪', ref: '撒下12', summary: '约押围攻、大卫攻取亚扪京城拉巴（今安曼）。围城期间发生大卫与拔示巴之罪。' },
      ] },
      { id: 'damascus-d', name_zh: '大马士革（亚兰）', name_en: 'Damascus', lng: 36.30, lat: 33.51, order: 10, confidence: 'identified', scriptureRef: '撒下8:5-6', events: [
        { title: '疆界达伯拉大河', ref: '撒下8', summary: '大卫击败亚兰、摩押、以东、琐巴，使版图北达大马士革，奠定所罗门帝国的疆域。' },
      ] },
    ] },
  ],
}

// —— 6. 所罗门王国（黄金时代与贸易网络）——
const solomon = {
  id: 'solomon',
  title: '所罗门王国地图',
  subtitle: '圣殿 · 红海港口 · 古代贸易网络',
  era: '约公元前 970–930',
  badge: '★★★★★',
  bounds: { minLng: 28, maxLng: 48, minLat: 13, maxLat: 35 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [
    { id: 'core', label: '王国核心', color: '#e8b04b', route: false, points: [
      { id: 'temple', name_zh: '耶路撒冷圣殿', name_en: 'The Temple', lng: 35.235, lat: 31.778, confidence: 'identified', year: -966, scriptureRef: '王上6-8', altar: '建造耶和华的殿，献殿祷告，荣耀充满', events: [
        { title: '建造圣殿', ref: '王上6:1', summary: '出埃及后第480年、所罗门在位第四年开工，历时七年建成；推罗王希兰供应香柏木与匠人。' },
        { title: '献殿与神的荣耀', ref: '王上8:10-11', summary: '约柜安放至圣所，云彩充满殿宇，耶和华的荣光充满圣殿；所罗门献上著名的献殿祷告。' },
      ] },
    ] },
    { id: 'trade', label: '贸易与外交', color: '#5ec2e8', route: true, points: [
      { id: 'tyre', name_zh: '推罗', name_en: 'Tyre', lng: 35.20, lat: 33.27, order: 1, confidence: 'identified', scriptureRef: '王上5;9:11', note: '腓尼基海上强国。', events: [
        { title: '希兰王的香柏木', ref: '王上5:6-10', summary: '推罗王希兰供应黎巴嫩的香柏木、松木与工匠，换取以色列的麦子与油，结盟修好。' },
      ] },
      { id: 'eziongeber', name_zh: '以旬迦别', name_en: 'Ezion-geber', lng: 34.98, lat: 29.54, order: 2, confidence: 'identified', scriptureRef: '王上9:26-28', note: '红海北端（亚喀巴湾）港口。', events: [
        { title: '红海船队往俄斐', ref: '王上9:26-28', summary: '所罗门在以东红海边建造船队，由推罗熟悉航海的人协助，从俄斐运回大量黄金。' },
      ] },
      { id: 'egypt-s', name_zh: '埃及', name_en: 'Egypt', lng: 31.20, lat: 30.05, order: 3, confidence: 'approximate', scriptureRef: '王上3:1;10:28-29', note: '联姻与战马、战车贸易。', events: [
        { title: '法老之女与马匹贸易', ref: '王上10:28-29', summary: '所罗门娶法老女儿为妻；从埃及进口战马战车，转售赫人和亚兰诸王，居中获利。' },
      ] },
      { id: 'tadmor', name_zh: '达莫（帕尔米拉）', name_en: 'Tadmor', lng: 38.27, lat: 34.56, order: 4, confidence: 'identified', scriptureRef: '王上9:18；代下8:4', note: '旷野中的商队要塞。', events: [
        { title: '建造旷野贸易城', ref: '代下8:4', summary: '所罗门在旷野建造达莫和积货城，控制通往美索不达米亚的商道。' },
      ] },
      { id: 'sheba', name_zh: '示巴', name_en: 'Sheba', lng: 45.00, lat: 15.40, order: 5, confidence: 'approximate', scriptureRef: '王上10:1-13', note: '阿拉伯半岛南端（今也门一带）的香料王国。', events: [
        { title: '示巴女王来访', ref: '王上10:1-10', summary: '示巴女王听见所罗门的智慧名声，带香料、宝石、大量黄金前来用难题试他；见其智慧与圣殿，诧异得神不守舍。' },
      ] },
    ] },
  ],
}

// —— 7. 北国南国历史（时间轴）——
const dividedKingdom = {
  id: 'divided',
  title: '北国南国历史地图',
  subtitle: '王国分裂 → 北国被掳 → 南国被掳 · 拖动时间轴看局势',
  era: '公元前 931–586',
  badge: '★★★★★',
  bounds: { minLng: 33.5, maxLng: 45.5, minLat: 30.0, maxLat: 37.5 },
  mode: 'timeline',
  layerSelect: 'multi',
  years: { min: -931, max: -586, default: -931, step: 1 },
  eras: [
    { label: '王国分裂', from: -931, to: -875 },
    { label: '先知时代', from: -874, to: -750 },
    { label: '北国灭亡', from: -749, to: -700 },
    { label: '南国灭亡', from: -699, to: -586 },
  ],
  layers: [
    { id: 'israel', label: '北国以色列', color: '#5ec2e8', route: false, points: [
      { id: 'shechem-n', name_zh: '示剑', name_en: 'Shechem', lng: 35.28, lat: 32.21, year: -931, confidence: 'identified', scriptureRef: '王上12', events: [
        { title: '王国分裂', ref: '王上12:16-20', summary: '罗波安拒绝减轻劳役，北方十支派拥立耶罗波安，国分为二；耶罗波安以示剑为初都。' },
      ] },
      { id: 'samaria', name_zh: '撒玛利亚', name_en: 'Samaria', lng: 35.19, lat: 32.28, year: -880, confidence: 'identified', scriptureRef: '王上16:24', events: [
        { title: '暗利建都撒玛利亚', ref: '王上16:24', summary: '暗利买下撒玛利亚山建为北国京城，亚哈继位后引入巴力崇拜。' },
      ] },
      { id: 'carmel', name_zh: '迦密山', name_en: 'Mt Carmel', lng: 35.03, lat: 32.73, year: -860, confidence: 'identified', scriptureRef: '王上18', events: [
        { title: '以利亚斗巴力先知', ref: '王上18:36-39', summary: '先知以利亚在迦密山求火降下，证明耶和华是神，众民俯伏说"耶和华是神"。' },
      ] },
      { id: 'samaria-fall', name_zh: '撒玛利亚陷落', name_en: 'Fall of Samaria', lng: 35.19, lat: 32.28, year: -722, confidence: 'identified', scriptureRef: '王下17', events: [
        { title: '北国被亚述所灭', ref: '王下17:6', summary: '亚述王撒缦以色围困三年攻陷撒玛利亚，将以色列人掳到亚述，十支派分散；先知何西阿、阿摩司曾警告。' },
      ] },
    ] },
    { id: 'judah', label: '南国犹大', color: '#e8b04b', route: false, points: [
      { id: 'jerusalem-j', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, year: -931, confidence: 'identified', scriptureRef: '王上12', events: [
        { title: '南国京城', ref: '王上12:21', summary: '大卫家罗波安保有犹大、便雅悯，以耶路撒冷为都；圣殿仍在，王位由大卫后裔承袭。' },
      ] },
      { id: 'isaiah', name_zh: '希西家的耶路撒冷', name_en: 'Hezekiah', lng: 35.235, lat: 31.778, year: -701, confidence: 'identified', scriptureRef: '王下18-19', events: [
        { title: '亚述围城与神的拯救', ref: '王下19:35', summary: '亚述王西拿基立围困耶路撒冷，先知以赛亚宣告神必护卫此城；耶和华的使者一夜击杀亚述军十八万五千，城得保全。' },
      ] },
      { id: 'jerusalem-fall', name_zh: '耶路撒冷陷落', name_en: 'Fall of Jerusalem', lng: 35.235, lat: 31.778, year: -586, confidence: 'identified', scriptureRef: '王下25', events: [
        { title: '南国被巴比伦所灭', ref: '王下25:8-11', summary: '巴比伦王尼布甲尼撒攻破耶路撒冷，焚毁圣殿与城，掳走犹大人；先知耶利米目睹并哀哭。' },
      ] },
    ] },
    { id: 'empires', label: '列强', color: '#ff6b6b', route: false, points: [
      { id: 'nineveh', name_zh: '尼尼微（亚述）', name_en: 'Nineveh', lng: 43.15, lat: 36.36, year: -722, confidence: 'identified', scriptureRef: '拿1;王下17', events: [
        { title: '亚述帝国', ref: '王下17', summary: '亚述以尼尼微为都，灭北国；先知约拿曾奉差往尼尼微宣讲悔改。' },
      ] },
      { id: 'babylon', name_zh: '巴比伦', name_en: 'Babylon', lng: 44.42, lat: 32.54, year: -586, confidence: 'identified', scriptureRef: '王下25;诗137', events: [
        { title: '巴比伦帝国与被掳', ref: '诗137:1', summary: '"我们曾在巴比伦的河边坐下，一追想锡安就哭了。"犹大人被掳至此七十年，但以理、以西结在此事奉。' },
      ] },
    ] },
  ],
}

// —— 8. 耶稣生平 ——
const jesus = {
  id: 'jesus',
  title: '耶稣生平地图',
  subtitle: '出生 → 受洗 → 传道 → 受难 → 复活',
  era: '约公元前 5 – 公元 30/33',
  badge: '★★★★★',
  bounds: { minLng: 34.4, maxLng: 36.2, minLat: 31.3, maxLat: 33.2 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [{
    id: 'life', label: '生平足迹', color: '#e8b04b', route: true, points: [
      { id: 'bethlehem-j', name_zh: '伯利恒', name_en: 'Bethlehem', lng: 35.20, lat: 31.70, order: 1, confidence: 'identified', scriptureRef: '路2:1-20', events: [
        { title: '道成肉身', ref: '路2:7', summary: '耶稣在伯利恒的马槽降生，天使向牧羊人报大喜的信息；应验弥迦书"伯利恒…将来必有一位为我作以色列的君王"。' },
      ] },
      { id: 'nazareth-j', name_zh: '拿撒勒', name_en: 'Nazareth', lng: 35.30, lat: 32.70, order: 2, confidence: 'identified', scriptureRef: '路2:39-52;4:16-30', events: [
        { title: '成长与受拒', ref: '路4:18-21', summary: '耶稣在拿撒勒长大；在会堂读以赛亚书宣告应验在自己身上，乡人却不接纳他。' },
      ] },
      { id: 'jordan-j', name_zh: '约旦河', name_en: 'Jordan River', lng: 35.55, lat: 31.84, order: 3, confidence: 'approximate', scriptureRef: '太3:13-17', events: [
        { title: '受洗与圣灵降临', ref: '太3:16-17', summary: '约翰为耶稣施洗，天开了，圣灵仿佛鸽子降下，有声音说："这是我的爱子，我所喜悦的。"' },
      ] },
      { id: 'capernaum-j', name_zh: '迦百农', name_en: 'Capernaum', lng: 35.57, lat: 32.88, order: 4, confidence: 'identified', scriptureRef: '太4:13;可2', events: [
        { title: '传道的中心', ref: '太4:13-17', summary: '耶稣以迦百农为加利利事工的基地，呼召门徒、医病赶鬼、宣讲天国近了。' },
      ] },
      { id: 'galilee-j', name_zh: '加利利海', name_en: 'Sea of Galilee', lng: 35.59, lat: 32.82, order: 5, confidence: 'identified', scriptureRef: '可4;6;太14', events: [
        { title: '平静风浪、五饼二鱼', ref: '可4:39;太14:19-21', summary: '在加利利海上斥责风浪、海面行走，又以五饼二鱼喂饱五千人，显明他是创造的主。' },
      ] },
      { id: 'jerusalem-j2', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, order: 6, confidence: 'identified', scriptureRef: '路19;太27-28', events: [
        { title: '受难', ref: '路23:33;46', summary: '耶稣骑驴荣入圣城，最后晚餐后于客西马尼被卖，在各各他被钉十字架，为世人的罪受死。' },
        { title: '复活', ref: '路24:6', summary: '第三日清晨坟墓空了——"他不在这里，已经复活了！"死亡被胜过，福音由此传向万邦。' },
      ] },
    ],
  }],
}

// —— 9. 保罗宣教 ——
const paul = {
  id: 'paul',
  title: '保罗宣教地图',
  subtitle: '三次宣教旅程 + 罗马之旅 · 沿途书信与教会',
  era: '约公元 46–62',
  badge: '★★★★★',
  bounds: { minLng: 11, maxLng: 38, minLat: 30, maxLat: 42.5 },
  mode: 'journey',
  layerSelect: 'single',
  layers: [
    { id: 'first', label: '第一次宣教', color: '#e8b04b', route: true, points: [
      { id: 'antioch1', name_zh: '安提阿（叙利亚）', name_en: 'Antioch', lng: 36.16, lat: 36.20, order: 1, confidence: 'identified', scriptureRef: '徒13:1-3', events: [
        { title: '差遣的母会', ref: '徒13:2-3', summary: '圣灵说："要为我分派巴拿巴和扫罗。"教会禁食祷告、按手差遣，宣教运动从此展开。' },
      ] },
      { id: 'cyprus', name_zh: '塞浦路斯（帕弗）', name_en: 'Paphos', lng: 32.42, lat: 34.76, order: 2, confidence: 'identified', scriptureRef: '徒13:4-12', events: [
        { title: '方伯归信', ref: '徒13:12', summary: '在帕弗，扫罗（保罗）斥责行法术的以吕马，方伯士求保罗看见神迹就信了。' },
      ] },
      { id: 'pisidian', name_zh: '彼西底的安提阿', name_en: 'Pisidian Antioch', lng: 31.19, lat: 38.31, order: 3, confidence: 'identified', scriptureRef: '徒13:14-50', events: [
        { title: '转向外邦', ref: '徒13:46', summary: '犹太人弃绝福音，保罗宣告："我们就转向外邦人去。"福音临到外邦。' },
      ] },
      { id: 'lystra1', name_zh: '路司得', name_en: 'Lystra', lng: 32.45, lat: 37.58, order: 4, confidence: 'identified', scriptureRef: '徒14:8-20', events: [
        { title: '被误为神、又遭石击', ref: '徒14:19', summary: '医好瘸腿者后被当作神明；随后犹太人煽动用石头打保罗，以为他死了。提摩太的家乡。' },
      ] },
    ] },
    { id: 'second', label: '第二次宣教', color: '#5ec2e8', route: true, points: [
      { id: 'antioch2', name_zh: '安提阿', name_en: 'Antioch', lng: 36.16, lat: 36.20, order: 1, confidence: 'identified', scriptureRef: '徒15:36', events: [] },
      { id: 'troas', name_zh: '特罗亚', name_en: 'Troas', lng: 26.24, lat: 39.76, order: 2, confidence: 'identified', scriptureRef: '徒16:8-10', events: [
        { title: '马其顿的异象', ref: '徒16:9', summary: '夜间异象中有马其顿人求："请过来帮助我们。"福音由此首次进入欧洲。' },
      ] },
      { id: 'philippi', name_zh: '腓立比', name_en: 'Philippi', lng: 24.29, lat: 41.01, order: 3, confidence: 'identified', scriptureRef: '徒16:11-40', note: '日后写《腓立比书》给此教会。', events: [
        { title: '吕底亚信主、狱中歌唱', ref: '徒16:25-34', summary: '卖紫布的吕底亚归主；保罗西拉被下监，半夜祷告唱诗，地大震动，禁卒全家信主。欧洲第一间教会。' },
      ] },
      { id: 'thessalonica', name_zh: '帖撒罗尼迦', name_en: 'Thessalonica', lng: 22.94, lat: 40.64, order: 4, confidence: 'identified', scriptureRef: '徒17:1-9', note: '日后写《帖撒罗尼迦前后书》。', events: [] },
      { id: 'athens', name_zh: '雅典', name_en: 'Athens', lng: 23.73, lat: 37.98, order: 5, confidence: 'identified', scriptureRef: '徒17:16-34', events: [
        { title: '亚略巴古的讲论', ref: '徒17:23', summary: '保罗借"未识之神"的坛向哲士传讲创造、复活与审判的真神。' },
      ] },
      { id: 'corinth2', name_zh: '哥林多', name_en: 'Corinth', lng: 22.93, lat: 37.94, order: 6, confidence: 'identified', scriptureRef: '徒18:1-18', note: '停留一年半；在此写《帖撒罗尼迦前后书》。', events: [
        { title: '与亚居拉、百基拉同工', ref: '徒18:1-11', summary: '保罗以织帐棚为业，与亚居拉夫妇同工；主在异象中说"有许多的百姓"，他便住下教导一年半。' },
      ] },
    ] },
    { id: 'third', label: '第三次宣教', color: '#4ade80', route: true, points: [
      { id: 'antioch3', name_zh: '安提阿', name_en: 'Antioch', lng: 36.16, lat: 36.20, order: 1, confidence: 'identified', scriptureRef: '徒18:23', events: [] },
      { id: 'ephesus3', name_zh: '以弗所', name_en: 'Ephesus', lng: 27.34, lat: 37.94, order: 2, confidence: 'identified', scriptureRef: '徒19', note: '停留约三年；在此写《哥林多前书》。', events: [
        { title: '三年事工与银匠骚动', ref: '徒19:10;23-41', summary: '主的道大大兴旺，焚烧邪术书籍；银匠底米丢因亚底米庙生意受损煽动全城骚乱。' },
      ] },
      { id: 'corinth3', name_zh: '哥林多', name_en: 'Corinth', lng: 22.93, lat: 37.94, order: 3, confidence: 'identified', scriptureRef: '徒20:2-3', note: '在此写《罗马书》。', events: [
        { title: '写《罗马书》', ref: '罗15:23-25', summary: '保罗在哥林多过冬，写信给罗马教会，阐明因信称义的福音，预备前往耶路撒冷与罗马。' },
      ] },
      { id: 'miletus', name_zh: '米利都', name_en: 'Miletus', lng: 27.28, lat: 37.53, order: 4, confidence: 'identified', scriptureRef: '徒20:17-38', events: [
        { title: '与以弗所长老泣别', ref: '徒20:36-38', summary: '保罗预言此去必遭捆锁，与众长老跪下祷告、抱颈痛哭告别。' },
      ] },
      { id: 'jerusalem-p', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, order: 5, confidence: 'identified', scriptureRef: '徒21:17-33', events: [
        { title: '被捕', ref: '徒21:33', summary: '保罗在圣殿被诬告引发骚乱，被罗马千夫长拿住，自此进入长期受审与监禁。' },
      ] },
    ] },
    { id: 'rome', label: '罗马之旅', color: '#c084fc', route: true, points: [
      { id: 'caesarea', name_zh: '该撒利亚', name_en: 'Caesarea', lng: 34.89, lat: 32.50, order: 1, confidence: 'identified', scriptureRef: '徒25:11-12', events: [
        { title: '上诉该撒', ref: '徒25:11', summary: '保罗在该撒利亚受审两年，向非斯都说："我要上告于该撒。"于是被解往罗马。' },
      ] },
      { id: 'fairhavens', name_zh: '佳澳（克里特）', name_en: 'Fair Havens', lng: 24.91, lat: 34.90, order: 2, confidence: 'approximate', scriptureRef: '徒27:8-13', events: [] },
      { id: 'malta', name_zh: '米利大（马耳他）', name_en: 'Malta', lng: 14.51, lat: 35.90, order: 3, confidence: 'identified', scriptureRef: '徒27:39-28:10', events: [
        { title: '海难与毒蛇', ref: '徒28:3-6', summary: '船遇友拉革罗大风破损，众人游泳上岸；保罗被毒蛇咬却毫无损伤，又医好岛上病人。' },
      ] },
      { id: 'puteoli', name_zh: '部丢利', name_en: 'Puteoli', lng: 14.12, lat: 40.82, order: 4, confidence: 'identified', scriptureRef: '徒28:13-14', events: [] },
      { id: 'rome', name_zh: '罗马', name_en: 'Rome', lng: 12.50, lat: 41.90, order: 5, confidence: 'identified', scriptureRef: '徒28:16-31', note: '软禁中写《以弗所书》《腓立比书》《歌罗西书》《腓利门书》等监狱书信。', events: [
        { title: '在罗马放胆传道', ref: '徒28:30-31', summary: '保罗在自己所租的房子住了两年，放胆传讲神国的道，将主耶稣基督的事教导人，并没有人禁止。' },
      ] },
    ] },
  ],
}

// —— 10. 启示录七教会 ——
const sevenChurches = {
  id: 'seven-churches',
  title: '启示录七教会地图',
  subtitle: '亚细亚七间教会 · 优点 / 责备 / 应许',
  era: '约公元 95',
  badge: '★★★★★',
  bounds: { minLng: 26.5, maxLng: 29.7, minLat: 37.5, maxLat: 39.4 },
  mode: 'journey',
  layerSelect: 'multi',
  layers: [{
    id: 'churches', label: '七教会（书信次序）', color: '#e8b04b', route: true, points: [
      { id: 'ephesus-c', name_zh: '以弗所', name_en: 'Ephesus', lng: 27.34, lat: 37.94, order: 1, confidence: 'identified', scriptureRef: '启2:1-7', events: [
        { title: '优点', ref: '启2:2-3', summary: '劳碌、忍耐、恨恶恶人、试验假使徒、为主名劳苦不乏倦。' },
        { title: '责备', ref: '启2:4', summary: '"把起初的爱心离弃了。"', },
        { title: '应许', ref: '启2:7', summary: '得胜的，必将神乐园中生命树的果子赐他吃。' },
      ] },
      { id: 'smyrna-c', name_zh: '士每拿', name_en: 'Smyrna', lng: 27.14, lat: 38.42, order: 2, confidence: 'identified', scriptureRef: '启2:8-11', events: [
        { title: '优点', ref: '启2:9', summary: '在患难、贫穷中却是富足的（受逼迫的忠心教会，主无责备）。' },
        { title: '应许', ref: '启2:10-11', summary: '务要至死忠心，主赐生命的冠冕；得胜的必不受第二次死的害。' },
      ] },
      { id: 'pergamum-c', name_zh: '别迦摩', name_en: 'Pergamum', lng: 27.18, lat: 39.13, order: 3, confidence: 'identified', scriptureRef: '启2:12-17', events: [
        { title: '优点', ref: '启2:13', summary: '住在撒但座位之处仍坚守主名，在见证人安提帕殉道时也没有弃绝信仰。' },
        { title: '责备', ref: '启2:14-15', summary: '容让巴兰的教训与尼哥拉党的教训（拜偶像、行奸淫）。' },
        { title: '应许', ref: '启2:17', summary: '得胜的，主赐隐藏的吗哪，并写着新名的白石。' },
      ] },
      { id: 'thyatira-c', name_zh: '推雅推喇', name_en: 'Thyatira', lng: 27.84, lat: 38.92, order: 4, confidence: 'identified', scriptureRef: '启2:18-29', events: [
        { title: '优点', ref: '启2:19', summary: '爱心、信心、勤劳、忍耐，且末后所行的善事比起初更多。' },
        { title: '责备', ref: '启2:20', summary: '容让自称先知的妇人耶洗别引诱仆人行奸淫、吃祭偶像之物。' },
        { title: '应许', ref: '启2:26-28', summary: '得胜的，主赐他权柄制伏列国，又把晨星赐给他。' },
      ] },
      { id: 'sardis-c', name_zh: '撒狄', name_en: 'Sardis', lng: 28.04, lat: 38.49, order: 5, confidence: 'identified', scriptureRef: '启3:1-6', events: [
        { title: '责备', ref: '启3:1-2', summary: '"按名你是活的，其实是死的。"行为在神面前没有一样是完全的。' },
        { title: '优点（少数）', ref: '启3:4', summary: '还有几名素来未曾污秽自己衣服的，必穿白衣与主同行。' },
        { title: '应许', ref: '启3:5', summary: '得胜的必穿白衣，主不从生命册上涂抹他的名，且在父与众使者面前认他的名。' },
      ] },
      { id: 'philadelphia-c', name_zh: '非拉铁非', name_en: 'Philadelphia', lng: 28.66, lat: 38.34, order: 6, confidence: 'identified', scriptureRef: '启3:7-13', events: [
        { title: '优点', ref: '启3:8', summary: '略有一点力量，却遵守主的道，没有弃绝主的名（忠心教会，主无责备）。' },
        { title: '应许', ref: '启3:8-12', summary: '主在他面前给他一个敞开的门；得胜的要作神殿中的柱子，写上神的名、新耶路撒冷的名。' },
      ] },
      { id: 'laodicea-c', name_zh: '老底嘉', name_en: 'Laodicea', lng: 29.11, lat: 37.84, order: 7, confidence: 'identified', scriptureRef: '启3:14-22', events: [
        { title: '责备', ref: '启3:15-17', summary: '不冷不热，自以为富足、一样都不缺，却不知是困苦、可怜、贫穷、瞎眼、赤身的。' },
        { title: '劝勉与应许', ref: '启3:18-20', summary: '"看哪，我站在门外叩门。"得胜的，主赐他在自己宝座上与主同坐。' },
      ] },
    ],
  }],
}

// —— 11. 圣经时间轴融合（救赎历史主线）——
const timeline = {
  id: 'timeline',
  title: '圣经时间轴 + 地图融合',
  subtitle: '拖动年份，看救赎历史在地图上展开（核心壁垒）',
  era: '公元前 2100 – 公元 95',
  badge: '★★★★★★',
  bounds: { minLng: 11, maxLng: 48, minLat: 14, maxLat: 42 },
  mode: 'timeline',
  layerSelect: 'multi',
  years: { min: -2100, max: 100, default: 100, step: 5 },
  eras: [
    { label: '族长', from: -2100, to: -1500 },
    { label: '出埃及', from: -1499, to: -1100 },
    { label: '王国', from: -1099, to: -600 },
    { label: '被掳归回', from: -599, to: -1 },
    { label: '新约', from: 0, to: 100 },
  ],
  layers: [{
    id: 'redemption', label: '救赎历史里程碑', color: '#e8b04b', route: false, points: [
      { id: 't-abraham', name_zh: '亚伯拉罕蒙召', name_en: 'Abraham', lng: 35.10, lat: 31.53, year: -2091, confidence: 'approximate', scriptureRef: '创12', events: [
        { title: '应许之约', ref: '创12:2-3', summary: '神拣选亚伯拉罕，应许使他成为大国，地上万族都要因他得福——救赎计划的起点。' },
      ] },
      { id: 't-egypt', name_zh: '寄居埃及', name_en: 'In Egypt', lng: 31.20, lat: 30.10, year: -1876, confidence: 'approximate', scriptureRef: '创46-50', events: [
        { title: '约瑟与下埃及', ref: '创46', summary: '雅各全家因约瑟下到埃及，寄居四百多年，渐成大族。' },
      ] },
      { id: 't-exodus', name_zh: '出埃及与西奈立约', name_en: 'Exodus', lng: 33.97, lat: 28.54, year: -1446, confidence: 'approximate', scriptureRef: '出20', events: [
        { title: '律法与立约', ref: '出19-20', summary: '摩西领以色列出埃及，在西奈山领受十诫，神与以色列立约成为祭司的国度。' },
      ] },
      { id: 't-conquest', name_zh: '约书亚进迦南', name_en: 'Conquest', lng: 35.44, lat: 31.87, year: -1406, confidence: 'approximate', scriptureRef: '书6', events: [
        { title: '得地为业', ref: '书11:23', summary: '约书亚率以色列攻取迦南，按支派分地，应许之地初步成就。' },
      ] },
      { id: 't-david', name_zh: '大卫建都耶路撒冷', name_en: 'David', lng: 35.235, lat: 31.778, year: -1003, confidence: 'identified', scriptureRef: '撒下5', events: [
        { title: '大卫之约', ref: '撒下7:16', summary: '神应许大卫的国位必坚立到永远，指向将来的弥赛亚君王。' },
      ] },
      { id: 't-solomon', name_zh: '所罗门建圣殿', name_en: 'Temple', lng: 35.235, lat: 31.778, year: -966, confidence: 'identified', scriptureRef: '王上6', events: [
        { title: '圣殿落成', ref: '王上8:11', summary: '耶和华的荣光充满圣殿，敬拜有了中心，王国进入黄金时代。' },
      ] },
      { id: 't-fall-n', name_zh: '北国亡于亚述', name_en: 'Assyria', lng: 35.19, lat: 32.28, year: -722, confidence: 'identified', scriptureRef: '王下17', events: [
        { title: '撒玛利亚陷落', ref: '王下17:6', summary: '北国以色列被亚述所灭，十支派分散。' },
      ] },
      { id: 't-exile', name_zh: '被掳巴比伦', name_en: 'Exile', lng: 44.42, lat: 32.54, year: -586, confidence: 'identified', scriptureRef: '王下25', events: [
        { title: '圣殿被毁、被掳七十年', ref: '耶25:11', summary: '巴比伦灭南国、焚圣殿，犹大被掳；但神借先知应许七十年后归回。' },
      ] },
      { id: 't-return', name_zh: '归回重建', name_en: 'Return', lng: 35.235, lat: 31.778, year: -538, confidence: 'identified', scriptureRef: '拉1;尼2', events: [
        { title: '波斯王下诏归回', ref: '拉1:1-3', summary: '古列王下诏准犹大人回耶路撒冷重建圣殿；以斯拉、尼希米带领重建殿与城墙。' },
      ] },
      { id: 't-jesus', name_zh: '耶稣降生与救赎', name_en: 'Jesus', lng: 35.20, lat: 31.70, year: 1, confidence: 'identified', scriptureRef: '路2;太27-28', events: [
        { title: '道成肉身、受死复活', ref: '约1:14', summary: '神的儿子降生、受死、复活，成就一切应许，新约由此开启。' },
      ] },
      { id: 't-church', name_zh: '教会与万邦', name_en: 'The Church', lng: 12.50, lat: 41.90, year: 60, confidence: 'identified', scriptureRef: '徒2;28', events: [
        { title: '福音传到地极', ref: '徒1:8', summary: '五旬节圣灵降临，教会诞生；保罗等人将福音从耶路撒冷传至罗马与万邦。' },
      ] },
    ],
  }],
}

// —— 12. 圣经人物轨迹 ——
const characters = {
  id: 'characters',
  title: '圣经人物轨迹地图',
  subtitle: '选择人物，看其出生地、活动地与旅程',
  era: '跨越两千年',
  badge: '★★★★★★',
  bounds: { minLng: 11, maxLng: 48, minLat: 14, maxLat: 42 },
  mode: 'journey',
  layerSelect: 'single',
  profile: true,
  layers: [
    { id: 'c-abraham', label: '亚伯拉罕', color: '#e8b04b', route: true, era: '约公元前 2166–1991', scene: 'altar', bio: '信心之父。蒙神呼召离开吾珥，凭信心寄居应许之地；神与他立约，应许其后裔如天上的星、万族因他得福。', points: [
      { id: 'ca-ur', name_zh: '吾珥（出生）', name_en: 'Ur', lng: 46.10, lat: 30.96, order: 1, confidence: 'identified', scriptureRef: '创11:28', events: [{ title: '本家之地', ref: '创11:31', summary: '亚伯拉罕生于迦勒底的吾珥。' }] },
      { id: 'ca-haran', name_zh: '哈兰', name_en: 'Haran', lng: 39.03, lat: 36.86, order: 2, confidence: 'identified', scriptureRef: '创12:4', events: [{ title: '蒙召起行', ref: '创12:4', summary: '七十五岁离哈兰往迦南。' }] },
      { id: 'ca-shechem', name_zh: '示剑', name_en: 'Shechem', lng: 35.28, lat: 32.21, order: 3, confidence: 'identified', scriptureRef: '创12:6-7', altar: '进迦南第一座坛', events: [] },
      { id: 'ca-hebron', name_zh: '希伯仑（终）', name_en: 'Hebron', lng: 35.10, lat: 31.53, order: 4, confidence: 'identified', scriptureRef: '创23', events: [{ title: '麦比拉洞', ref: '创23', summary: '葬于希伯仑麦比拉洞。' }] },
    ] },
    { id: 'c-moses', label: '摩西', color: '#5ec2e8', route: true, era: '约公元前 1526–1406', scene: 'tablets', bio: '以色列的领袖与立法者。在荆棘火焰中蒙召，领以色列出埃及、过红海，在西奈山领受十诫与律法，带领百姓走过旷野四十年。', points: [
      { id: 'cm-egypt', name_zh: '埃及（出生/王宫）', name_en: 'Egypt', lng: 31.20, lat: 30.10, order: 1, confidence: 'approximate', scriptureRef: '出2', events: [{ title: '蒙救与长大', ref: '出2:10', summary: '生于埃及，被法老女儿收养长大。' }] },
      { id: 'cm-midian', name_zh: '米甸', name_en: 'Midian', lng: 35.40, lat: 28.40, order: 2, confidence: 'approximate', scriptureRef: '出3', altar: '何烈山荆棘火焰中蒙召', events: [{ title: '荆棘异象', ref: '出3:2', summary: '逃往米甸牧羊四十年，在何烈山火焰中蒙召。' }] },
      { id: 'cm-sinai', name_zh: '西奈山', name_en: 'Mt Sinai', lng: 33.97, lat: 28.54, order: 3, confidence: 'identified', scriptureRef: '出20', altar: '领受十诫、立约', events: [{ title: '颁布律法', ref: '出20', summary: '领以色列出埃及，在西奈领受律法。' }] },
      { id: 'cm-nebo', name_zh: '尼波山（终）', name_en: 'Mt Nebo', lng: 35.73, lat: 31.77, order: 4, confidence: 'approximate', scriptureRef: '申34', events: [{ title: '遥望应许之地', ref: '申34:1-5', summary: '在尼波山遥望迦南后逝世。' }] },
    ] },
    { id: 'c-david', label: '大卫', color: '#ff6b6b', route: true, era: '约公元前 1040–970', scene: 'crown', bio: '合神心意的牧人君王。从伯利恒牧场受膏，凭信心击杀歌利亚，建都耶路撒冷；神应许他的国位坚立到永远。诗篇多出其手。', points: [
      { id: 'cd-beth', name_zh: '伯利恒（出生）', name_en: 'Bethlehem', lng: 35.20, lat: 31.70, order: 1, confidence: 'identified', scriptureRef: '撒上16', events: [{ title: '受膏', ref: '撒上16:13', summary: '牧童大卫在伯利恒受撒母耳膏立。' }] },
      { id: 'cd-elah', name_zh: '以拉谷', name_en: 'Elah', lng: 34.96, lat: 31.69, order: 2, confidence: 'approximate', scriptureRef: '撒上17', events: [{ title: '战胜歌利亚', ref: '撒上17', summary: '凭信心击杀巨人歌利亚。' }] },
      { id: 'cd-hebron', name_zh: '希伯仑', name_en: 'Hebron', lng: 35.10, lat: 31.53, order: 3, confidence: 'identified', scriptureRef: '撒下2', events: [{ title: '作犹大王', ref: '撒下2:4', summary: '先在希伯仑作王七年半。' }] },
      { id: 'cd-jeru', name_zh: '耶路撒冷', name_en: 'Jerusalem', lng: 35.235, lat: 31.778, order: 4, confidence: 'identified', scriptureRef: '撒下5', events: [{ title: '建都、立约', ref: '撒下5-7', summary: '攻取耶布斯定为京城，神立永约。' }] },
    ] },
    { id: 'c-elijah', label: '以利亚', color: '#4ade80', route: true, era: '约公元前 9 世纪', scene: 'fire', bio: '烈火先知。在亚哈王拜巴力的黑暗年代为耶和华争战，于迦密山求火降下证明真神，最终乘旋风火车被接升天。', points: [
      { id: 'ce-gilead', name_zh: '提斯比（基列）', name_en: 'Tishbe', lng: 35.75, lat: 32.30, order: 1, confidence: 'approximate', scriptureRef: '王上17:1', events: [{ title: '宣告旱灾', ref: '王上17:1', summary: '基列的提斯比人以利亚宣告三年不下雨。' }] },
      { id: 'ce-cherith', name_zh: '基立溪', name_en: 'Cherith', lng: 35.62, lat: 32.05, order: 2, confidence: 'approximate', scriptureRef: '王上17:2-6', events: [{ title: '乌鸦供养', ref: '王上17:6', summary: '神命乌鸦早晚叼饼和肉供养他。' }] },
      { id: 'ce-carmel', name_zh: '迦密山', name_en: 'Carmel', lng: 35.03, lat: 32.73, order: 3, confidence: 'identified', scriptureRef: '王上18', altar: '重修耶和华的坛，求火降下', events: [{ title: '斗巴力先知', ref: '王上18:38', summary: '求火降下，证明耶和华是神。' }] },
      { id: 'ce-horeb', name_zh: '何烈山', name_en: 'Horeb', lng: 33.97, lat: 28.54, order: 4, confidence: 'identified', scriptureRef: '王上19', events: [{ title: '微小的声音', ref: '王上19:12', summary: '在何烈山洞口，神不在风火地震中，而在微小的声音里。' }] },
    ] },
    { id: 'c-paul', label: '保罗', color: '#c084fc', route: true, era: '约公元 5–67', scene: 'boat', epistles: ['罗马书','哥林多前后书','加拉太书','以弗所书','腓立比书','歌罗西书','帖前后书','提摩太前后书','提多书','腓利门书'], bio: '外邦人的使徒。原为逼迫教会的法利赛人，在大马士革路上蒙主光照归主；三次宣教旅程遍传福音，写下十三卷书信，最终在罗马为主作见证。', points: [
      { id: 'cp-tarsus', name_zh: '大数（出生）', name_en: 'Tarsus', lng: 34.90, lat: 36.92, order: 1, confidence: 'identified', scriptureRef: '徒22:3', events: [{ title: '生于大数', ref: '徒22:3', summary: '生在基利家的大数，长在耶路撒冷迦玛列门下。' }] },
      { id: 'cp-damascus', name_zh: '大马士革路上', name_en: 'Damascus', lng: 36.30, lat: 33.51, order: 2, confidence: 'identified', scriptureRef: '徒9', events: [{ title: '蒙光照归主', ref: '徒9:3-6', summary: '往大马士革途中被大光照住，听见主的声音，从逼迫者变为使徒。' }] },
      { id: 'cp-antioch', name_zh: '安提阿', name_en: 'Antioch', lng: 36.16, lat: 36.20, order: 3, confidence: 'identified', scriptureRef: '徒13', events: [{ title: '宣教的差遣地', ref: '徒13:2-3', summary: '从安提阿被圣灵差派，三次宣教旅程的起点。' }] },
      { id: 'cp-rome', name_zh: '罗马（终）', name_en: 'Rome', lng: 12.50, lat: 41.90, order: 4, confidence: 'identified', scriptureRef: '徒28', events: [{ title: '在罗马传道', ref: '徒28:30-31', summary: '被解到罗马，软禁中仍放胆传讲神国的道。' }] },
    ] },
  ],
}

export const BIBLE_MAPS = [
  abraham, exodus, joshua, tribes, david, solomon,
  dividedKingdom, jesus, paul, sevenChurches, timeline, characters,
]

export const BIBLE_MAPS_BY_ID = Object.fromEntries(BIBLE_MAPS.map(m => [m.id, m]))
