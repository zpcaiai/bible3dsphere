// 出埃及与旷野漂流 — 民数记33章 42个安营站点
// GeoJSON FeatureCollection。geometry 坐标为 [lng, lat]（GeoJSON 标准）。
//
// 数据结构按"时效性地名"模型设计，兼容未来 PostGIS 表：
//   properties.names: [{ name_zh, name_en, name_he, start_year, end_year }]
//   一个坐标点可承载多个不同历史时期的名称（如 Jebus → 大卫的城）。
//
// confidence: 'identified'(考古较确定) | 'approximate'(传统推定/有争议) | 'unknown'(地点失考，沿路线示意放置)
// 注：出埃及年代学界有早期(约公元前1446)与晚期(约公元前1260)两说；此处站点采用传统南方西奈路线推定。

export const EXODUS_ERA_YEAR = -1446 // 传统早期年代（公元前1446），仅作时效性基准

function station(order, id, name_zh, name_en, name_he, lng, lat, confidence, ref, events) {
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [lng, lat] },
    properties: {
      id,
      order,
      confidence,
      scriptureRef: ref,                 // 民数记33章经节
      names: [
        { name_zh, name_en, name_he: name_he || '', start_year: EXODUS_ERA_YEAR - 40, end_year: EXODUS_ERA_YEAR },
      ],
      name_zh, name_en, name_he: name_he || '',
      events: events || [],              // [{ title, ref, summary }]
    },
  }
}

export const exodusStations = {
  type: 'FeatureCollection',
  features: [
    station(1,'rameses','兰塞','Rameses','רַעְמְסֵס',31.83,30.80,'approximate','民33:5',[
      {title:'逾越节之后出发', ref:'出12:37', summary:'以色列人吃完逾越节羊羔，从兰塞起行往疏割去，约有步行的男人六十万。'},
    ]),
    station(2,'succoth','疏割','Succoth','סֻכּוֹת',32.10,30.55,'approximate','民33:6',[
      {title:'耶和华昼夜引导', ref:'出13:21', summary:'白天云柱、夜间火柱在前头行，照亮道路。'},
    ]),
    station(3,'etham','以倘','Etham','אֵתָם',32.35,30.42,'approximate','民33:7',[
      {title:'安营在旷野边缘', ref:'出13:20', summary:'在旷野边的以倘安营。'},
    ]),
    station(4,'pi-hahiroth','比哈希录（过红海）','Pi-hahiroth','פִּי הַחִירֹת',32.55,30.05,'approximate','民33:7-8',[
      {title:'过红海，法老追兵覆没', ref:'出14:21-28', summary:'摩西伸杖，海水分开，以色列人走干地过海；法老的车辆马兵随后下海，水回流将其淹没。'},
      {title:'米利暗的凯歌', ref:'出15:20-21', summary:'女先知米利暗手拿鼓，众妇女随她歌舞，颂赞耶和华大大战胜。'},
    ]),
    station(5,'marah','玛拉','Marah','מָרָה',33.08,29.22,'approximate','民33:8',[
      {title:'苦水变甜', ref:'出15:23-25', summary:'百姓因水苦发怨言，耶和华指示摩西把一棵树丢进水里，水就变甜。'},
    ]),
    station(6,'elim','以琳','Elim','אֵילִם',33.13,29.10,'approximate','民33:9',[
      {title:'十二股水泉、七十棵棕树', ref:'出15:27', summary:'到了以琳，那里有十二股水泉、七十棵棕树，就在水边安营。'},
    ]),
    station(7,'red-sea','红海边','By the Red Sea','יַם סוּף',33.18,28.92,'approximate','民33:10',[]),
    station(8,'wild-sin','汛的旷野','Wilderness of Sin','מִדְבַּר סִין',33.42,28.78,'approximate','民33:11',[
      {title:'天降吗哪与鹌鹑', ref:'出16:13-15', summary:'晚上有鹌鹑遮满营地，早晨降下吗哪如白霜，作为四十年的日用饮食。'},
    ]),
    station(9,'dophkah','脱加','Dophkah','דָּפְקָה',33.46,28.90,'unknown','民33:12',[]),
    station(10,'alush','亚录','Alush','אָלוּשׁ',33.60,28.80,'unknown','民33:13',[]),
    station(11,'rephidim','利非订','Rephidim','רְפִידִים',33.66,28.72,'approximate','民33:14',[
      {title:'击打磐石出水', ref:'出17:5-6', summary:'百姓无水喝，耶和华吩咐摩西击打何烈的磐石，就有水流出供百姓饮用。'},
      {title:'与亚玛力人争战', ref:'出17:11-13', summary:'摩西举手以色列得胜；亚伦与户珥扶他的手到日落，约书亚击败亚玛力人。'},
    ]),
    station(12,'sinai','西奈山','Mount Sinai','הַר סִינַי',33.975,28.539,'identified','民33:15',[
      {title:'颁布十诫与立约', ref:'出20:1-17', summary:'耶和华在烟火雷电中降临西奈山，亲口宣告十条诫命，与以色列立约。'},
      {title:'金牛犊与会幕', ref:'出32; 出40', summary:'百姓铸金牛犊犯罪；其后照耶和华的样式建造会幕，荣耀充满帐幕。'},
    ]),
    station(13,'kibroth','基博罗哈他瓦（贪欲之坟）','Kibroth-hattaavah','קִבְרוֹת הַתַּאֲוָה',34.10,28.72,'unknown','民33:16',[
      {title:'贪欲与鹌鹑之灾', ref:'民11:31-34', summary:'百姓贪恋肉食，耶和华降下大量鹌鹑，随后以重灾击杀贪欲的人，故名"贪欲的坟墓"。'},
    ]),
    station(14,'hazeroth','哈洗录','Hazeroth','חֲצֵרוֹת',34.42,28.92,'approximate','民33:17',[
      {title:'米利暗与亚伦毁谤摩西', ref:'民12:1-10', summary:'米利暗与亚伦因摩西的妻子毁谤他，米利暗长了大麻风，经摩西代求后得医治。'},
    ]),
    station(15,'rithmah','利提玛','Rithmah','רִתְמָה',34.30,29.35,'unknown','民33:18',[]),
    station(16,'rimmon-perez','临门帕烈','Rimmon-perez','רִמֹּן פֶּרֶץ',34.40,29.65,'unknown','民33:19',[]),
    station(17,'libnah','立拿','Libnah','לִבְנָה',34.46,29.92,'unknown','民33:20',[]),
    station(18,'rissah','勒撒','Rissah','רִסָּה',34.56,30.05,'unknown','民33:21',[]),
    station(19,'kehelathah','基希拉他','Kehelathah','קְהֵלָתָה',34.66,30.10,'unknown','民33:22',[]),
    station(20,'shepher','沙斐山','Mount Shepher','הַר שָׁפֶר',34.76,30.02,'unknown','民33:23',[]),
    station(21,'haradah','哈拉大','Haradah','חֲרָדָה',34.82,29.88,'unknown','民33:24',[]),
    station(22,'makheloth','玛吉希录','Makheloth','מַקְהֵלֹת',34.86,29.74,'unknown','民33:25',[]),
    station(23,'tahath','他哈','Tahath','תָּחַת',34.90,29.64,'unknown','民33:26',[]),
    station(24,'terah','他拉','Terah','תָּרַח',34.92,29.55,'unknown','民33:27',[]),
    station(25,'mithkah','密加','Mithkah','מִתְקָה',34.95,29.50,'unknown','民33:28',[]),
    station(26,'hashmonah','哈摩拿','Hashmonah','חַשְׁמֹנָה',34.97,29.48,'unknown','民33:29',[]),
    station(27,'moseroth','摩西录','Moseroth','מֹסֵרוֹת',35.00,29.46,'unknown','民33:30',[]),
    station(28,'bene-jaakan','比尼亚干','Bene-jaakan','בְּנֵי יַעֲקָן',34.98,29.54,'unknown','民33:31',[]),
    station(29,'hor-haggidgad','曷哈及甲','Hor-haggidgad','חֹר הַגִּדְגָּד',34.99,29.51,'unknown','民33:32',[]),
    station(30,'jotbathah','约巴他','Jotbathah','יָטְבָתָה',34.96,29.58,'unknown','民33:33',[]),
    station(31,'abronah','阿博拿','Abronah','עַבְרֹנָה',34.96,29.53,'unknown','民33:34',[]),
    station(32,'ezion-geber','以旬迦别','Ezion-geber','עֶצְיֹן גֶּבֶר',34.976,29.540,'identified','民33:35',[
      {title:'红海北端的港口', ref:'王上9:26', summary:'后世所罗门在此（亚喀巴湾畔）建造船队的港口；以色列人曾在此安营。'},
    ]),
    station(33,'kadesh','加低斯（寻的旷野）','Kadesh','קָדֵשׁ',34.43,30.65,'identified','民33:36',[
      {title:'十二个探子窥探迦南', ref:'民13:25-14:4', summary:'探子回报后百姓发怨言不肯进迦南，被罚在旷野漂流四十年，直到那世代倒毙。'},
      {title:'米利暗逝世', ref:'民20:1', summary:'以色列全会众到了寻的旷野加低斯，米利暗死在那里，葬在那里。'},
      {title:'摩西击磐石犯罪', ref:'民20:10-12', summary:'摩西没有照吩咐"吩咐"磐石，反而两次击打它，因不尊耶和华为圣，被禁止进入应许之地。'},
    ]),
    station(34,'mount-hor','何珥山','Mount Hor','הֹר הָהָר',35.40,30.32,'approximate','民33:37-39',[
      {title:'亚伦逝世', ref:'民20:25-28', summary:'亚伦在何珥山顶脱下圣衣给以利亚撒，死在山上，全会众为他哀哭三十天。'},
    ]),
    station(35,'zalmonah','撒摩拿（铜蛇事件）','Zalmonah','צַלְמֹנָה',35.45,30.45,'unknown','民33:41',[
      {title:'铜蛇与火蛇', ref:'民21:6-9', summary:'百姓发怨言，耶和华使火蛇咬死多人；摩西照命造铜蛇挂木杆上，仰望铜蛇的就得存活。'},
    ]),
    station(36,'punon','普嫩','Punon','פּוּנֹן',35.50,30.62,'approximate','民33:42',[]),
    station(37,'oboth','阿伯','Oboth','אֹבֹת',35.55,30.74,'unknown','民33:43',[]),
    station(38,'iye-abarim','以耶亚巴琳','Iye-abarim','עִיֵּי הָעֲבָרִים',35.55,30.96,'approximate','民33:44',[]),
    station(39,'dibon-gad','底本迦得','Dibon-gad','דִּיבֹן גָּד',35.78,31.50,'identified','民33:45',[]),
    station(40,'almon-diblathaim','亚门低比拉太音','Almon-diblathaim','עַלְמֹן דִּבְלָתָיְמָה',35.80,31.55,'unknown','民33:46',[]),
    station(41,'abarim','亚巴琳山（尼波前）','Mountains of Abarim','הָרֵי הָעֲבָרִים',35.73,31.77,'approximate','民33:47',[
      {title:'摩西遥望应许之地', ref:'申34:1-4', summary:'摩西上尼波山的毗斯迦山顶，耶和华把全地指给他看：这就是我向亚伯拉罕、以撒、雅各起誓应许之地。'},
    ]),
    station(42,'moab-plains','摩押平原（什亭）','Plains of Moab','עַרְבֹת מוֹאָב',35.62,31.83,'approximate','民33:48-49',[
      {title:'巴兰的预言', ref:'民23-24', summary:'摩押王巴勒雇巴兰咒诅以色列，巴兰却被神感动连连祝福，预言"有星要出于雅各"。'},
      {title:'摩西临终讲论与逝世', ref:'申命记; 申34:5', summary:'摩西在此向新一代宣讲申命记的训诲，随后在尼波山逝世，约书亚接续带领进入迦南。'},
    ]),
  ],
}

// 路线：按 order 连接各站点形成漂流路径（[lng,lat] 序列）
export const exodusRoute = {
  type: 'Feature',
  geometry: {
    type: 'LineString',
    coordinates: exodusStations.features
      .slice()
      .sort((a, b) => a.properties.order - b.properties.order)
      .map(f => f.geometry.coordinates),
  },
  properties: { name_zh: '以色列人的路线', name_en: "Israel's Route", hypothesis: 'traditional-south' },
}

export const confidenceMeta = {
  identified:  { label: '考古较确定', color: '#4ade80' },
  approximate: { label: '传统推定',   color: '#fbbf24' },
  unknown:     { label: '地点失考',   color: '#94a3b8' },
}

// 路线假说变体（供地图选择器使用）
export const routeHypotheses = [
  {
    id: 'traditional-south',
    label: '传统南方西奈路线',
    short: '南方路线',
    color: '#f59e0b',
    description: '经苦海→西奈半岛南端（传统说法，公元前1446年或1260年），民数记33章站点依此假说排列。',
    route: exodusStations.features
      .slice()
      .sort((a, b) => a.properties.order - b.properties.order)
      .map(f => f.geometry.coordinates),
  },
  {
    id: 'northern',
    label: '北方海滨路线',
    short: '北方路线',
    color: '#6366f1',
    description: '经腓力士地海滨大道向北进迦南（神明确拒绝此路线，出13:17），学术上仍存争议。',
    route: exodusStations.features
      .slice()
      .sort((a, b) => a.properties.order - b.properties.order)
      .map(f => f.geometry.coordinates),
  },
]
