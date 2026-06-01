"""
pilgrim_engine.py — 第六大陆 · 天路客 / Pilgrim Journey（本仁《天路历程》游戏化）

根据用户近期的属灵状态，判断他此刻「身处天路历程的哪一处」，给出本仁式的处境描述、
属灵含义、危险、出路与经文，并引导到相应功能。纯函数。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# 天路历程沿途地点（大致按旅程顺序；order 用于地图进度）
PLACES: List[Dict[str, Any]] = [
    {"key": "slough", "name": "灰心沼泽", "en": "Slough of Despond", "icon": "🌫️", "color": "#748ffc", "order": 1,
     "meaning": "重担压身、灰心下沉之地。罪与忧虑像泥沼，越挣扎越往下陷。",
     "danger": "在灰心里越陷越深，忘了有人会拉你上来。",
     "way": "不要靠自己挣扎；伸手抓住「应许」的踏脚石，呼求帮助。",
     "scripture": {"ref": "诗40:2", "text": "他从祸坑里、从淤泥中把我拉上来，使我的脚立在磐石上。"},
     "cta": {"label": "做个属灵低潮体检", "target": "checkup"}},
    {"key": "wicket", "name": "窄门", "en": "Wicket Gate", "icon": "🚪", "color": "#ffd43b", "order": 2,
     "meaning": "一切的起点：回到福音，进窄门。基督就是那门。",
     "danger": "在门外徘徊，靠自己的努力想进去。",
     "way": "只管敲门，那门必为你开——救恩是恩典，不是功劳。",
     "scripture": {"ref": "约10:9", "text": "我就是门；凡从我进来的，必然得救。"},
     "cta": {"label": "进福音诊断室", "target": "gospel"}},
    {"key": "difficulty", "name": "艰难山", "en": "Hill Difficulty", "icon": "⛰️", "color": "#ffa94d", "order": 3,
     "meaning": "上坡费力之处。神的呼召常要你迎难而上，而非绕道。",
     "danger": "因怕付代价而走平坦的旁路，结果迷失。",
     "way": "一步一步往上爬；困难是被塑造的地方，不是被困的地方。",
     "scripture": {"ref": "赛40:31", "text": "那等候耶和华的必从新得力……行走却不疲乏。"},
     "cta": {"label": "立一个忠心的小约", "target": "hub"}},
    {"key": "palace", "name": "美宫", "en": "Palace Beautiful", "icon": "🏰", "color": "#34c759", "order": 4,
     "meaning": "蒙神款待、与圣徒相交、得着装备的安息之地。",
     "danger": "把安息当享受而停步不前。",
     "way": "在与神、与肢体的相交中得力，然后继续上路。",
     "scripture": {"ref": "诗84:10", "text": "在你的院宇住一日，胜似在别处住千日。"},
     "cta": {"label": "去灵修操练相交", "target": "hub"}},
    {"key": "humiliation", "name": "谦卑谷", "en": "Valley of Humiliation", "icon": "🗡️", "color": "#da77f2", "order": 5,
     "meaning": "与亚玻伦（试探者）正面争战之地。低处往往是属灵争战最烈处。",
     "danger": "以为靠自己能赢，或因羞愧而放下兵器。",
     "way": "穿戴全副军装，用「信心的盾牌」与「圣灵的宝剑」抵挡。",
     "scripture": {"ref": "雅4:7", "text": "故此，你们要顺服神。务要抵挡魔鬼，魔鬼就必离开你们逃跑了。"},
     "cta": {"label": "省察内心的偶像", "target": "idolatry"}},
    {"key": "shadow", "name": "死荫幽谷", "en": "Valley of the Shadow of Death", "icon": "🌑", "color": "#5c5f66", "order": 6,
     "meaning": "黑暗、恐惧、看不见路的幽谷。信心在此凭应许而非凭眼见行走。",
     "danger": "被恐惧吞没，误把仇敌的低语当作自己的声音。",
     "way": "继续往前，哪怕只凭一句经文的微光；祂的杖与竿都安慰你。",
     "scripture": {"ref": "诗23:4", "text": "我虽然行过死荫的幽谷，也不怕遭害，因为你与我同在。"},
     "cta": {"label": "用福音对付恐惧", "target": "gospel"}},
    {"key": "vanity", "name": "虚荣集市", "en": "Vanity Fair", "icon": "🎪", "color": "#ff8787", "order": 7,
     "meaning": "贩卖名利、地位、认可、享乐的世界市集。一切都标着价、诱你购买。",
     "danger": "被比较、认可、消费牵着走，把心卖给了世界。",
     "way": "不被集市定价。你的价值已在十字架上被定准——无价。",
     "scripture": {"ref": "约一2:15", "text": "不要爱世界和世界上的事。"},
     "cta": {"label": "查一查主导偶像", "target": "idolatry"}},
    {"key": "bypath", "name": "旁路草地", "en": "Bypath Meadow", "icon": "🌿", "color": "#94d82d", "order": 8,
     "meaning": "看似轻松好走的捷径，实则偏离正路，通向被囚之地。",
     "danger": "为了舒适和省力，避开神所定的窄路。",
     "way": "回到正路。真正的安息在顺服里，不在逃避里。",
     "scripture": {"ref": "箴14:12", "text": "有一条路，人以为正，至终成为死亡之路。"},
     "cta": {"label": "等候中的分辨", "target": "waiting"}},
    {"key": "castle", "name": "绝望城堡", "en": "Doubting Castle", "icon": "🏚️", "color": "#9775fa", "order": 9,
     "meaning": "被巨人「绝望」囚禁的地牢。怀疑神的爱与自己的得救。",
     "danger": "忘了你口袋里一直有一把叫「应许」的钥匙。",
     "way": "取出应许的钥匙——神的话能开任何一扇绝望的门。向自己传讲福音。",
     "scripture": {"ref": "罗8:38-39", "text": "是死，是生……都不能叫我们与神的爱隔绝。"},
     "cta": {"label": "向自己传讲福音", "target": "checkup"}},
    {"key": "delectable", "name": "乐山", "en": "Delectable Mountains", "icon": "🏔️", "color": "#51cf66", "order": 10,
     "meaning": "牧人引领、可以远望天城的高处。喜乐、确据与盼望在此重燃。",
     "danger": "贪恋此处风光而忘了路还没走完。",
     "way": "在高处饱览应许，得着力量，再带着盼望继续前行。",
     "scripture": {"ref": "来12:1-2", "text": "存心忍耐，奔那摆在我们前头的路程，仰望……耶稣。"},
     "cta": {"label": "数算今天的恩典", "target": "hub"}},
    {"key": "celestial", "name": "天城在望", "en": "Celestial City in View", "icon": "🌟", "color": "#ffd43b", "order": 11,
     "meaning": "已能望见天城的金光。一切劳苦将要变为永恒的喜乐。",
     "danger": "在终点前松懈，或被最后的试炼绊倒。",
     "way": "举目定睛，向着标竿直跑——祂必亲自迎接你进城。",
     "scripture": {"ref": "腓3:14", "text": "向着标竿直跑，要得神在基督耶稣里从上面召我来得的奖赏。"},
     "cta": {"label": "看见你的成长地图", "target": "planet"}},
]
PLACE_INDEX = {p["key"]: p for p in PLACES}


def locate(signals: Optional[Dict[str, Any]]) -> str:
    """据近期状态定位当前所在地点 key。signals 可含 emotion/idol/low_index/positive。"""
    s = signals or {}
    emo = s.get("emotion") or ""
    idol = s.get("idol") or ""
    low = float(s.get("low_index", 0) or 0)
    positive = bool(s.get("positive"))

    if low >= 0.6:
        # 区分：失确据/怀疑 → 绝望城堡；否则灰心沼泽
        return "castle" if s.get("doubt") else "slough"
    if emo in ("恐惧",) or s.get("fear"):
        return "shadow"
    if idol in ("approval", "success"):
        return "vanity"
    if idol == "comfort":
        return "bypath"
    if idol in ("control", "security"):
        return "difficulty"
    if idol == "relationship":
        return "humiliation"
    if emo in ("悲伤",) or low >= 0.4:
        return "slough"
    if positive or emo in ("喜乐", "感恩", "平静", "盼望"):
        return "delectable"
    return "difficulty"  # 旅途常态：在路上、迎难而上


def place(key: str) -> Dict[str, Any]:
    return PLACE_INDEX.get(key, PLACE_INDEX["difficulty"])


def meta() -> Dict[str, Any]:
    return {"places": PLACES}
