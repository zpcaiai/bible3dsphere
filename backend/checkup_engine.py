"""
checkup_engine.py — 属灵低潮体检 / Spiritual Checkup（钟马田《属灵低潮》）

钟马田名言：「我们大部分的不快乐，是因为听自己说话，而不是向自己传讲。」
体检 8 个症状(0–10) → 找出主导低潮 → 根源 / 福音欠缺 / 经文 / 操练 / 祷告 +
一句「向自己传讲的福音」。纯函数；AI 走钟马田 Spiritual Checkup 技能 Prompt，失败回退。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

SYMPTOMS: List[Dict[str, str]] = [
    {"key": "joylessness",      "name": "失去喜乐", "hint": "曾经的喜乐淡了，提不起劲。"},
    {"key": "assurance_loss",   "name": "失去确据", "hint": "怀疑自己到底有没有得救、被爱。"},
    {"key": "self_condemnation","name": "自我控告", "hint": "反复责备自己，活在懊悔里。"},
    {"key": "hopelessness",     "name": "失去盼望", "hint": "看不到出路，觉得不会更好了。"},
    {"key": "circumstance",     "name": "只盯环境", "hint": "被处境牵着走，忘了神。"},
    {"key": "dryness",          "name": "属灵枯干", "hint": "读经祷告像例行公事，感受不到神。"},
    {"key": "anxiety",          "name": "焦虑不安", "hint": "心里常常担忧、绷紧。"},
    {"key": "discouragement",   "name": "灰心丧志", "hint": "想放弃，觉得努力没有意义。"},
]
SYMPTOM_INDEX = {s["key"]: s for s in SYMPTOMS}

REMEDY: Dict[str, Dict[str, Any]] = {
    "joylessness": {
        "root": "把喜乐建立在感受或处境上，而非建立在「神是谁、祂为我做了什么」上。",
        "deficit": "忘了救恩本身就是喜乐的源头——你的名字记录在天上。",
        "scripture": {"ref": "诗16:11", "text": "在你面前有满足的喜乐，在你右手中有永远的福乐。"},
        "practice": "数算三件救恩中不变的事实（被赦免、被收纳、有永生），向自己宣告。",
        "prayer": "主啊，求你把救恩的喜乐重新赐给我，叫我的喜乐不再随处境起伏。",
        "preach": "不要听自己的低落，要向自己传讲：我的喜乐不在感觉，在那位永不改变的救主。",
    },
    "assurance_loss": {
        "root": "把得救的确据建立在自己的表现或感觉上，而不是基督成就的事实上。",
        "deficit": "忘了称义是神的宣告，不靠你的好坏，全靠基督的血。",
        "scripture": {"ref": "罗8:38-39", "text": "是死，是生……都不能叫我们与神的爱隔绝。"},
        "practice": "读约一5:11-13，把「神的儿子在你里面、你就有永生」当作事实领受。",
        "prayer": "主啊，我的确据不在我的感觉，而在你的应许。求你坚固我的信心。",
        "preach": "不要凭感觉判断你与神的关系，要凭十字架——那是神爱你的铁证。",
    },
    "self_condemnation": {
        "root": "做了自己的审判官，不肯接受十字架上「赦了」的宣判。",
        "deficit": "忘了在基督里就不定罪了——控告你的不是神，是你自己或仇敌。",
        "scripture": {"ref": "罗8:1", "text": "如今，那些在基督耶稣里的就不定罪了。"},
        "practice": "把一件反复懊悔的事，明确交在十字架前，领受赦免，不再翻旧账。",
        "prayer": "主啊，谢谢你已经赦免我。求你帮助我接受你的赦免，停止控告自己。",
        "preach": "审判已在各各他落槌，宣判是「赦了」——你无权再定一个神已称义的人的罪。",
    },
    "hopelessness": {
        "root": "把盼望建立在事情会变好上，而非建立在神的性情与应许上。",
        "deficit": "忘了基督已经胜过世界，神能使万事互相效力。",
        "scripture": {"ref": "罗15:13", "text": "但愿使人有盼望的神……叫你们……大有盼望。"},
        "practice": "写下一件你正绝望的事，旁边写：「但神仍坐在宝座上。」",
        "prayer": "主啊，我看不到出路，但你是道路。求你把活泼的盼望重新赐给我。",
        "preach": "盼望不是「事情会变好」，是「神必不撇下我」——这盼望不叫人羞愧。",
    },
    "circumstance": {
        "root": "眼目离开了神，被环境的浪涛吞没（像彼得看风浪就下沉）。",
        "deficit": "忘了那位踏浪而来、向你伸手的主，比风浪更大。",
        "scripture": {"ref": "诗121:1-2", "text": "我要向山举目，我的帮助从造天地的耶和华而来。"},
        "practice": "刻意把目光从问题移开 3 分钟，单单默想神的一个属性（如：祂掌权）。",
        "prayer": "主啊，我一直盯着风浪。求你叫我举目看你，在惊涛中仍然安稳。",
        "preach": "把眼目从环境移到基督身上——他若与我同在，风浪又算什么？",
    },
    "dryness": {
        "root": "把与神的关系活成了例行公事，靠感觉而非靠信心亲近祂。",
        "deficit": "忘了即使在枯干中，神的应许与同在依然真实，不随感受改变。",
        "scripture": {"ref": "诗42:1-2", "text": "我的心切慕你，如鹿切慕溪水。"},
        "practice": "今天不求感受，只凭信心来到神面前安静 5 分钟，承认「我渴慕你」。",
        "prayer": "主啊，我心干渴。求你这活水的泉源，再一次润泽我枯干的灵。",
        "preach": "枯干不等于被弃。凭信心继续来，因为应许不靠感觉成立。",
    },
    "anxiety": {
        "root": "想替神掌管未来，把安全感放在掌控上，而非放在祂的看顾上。",
        "deficit": "忘了天父顾念你，连麻雀都看顾，何况是你。",
        "scripture": {"ref": "彼前5:7", "text": "你们要将一切的忧虑卸给神，因为他顾念你们。"},
        "practice": "把最挂虑的一件事写下，一句话交托：「这件事我交给你。」",
        "prayer": "主啊，我把忧虑卸给你，因为你顾念我。求你以出人意外的平安守护我。",
        "preach": "不要在忧虑里反刍，要把它卸给那位彻夜看顾、从不打盹的神。",
    },
    "discouragement": {
        "root": "用结果衡量价值，忘了忠心比成功更蒙神看重。",
        "deficit": "忘了神看重的是过程中的忠心，且必亲自成全祂在你身上开始的工。",
        "scripture": {"ref": "加6:9", "text": "我们行善，不可丧志；若不灰心，到了时候就要收成。"},
        "practice": "在你想放弃的事上，今天只忠心地再走一小步，把收成交给神。",
        "prayer": "主啊，我有些灰心。求你叫我从新得力，在忠心中等候你的时候。",
        "preach": "不要因看不见成果就丧志——开始这工的神，必亲自完成。",
    },
}


def _n(v):
    try:
        return max(0.0, min(10.0, float(v)))
    except Exception:
        return 0.0


def assess(ratings: Dict[str, Any]) -> Dict[str, Any]:
    scores = {s["key"]: _n(ratings.get(s["key"])) for s in SYMPTOMS}
    vals = list(scores.values())
    index = round(sum(vals) / len(vals) / 10.0, 3) if vals else 0.0   # 0–1 低潮指数
    ranked = sorted(SYMPTOMS, key=lambda s: scores[s["key"]], reverse=True)
    top = [s for s in ranked if scores[s["key"]] >= 4][:2]

    if index < 0.25 or not top:
        return {
            "index": index, "level": "稳健",
            "summary": "目前你的灵里相对稳健。继续以信心而非感觉亲近神——风平浪静时打的桩，"
                       "会在风暴里站立得住。",
            "items": [], "preach": "无论高低，都向自己传讲福音，而不是听凭情绪做主。",
            "scripture": {"ref": "诗103:1", "text": "我的心哪，你要称颂耶和华！"},
            "source": "deterministic",
        }

    level = "高" if index >= 0.6 else "中" if index >= 0.4 else "轻"
    items = []
    for s in top:
        r = REMEDY[s["key"]]
        items.append({"name": s["name"], "root": r["root"], "deficit": r["deficit"],
                      "scripture": r["scripture"], "practice": r["practice"],
                      "prayer": r["prayer"], "preach": r["preach"]})
    lead = top[0]
    summary = (f"体检显示你正经历「{lead['name']}」为主的属灵低潮（低潮指数 {int(index*100)}）。"
               f"钟马田会温柔而坚定地提醒你：这多半不是因为你不属灵，而是因为你在「听自己」"
               f"——听那些低落、控告、绝望的声音。现在，轮到你向自己传讲福音了。")
    return {"index": index, "level": level, "summary": summary, "items": items,
            "preach": items[0]["preach"], "scripture": items[0]["scripture"],
            "source": "deterministic"}


def formation_signal(result: Dict[str, Any]):
    """做体检=诚实面对低潮+寻求福音=反思成长；低潮高则轻推 fear。"""
    idx = result.get("index", 0)
    if idx >= 0.5:
        return (["fear", "growth"], False, True, round(3 + idx * 6, 1))
    return (["growth"], True, True, 4.0)


# ── AI（钟马田 Spiritual Checkup 技能）────────────────────────────────────────
def build_prompt(ratings: Dict[str, Any]) -> List[Dict[str, str]]:
    lines = "\n".join(f"- {s['name']}: {int(_n(ratings.get(s['key'])))}/10" for s in SYMPTOMS)
    system = (
        "你是一位属灵医生，按照马丁·钟马田《属灵低潮》(Spiritual Depression)的方法工作。"
        "核心：人的不快乐，多因「听自己说话」而非「向自己传讲福音」。对每个突出症状："
        "描述→指出根源→指出所缺的福音真理→推荐一个属灵操练→推荐经文→推荐祷告。"
        "温柔、不定罪、以福音为药。只输出一个 JSON 对象。"
    )
    user = (f"我的属灵低潮自评：\n{lines}\n\n严格按 JSON：\n"
            '{"summary":"温柔的总体诊断","level":"轻|中|高","preach":"一句向自己传讲的福音",'
            '"items":[{"name":"症状","root":"根源","deficit":"所缺福音","scripture":{"ref":"","text":""},'
            '"practice":"操练","prayer":"祷告","preach":"传讲句"}]}')
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def analyze(ratings: Dict[str, Any], settings: Any = None, use_ai: bool = True) -> Dict[str, Any]:
    fallback = assess(ratings)
    if not use_ai or not fallback.get("items"):
        return fallback
    try:
        try:
            from backend.waiting_engine import call_ai_provider
        except Exception:
            from waiting_engine import call_ai_provider
        ai = call_ai_provider(build_prompt(ratings), settings=settings)
    except Exception:
        ai = None
    if not ai or not isinstance(ai.get("items"), list) or not ai["items"]:
        return fallback
    out = dict(fallback)
    out["summary"] = str(ai.get("summary") or fallback["summary"])
    out["preach"] = str(ai.get("preach") or fallback["preach"])
    items = []
    for it in ai["items"][:3]:
        if not isinstance(it, dict):
            continue
        sc = it.get("scripture") if isinstance(it.get("scripture"), dict) else {}
        items.append({"name": str(it.get("name", "")), "root": str(it.get("root", "")),
                      "deficit": str(it.get("deficit", "")),
                      "scripture": {"ref": str(sc.get("ref", "")), "text": str(sc.get("text", ""))},
                      "practice": str(it.get("practice", "")), "prayer": str(it.get("prayer", "")),
                      "preach": str(it.get("preach", ""))})
    if items:
        out["items"] = items
        out["scripture"] = items[0]["scripture"]
    out["source"] = "ai"
    return out


def meta() -> Dict[str, Any]:
    return {"symptoms": SYMPTOMS}
