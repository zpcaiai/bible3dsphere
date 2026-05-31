// 保罗宣教旅程 —— 使徒行传记载的三次宣教旅行 + 押往罗马的航程。
// 城市坐标 [lng, lat]；事件附在事件发生地的城市上（跨旅程通用）。
// confidence 多为 identified（考古较确定的古城）。

const C = (id, name_zh, name_en, lng, lat, confidence, events) => ({
  id, name_zh, name_en, lng, lat, confidence: confidence || 'identified', events: events || [],
})

// 城市库
export const paulCities = [
  C('antioch-syria','安提阿（叙利亚）','Antioch (Syria)',36.16,36.20,'identified',[
    {title:'宣教事工的母会', ref:'徒13:1-3', summary:'安提阿教会禁食祷告，圣灵差派巴拿巴和扫罗（保罗）出去传道，三次旅程皆由此出发。'},
  ]),
  C('seleucia','西流基','Seleucia',35.93,36.12,'identified',[]),
  C('salamis','撒拉米','Salamis',33.90,35.18,'identified',[
    {title:'在居比路（塞浦路斯）传道', ref:'徒13:5', summary:'到了撒拉米，就在犹太人的会堂里传讲神的道。'},
  ]),
  C('paphos','帕弗','Paphos',32.41,34.77,'identified',[
    {title:'行法术的以吕马受罚', ref:'徒13:6-12', summary:'保罗斥责术士以吕马，他即刻瞎眼；方伯士求·保罗见此希奇，就信了主。'},
  ]),
  C('perga','别加','Perga',30.85,36.96,'identified',[
    {title:'约翰马可离队', ref:'徒13:13', summary:'到了旁非利亚的别加，约翰马可离开他们回耶路撒冷去了。'},
  ]),
  C('attalia','亚大利','Attalia',30.70,36.88,'identified',[]),
  C('pisidian-antioch','彼西底的安提阿','Pisidian Antioch',31.19,38.30,'identified',[
    {title:'会堂讲道，转向外邦', ref:'徒13:16-48', summary:'保罗在会堂讲述救恩历史；犹太人嫉妒抵挡，保罗宣告转向外邦人，外邦人欢喜领受。'},
  ]),
  C('iconium','以哥念','Iconium',32.49,37.87,'identified',[
    {title:'险被石头打', ref:'徒14:1-6', summary:'许多人信主，但城里分党，有人要凌辱用石头打他们，二人就逃往路司得、特庇。'},
  ]),
  C('lystra','路司得','Lystra',32.45,37.58,'approximate',[
    {title:'医好生来瘸腿的人', ref:'徒14:8-18', summary:'保罗医好瘸腿者，众人以为是神（宙斯、希耳米）下凡，要献祭，二人极力拦阻。'},
    {title:'保罗被石头打', ref:'徒14:19-20', summary:'有犹太人挑唆众人用石头打保罗，以为他死了拖到城外；门徒围着他，他起来又进城。'},
  ]),
  C('derbe','特庇','Derbe',33.30,37.35,'approximate',[]),
  C('troas','特罗亚','Troas',26.16,39.75,'identified',[
    {title:'马其顿的异象', ref:'徒16:9-10', summary:'夜间保罗见异象：一个马其顿人求他过去帮助；福音由此首次踏入欧洲。'},
    {title:'犹推古从窗台坠落复生', ref:'徒20:7-12', summary:'保罗讲道到半夜，少年犹推古困倦从三楼坠下，保罗下去抱住他，他活了。'},
  ]),
  C('samothrace','撒摩特喇','Samothrace',25.53,40.46,'identified',[]),
  C('neapolis','尼亚波利','Neapolis',24.41,40.94,'identified',[]),
  C('philippi','腓立比','Philippi',24.29,41.01,'identified',[
    {title:'吕底亚归主', ref:'徒16:13-15', summary:'卖紫色布的妇人吕底亚听道，主开她的心，她和全家受洗，欧洲首位信徒。'},
    {title:'下监与狱卒全家信主', ref:'徒16:25-34', summary:'保罗西拉在狱中唱诗祷告，地大震动监门全开；狱卒要自尽被拦，问当怎样行才可得救，当夜全家受洗。'},
  ]),
  C('amphipolis','暗妃波里','Amphipolis',23.83,40.82,'identified',[]),
  C('apollonia','亚波罗尼亚','Apollonia',23.45,40.78,'identified',[]),
  C('thessalonica','帖撒罗尼迦','Thessalonica',22.94,40.64,'identified',[
    {title:'三个安息日辩道', ref:'徒17:1-9', summary:'保罗一连三个安息日在会堂讲论；信的人不少，不信的犹太人聚众生乱。'},
  ]),
  C('berea','庇哩亚','Berea',22.20,40.52,'identified',[
    {title:'甘心领受、天天考查圣经', ref:'徒17:10-12', summary:'庇哩亚人比帖撒罗尼迦人开明，甘心领受这道，天天考查圣经，要晓得是否如此。'},
  ]),
  C('athens','雅典','Athens',23.73,37.98,'identified',[
    {title:'亚略巴古讲"未识之神"', ref:'徒17:22-31', summary:'保罗站在亚略巴古，借坛上"未识之神"传讲创造主与复活的福音。', image:'https://commons.wikimedia.org/wiki/Special:FilePath/V%26A_-_Raphael%2C_St_Paul_Preaching_in_Athens_(1515).jpg?width=640'},
  ]),
  C('corinth','哥林多','Corinth',22.93,37.94,'identified',[
    {title:'住一年半，与百基拉亚居拉同工', ref:'徒18:1-11', summary:'保罗与织帐棚的亚居拉、百基拉同住做工，在此住了一年六个月教导神的道。'},
  ]),
  C('cenchreae','坚革哩','Cenchreae',22.99,37.89,'identified',[]),
  C('ephesus','以弗所','Ephesus',27.34,37.94,'identified',[
    {title:'两年之久，主道兴旺', ref:'徒19:8-10', summary:'保罗在推喇奴学房天天辩论，达两年，全亚细亚的人都听见主的道。'},
    {title:'银匠为亚底米起哄乱', ref:'徒19:23-41', summary:'银匠底米丢因偶像生意受损，煽动全城高喊"大哉以弗所人的亚底米"，满城混乱。'},
  ]),
  C('miletus','米利都','Miletus',27.28,37.53,'identified',[
    {title:'向以弗所长老告别', ref:'徒20:17-38', summary:'保罗召以弗所长老来米利都，托付他们牧养神的教会，众人痛哭与他送别。'},
  ]),
  C('tyre','推罗','Tyre',35.20,33.27,'identified',[]),
  C('caesarea','凯撒利亚','Caesarea Maritima',34.89,32.50,'identified',[
    {title:'押往罗马的起点', ref:'徒27:1', summary:'保罗与别的囚犯交给百夫长犹流，从这里上船往意大利去。'},
  ]),
  C('jerusalem','耶路撒冷','Jerusalem',35.23,31.78,'identified',[
    {title:'旅程的终点与被捕', ref:'徒21:17-33', summary:'保罗回到耶路撒冷，在圣殿被犹太人围攻，被罗马千夫长拘押，开启赴罗马受审之路。'},
  ]),
  C('sidon','西顿','Sidon',35.37,33.56,'identified',[]),
  C('myra','每拉','Myra',29.98,36.26,'identified',[]),
  C('fair-havens','佳澳（革哩底）','Fair Havens',24.80,34.90,'approximate',[
    {title:'保罗预警航行危险', ref:'徒27:9-12', summary:'保罗劝阻继续航行，但百夫长信从船主，多数人主张开船离开佳澳。'},
  ]),
  C('malta','米利大（马耳他）','Malta',14.45,35.90,'identified',[
    {title:'海难得救、毒蛇无害', ref:'徒28:1-6', summary:'船破众人游泳上岸到米利大岛；毒蛇咬保罗的手而他毫无所害，土人以为他是神。'},
  ]),
  C('syracuse','叙拉古','Syracuse',15.29,37.07,'identified',[]),
  C('rhegium','利基翁','Rhegium',15.65,38.11,'identified',[]),
  C('puteoli','部丢利','Puteoli',14.12,40.82,'identified',[]),
  C('rome','罗马','Rome',12.50,41.89,'identified',[
    {title:'在罗马放胆传道', ref:'徒28:30-31', summary:'保罗在自己所租的房子住了两年，放胆传讲神国的道，将主耶稣基督的事教导人，并没有人禁止。'},
  ]),
  C('assos','亚朔','Assos',26.34,39.49,'identified',[]),
  C('mitylene','米推利尼','Mitylene',26.55,39.11,'identified',[]),
]

const order = (ids) => ids // 语义占位，保持可读

// 四段旅程（变体）。stationIds 为该旅程依序经过的城市。
export const paulJourneys = [
  {
    id: 'journey-1', label: '第一次旅程', short: '一次', color: '#fbbf24', startYear: 46, endYear: 48,
    description: '使徒行传13-14章：自叙利亚安提阿出发，经居比路（塞浦路斯）至加拉太南部诸城，再原路返回。',
    stationIds: order(['antioch-syria','seleucia','salamis','paphos','perga','pisidian-antioch','iconium','lystra','derbe','attalia']),
  },
  {
    id: 'journey-2', label: '第二次旅程', short: '二次', color: '#38bdf8', startYear: 49, endYear: 52,
    description: '使徒行传15:36-18:22：福音首次进入欧洲——腓立比、帖撒罗尼迦、雅典、哥林多。',
    stationIds: order(['antioch-syria','derbe','lystra','troas','samothrace','neapolis','philippi','amphipolis','apollonia','thessalonica','berea','athens','corinth','cenchreae','ephesus','caesarea','jerusalem']),
  },
  {
    id: 'journey-3', label: '第三次旅程', short: '三次', color: '#a78bfa', startYear: 53, endYear: 57,
    description: '使徒行传18:23-21:17：长驻以弗所，经马其顿、希腊返回，于米利都向长老告别，终至耶路撒冷被捕。',
    stationIds: order(['antioch-syria','ephesus','troas','philippi','corinth','assos','mitylene','miletus','tyre','caesarea','jerusalem']),
  },
  {
    id: 'voyage-rome', label: '押往罗马', short: '赴罗马', color: '#fb7185', startYear: 59, endYear: 62,
    description: '使徒行传27-28章：自凯撒利亚渡海，遇风暴于米利大（马耳他）海难得救，终抵罗马受审传道。',
    stationIds: order(['caesarea','sidon','myra','fair-havens','malta','syracuse','rhegium','puteoli','rome']),
  },
]
