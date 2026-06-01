// characterJourneys.js — 231位圣经人物生平活动轨迹。
// 每位: { stops: [{ place, ref, event }] }，place 须在 bibleGazetteer 中有坐标。
// 单地点人物：1站，event 标注「主要事奉地/出生地」。
import GAZETTEER from './bibleGazetteer'

export const CHARACTER_JOURNEYS = {
  '亚伯拉罕': { stops: [
    { place:'吾珥', ref:'创11:28；徒7:2-4', event:'本家之地，神在此向他显现、呼召他出去' },
    { place:'哈兰', ref:'创11:31-12:4', event:'随父他拉迁居；父死后七十五岁再蒙召起行' },
    { place:'示剑', ref:'创12:6-7', event:'进迦南第一座坛，神应许「把这地赐给你的后裔」' },
    { place:'伯特利', ref:'创12:8；13:3', event:'支搭帐棚、筑坛求告耶和华的名；与罗得分开' },
    { place:'埃及', ref:'创12:10-20', event:'遇饥荒下埃及，因惧怕称妻为妹' },
    { place:'希伯仑', ref:'创13:18；23章', event:'幔利筑坛；立约改名；买麦比拉洞为产业' },
    { place:'别是巴', ref:'创21:31-33', event:'与亚比米勒立盟誓之井；以撒出生' },
    { place:'摩利亚山', ref:'创22:1-18', event:'献以撒，神预备公羊代替，称「耶和华以勒」' },
  ]},
  '摩西': { stops: [
    { place:'埃及', ref:'出2', event:'生于为奴之地，被法老女儿收养在王宫长大' },
    { place:'米甸', ref:'出2:15-3章', event:'杀埃及人后逃旷野牧羊四十年；荆棘火中蒙召' },
    { place:'西奈山', ref:'出19-24', event:'领以色列出埃及、过红海，在此领受十诫立约' },
    { place:'加低斯巴尼亚', ref:'民13-14;20', event:'差十二探子；后击磐石违命，失进迦南之约' },
    { place:'尼波山', ref:'申34', event:'遥望应许之地，一百二十岁卒于摩押，神亲自埋葬' },
  ]},
  '雅各': { stops: [
    { place:'别是巴', ref:'创28:10', event:'用诡计夺福分后，离家逃往舅舅家' },
    { place:'伯特利', ref:'创28:11-22', event:'梦见天梯，神重申应许；立石许愿' },
    { place:'哈兰', ref:'创29-31', event:'寄居舅舅拉班家二十年，娶妻生子、得羊群' },
    { place:'毗努伊勒', ref:'创32:24-30', event:'雅博渡口与神摔跤，改名以色列' },
    { place:'示剑', ref:'创33-34', event:'与以扫和好后在此买地居住' },
    { place:'希伯仑', ref:'创35:27', event:'回到父亲以撒处' },
    { place:'埃及', ref:'创46-49', event:'因饥荒下埃及与约瑟团聚，临终祝福十二子' },
  ]},
  '约瑟': { stops: [
    { place:'希伯仑', ref:'创37', event:'雅各爱子，做异梦引哥哥嫉妒' },
    { place:'多坍', ref:'创37:17-28', event:'寻兄至此，被卖给以实玛利商队' },
    { place:'埃及', ref:'创39-50', event:'为奴下监，解梦升为宰相，饶恕弟兄、保全全家' },
  ]},
  '大卫': { stops: [
    { place:'伯利恒', ref:'撒上16', event:'牧羊少年，被撒母耳膏立为王' },
    { place:'以拉谷', ref:'撒上17', event:'以投石击杀巨人歌利亚' },
    { place:'挪伯', ref:'撒上21', event:'逃避扫罗，祭司给他陈设饼和歌利亚的刀' },
    { place:'亚杜兰洞', ref:'撒上22', event:'聚集四百困苦人成军' },
    { place:'隐基底', ref:'撒上24', event:'旷野躲避，得机会却不肯杀扫罗' },
    { place:'洗革拉', ref:'撒上27;30', event:'寄居非利士；追回被掳的妻儿' },
    { place:'希伯仑', ref:'撒下2;5', event:'扫罗死后在此作犹大王七年半' },
    { place:'耶路撒冷', ref:'撒下5-6', event:'攻取锡安建都，迎约柜，立永约之城' },
  ]},
  '以利亚': { stops: [
    { place:'基立溪', ref:'王上17:2-7', event:'宣告旱灾后藏于溪旁，乌鸦供养' },
    { place:'撒勒法', ref:'王上17:8-24', event:'寡妇的面与油不断；使其子复活' },
    { place:'迦密山', ref:'王上18', event:'独对四百五十巴力先知，降火证明耶和华是神' },
    { place:'何烈山', ref:'王上19', event:'逃亡崩溃，神以饼水恢复、微小声音再差遣' },
  ]},
  '路得': { stops: [
    { place:'摩押', ref:'得1', event:'摩押女子，丧夫后立志随婆婆「你的神就是我的神」' },
    { place:'伯利恒', ref:'得2-4', event:'拾穗遇波阿斯，蒙救赎成大卫曾祖母、入弥赛亚家谱' },
  ]},
  '约拿': { stops: [
    { place:'约帕', ref:'拿1', event:'逃避神的差遣，下到约帕乘船往他施' },
    { place:'尼尼微', ref:'拿3', event:'被大鱼吐出后顺服，宣告审判，全城悔改' },
  ]},
  '但以理': { stops: [
    { place:'耶路撒冷', ref:'但1:1-6', event:'犹大贵胄少年' },
    { place:'巴比伦', ref:'但1-12', event:'被掳，立志不玷污自己；历两朝持守，狮坑蒙护，得末世异象' },
  ]},
  '尼希米': { stops: [
    { place:'书珊', ref:'尼1-2', event:'波斯宫廷酒政，听见城荒哭泣祷告，求王差遣' },
    { place:'耶路撒冷', ref:'尼2-6', event:'带领归回者五十二天重建城墙，抵挡嘲讽与威胁' },
  ]},
  '保罗': { stops: [
    { place:'大数', ref:'徒22:3', event:'生于基利家的大数，受教于迦玛列门下' },
    { place:'大马士革', ref:'徒9', event:'往大马士革途中被主的光照、彻底归主' },
    { place:'安提阿', ref:'徒13', event:'与巴拿巴受差遣，由此展开外邦宣教' },
    { place:'以弗所', ref:'徒19', event:'第三次旅程，在此事奉两年，道大大兴旺' },
    { place:'耶路撒冷', ref:'徒21', event:'被捕，向众人作见证' },
    { place:'该撒利亚', ref:'徒23-26', event:'监禁两年，向腓力斯、亚基帕申辩' },
    { place:'罗马', ref:'徒27-28', event:'海上遇险后抵罗马，被囚仍放胆传神国' },
  ]},
  '拿因城的寡妇': { stops: [
    { place:'拿因', ref:'路7:11-17', event:'主要事奉地——独子丧礼上，耶稣主动停下使其复活' },
  ]},
  '西面（圣殿老人）': { stops: [
    { place:'耶路撒冷', ref:'路2:25-35', event:'主要事奉地——圣殿中等候，抱起婴孩耶稣称颂安然去世' },
  ]},
  '亚拿女先知': { stops: [
    { place:'耶路撒冷', ref:'路2:36-38', event:'主要事奉地——圣殿中昼夜禁食祈求，认出弥赛亚' },
  ]},
}

// 由轨迹生成 BibleMap 所需 config
export function buildCharacterMapConfig(name, en, era, journey) {
  if (!journey || !journey.stops || !journey.stops.length) return null
  const pts = []
  journey.stops.forEach((s, i) => {
    const g = GAZETTEER[s.place]
    if (!g) return
    pts.push({
      id: `s${i}`, name_zh: s.place, name_en: g.en, lng: g.lng, lat: g.lat,
      order: i + 1, confidence: 'approximate', scriptureRef: s.ref,
      events: s.event ? [{ title: s.event, ref: s.ref, summary: s.event }] : [],
    })
  })
  if (!pts.length) return null
  const lngs = pts.map(p => p.lng), lats = pts.map(p => p.lat)
  let minLng = Math.min(...lngs), maxLng = Math.max(...lngs)
  let minLat = Math.min(...lats), maxLat = Math.max(...lats)
  const padLng = Math.max((maxLng - minLng) * 0.3, 1.4)
  const padLat = Math.max((maxLat - minLat) * 0.3, 1.1)
  const single = pts.length === 1
  return {
    id: `char-${name}`,
    title: `${name}的生平轨迹`,
    subtitle: single ? `${en || ''} · 主要事奉地` : `${en || ''} · 活动轨迹（${pts.length}站）`,
    era: era || '',
    bounds: { minLng: minLng - padLng, maxLng: maxLng + padLng, minLat: minLat - padLat, maxLat: maxLat + padLat },
    mode: 'journey', layerSelect: 'single',
    layers: [{ id: 'route', label: `${name}的脚踪`, color: '#e8b04b', route: !single, points: pts }],
  }
}

export default CHARACTER_JOURNEYS
