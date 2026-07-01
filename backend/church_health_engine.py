"""
church_health_engine.py — 健康教会九标志 · Church Health OS 引擎
================================================================

把 9Marks（健康教会九标志）的理念融入属灵星球，形成「教会健康生态层」。
本引擎提供：

  1. NINE_MARKS         —— 九标志字典（中英名 + 经文根基 + 定义）
  2. ScoringService     —— 九标志成长评分算法 v1（改编自方案 §6）
  3. compute_overview() —— 汇总用户各子系统的证据 → 九标志成长概览 + 总分
  4. run_sermon_formation() —— 讲道回应生成 Agent（听道→悔改→相信→顺服→肢体应用）
  5. run_gospel_clarity()   —— 福音清晰度评估 Agent（神-人-基督-回应 四格 + 假福音检测）
  6. SYSTEM_BOUNDARY    —— 所有 Church Health Agent 的统一边界（AI 不定罪/不赦罪/不执行纪律）
  7. SCHEMA_SQL / ensure_tables() —— ch_* 数据表（懒建表）

设计原则（务必遵守）：
  - 九标志评分不是属灵身份审判，只用于「看见成长方向 + 下一步操练 + 门训更具体」。
  - AI 不能替代牧师/长老/小组长/辅导员/医生；不能宣告一个人是否真正重生；
    不能执行教会纪律；不能赦罪。遇危机优先安全与真人求助（crisis-first）。
  - 隐私优先：悔改/恢复记录默认仅本人可见，除非用户明确授权或安全策略触发。

后端栈：FastAPI + psycopg（原生 SQL，%s 占位符，按 email 归属），
LLM 通过 llm_provider.generate_json（未配置真实 provider 时走 Mock，可离线运行）。
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── LLM provider（可选，缺失时全部走确定性回退，接口仍可用）─────────────────────
try:  # pragma: no cover - import shim, mirrors other routers/engines
    from backend import llm_provider as _llm  # type: ignore
except Exception:  # pragma: no cover
    try:
        import llm_provider as _llm  # type: ignore
    except Exception:  # pragma: no cover
        _llm = None  # type: ignore


# ═══════════════════════════════════════════════════════════════════════════
# 1. 九标志字典
# ═══════════════════════════════════════════════════════════════════════════
# code 与评分权重、快照表 mark_code 一一对应。
NINE_MARKS: List[Dict[str, Any]] = [
    {
        "code": "expository_preaching",
        "name_zh": "释经讲道",
        "name_en": "Expository Preaching",
        "sort_order": 1,
        "module": "Sermon Formation Engine",
        "blurb": "抓住一段经文的主旨，以经文主旨作为信息核心，再应用到今天的生活。",
        "biblical_basis": ["提摩太后书 4:2", "尼希米记 8:1-8", "使徒行传 2:42"],
    },
    {
        "code": "biblical_theology",
        "name_zh": "合乎圣经的神学",
        "name_en": "Biblical Theology",
        "sort_order": 2,
        "module": "Biblical Theology Graph",
        "blurb": "以整本圣经的救赎历史与基督中心，塑造合乎圣经的神观、人观、福音观。",
        "biblical_basis": ["路加福音 24:27", "提摩太后书 1:13", "使徒行传 20:27"],
    },
    {
        "code": "gospel_clarity",
        "name_zh": "对福音的合乎圣经的理解",
        "name_en": "The Gospel",
        "sort_order": 3,
        "module": "Gospel Clarity Engine",
        "blurb": "圣洁的神、犯罪的人、受死复活的基督、悔改与信靠的回应——防止福音被道德主义/成功神学/心理化。",
        "biblical_basis": ["哥林多前书 15:1-4", "罗马书 3:23-26", "以弗所书 2:8-9"],
    },
    {
        "code": "conversion",
        "name_zh": "合乎圣经的对归信的理解",
        "name_en": "Conversion",
        "sort_order": 4,
        "module": "Conversion & Repentance Discernment",
        "blurb": "真实的悔改与信心、可见的悔改果子；不把洗礼当作得救条件，也不落入廉价恩典。",
        "biblical_basis": ["马可福音 1:15", "约翰福音 3:3-8", "使徒行传 26:20"],
    },
    {
        "code": "evangelism",
        "name_zh": "合乎圣经的对福音布道的理解",
        "name_en": "Evangelism",
        "sort_order": 5,
        "module": "Evangelism Practice System",
        "blurb": "把传福音变成日常操练：代祷名单、个人见证、福音对话、慕道友陪伴与复盘。",
        "biblical_basis": ["马太福音 28:19-20", "罗马书 10:14-17", "使徒行传 8:4"],
    },
    {
        "code": "membership",
        "name_zh": "合乎圣经的对教会成员的理解",
        "name_en": "Church Membership",
        "sort_order": 6,
        "module": "Local Church Membership OS",
        "blurb": "从「属灵消费者」回到对本地教会的委身：敬拜节律、肢体关系、服事与成员约。",
        "biblical_basis": ["哥林多前书 12:12-27", "希伯来书 10:24-25", "使徒行传 2:42-47"],
    },
    {
        "code": "discipline",
        "name_zh": "合乎圣经的教会纪律",
        "name_en": "Church Discipline",
        "sort_order": 7,
        "module": "Restoration & Accountability Flow",
        "blurb": "帮助成员追求圣洁、与罪争战的恢复性牧养流程——AI 只识别风险/助自省/建议求助，绝不执行纪律。",
        "biblical_basis": ["马太福音 18:15-17", "加拉太书 6:1", "雅各书 5:19-20"],
    },
    {
        "code": "discipleship",
        "name_zh": "促进门徒造就与成长",
        "name_en": "Discipleship & Growth",
        "sort_order": 8,
        "module": "Discipleship Growth Engine",
        "blurb": "把门训从课程变成生命共同体：一对一门训、彼此效法、恩赐与服事、信望爱成长。",
        "biblical_basis": ["马太福音 28:19", "以弗所书 4:11-16", "提摩太后书 2:2"],
    },
    {
        "code": "leadership",
        "name_zh": "合乎圣经的教会带领",
        "name_en": "Church Leadership",
        "sort_order": 9,
        "module": "Care Dashboard for Elders/Leaders",
        "blurb": "长老/牧者/小组长以神的话语牧养群体：关怀提醒、群体健康趋势、危机分流。",
        "biblical_basis": ["彼得前书 5:1-4", "提摩太前书 3:1-7", "使徒行传 20:28"],
    },
]

MARK_BY_CODE: Dict[str, Dict[str, Any]] = {m["code"]: m for m in NINE_MARKS}
MARK_CODES: List[str] = [m["code"] for m in NINE_MARKS]


# ═══════════════════════════════════════════════════════════════════════════
# 2. 统一系统边界 Prompt（所有 Church Health Agent 共享）
# ═══════════════════════════════════════════════════════════════════════════
SYSTEM_BOUNDARY = (
    "你是属灵星球 Church Health OS 的辅助型 AI Agent。你帮助用户在本地教会、福音、门训、"
    "悔改、敬拜、讲道回应和肢体关系中成长。\n\n"
    "绝对边界：\n"
    "1. 你不能替代牧师、长老、小组长、辅导员、医生或危机干预人员。\n"
    "2. 你不能宣告一个人是否真正重生。\n"
    "3. 你不能执行教会纪律。\n"
    "4. 你不能赦罪。\n"
    "5. 你不能要求用户离开或加入某个具体教会；只能给出辨别问题，建议与成熟基督徒或牧者交通。\n"
    "6. 你必须鼓励用户回到本地教会、真实肢体关系和真人牧养中。\n"
    "7. 你必须避免用属灵语言压制心理危机、虐待、暴力、自伤风险或专业帮助需求。\n"
    "8. 遇到危机、自伤、暴力、虐待、严重成瘾、操控关系、未成年人安全问题，必须优先安全与真人求助。\n"
    "9. 你输出的建议必须温柔、清晰、符合福音，不以控告为目的。\n"
    "10. 你要区分「个人操练建议」和「教会权柄行动」，后者不能由 AI 执行。\n"
)

# 轻量危机关键词（保底安全；真正的危机处理交给 crisis 子系统）
_CRISIS_PATTERNS = [
    "自杀", "自残", "自伤", "想死", "轻生", "结束生命", "不想活",
    "kill myself", "suicide", "self-harm", "end my life",
    "家暴", "虐待", "施暴", "性侵", "被打", "abuse", "violence",
    "未成年", "儿童", "minor", "underage",
]


def detect_crisis(*texts: Optional[str]) -> bool:
    """轻量危机信号检测；命中则应优先路由到 crisis 子系统与真人求助。"""
    blob = " ".join([t for t in texts if t]).lower()
    return any(p.lower() in blob for p in _CRISIS_PATTERNS)


# ═══════════════════════════════════════════════════════════════════════════
# 3. 九标志评分算法 v1（改编自方案 §6）
# ═══════════════════════════════════════════════════════════════════════════
MARK_WEIGHTS: Dict[str, Dict[str, float]] = {
    "expository_preaching": {"has_notes": 0.25, "has_main_point": 0.25,
                             "has_gospel_connection": 0.25, "has_obedience_action": 0.25},
    "biblical_theology": {"scripture_connection": 0.30, "redemptive_history": 0.25,
                          "christ_centered_reading": 0.25, "doctrine_application": 0.20},
    "gospel_clarity": {"god_score": 0.25, "sin_score": 0.25,
                       "christ_score": 0.30, "response_score": 0.20},
    "conversion": {"testimony_clarity": 0.30, "repentance_understanding": 0.25,
                   "faith_understanding": 0.25, "church_life_readiness": 0.20},
    "evangelism": {"prayer_for_unbelievers": 0.25, "gospel_conversation": 0.25,
                   "testimony_prepared": 0.25, "followup_love": 0.25},
    "membership": {"worship_attendance": 0.25, "membership_commitment": 0.25,
                   "small_group_participation": 0.20, "service_participation": 0.15,
                   "pastoral_connection": 0.15},
    "discipline": {"confession_honesty": 0.30, "repentance_steps": 0.25,
                   "accountability": 0.25, "restoration_progress": 0.20},
    "discipleship": {"being_discipled": 0.25, "discipling_others": 0.25,
                     "weekly_growth_review": 0.25, "service_and_imitation": 0.25},
    "leadership": {"leader_prayer": 0.25, "care_followup": 0.25,
                   "word_centered_guidance": 0.25, "healthy_authority_use": 0.25},
}

MEMBERSHIP_STATUS_SCORE = {
    "none": 0, "visitor": 25, "regular_attender": 50, "member_candidate": 70,
    "member": 100, "inactive": 30, "transferred": 40,
}


class ScoringService:
    """把每个标志的原始证据 features 归一到 0-100 分，并给出证据/风险/建议。"""

    # ── helpers ────────────────────────────────────────────────────────────
    @staticmethod
    def _n05(value: Any) -> int:
        """0-5 → 0-100。"""
        if value is None:
            return 0
        try:
            return max(0, min(100, int((float(value) / 5.0) * 100)))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _b(value: Any) -> int:
        return 100 if value else 0

    # ── public ─────────────────────────────────────────────────────────────
    def score_mark(self, mark_code: str, features: Dict[str, Any]) -> Dict[str, Any]:
        fn = {
            "gospel_clarity": self._score_gospel_clarity,
            "membership": self._score_membership,
            "expository_preaching": self._score_expository,
            "discipline": self._score_discipline,
            "discipleship": self._score_discipleship,
            "evangelism": self._score_evangelism,
            "conversion": self._score_conversion,
        }.get(mark_code)
        result = fn(features) if fn else self._score_generic(mark_code, features)
        result.setdefault("risks", [])
        result.setdefault("recommendations", [])
        result["score"] = max(0, min(100, int(result.get("score", 0))))
        return result

    # ── per-mark ─────────────────────────────────────────────────────────────
    def _score_gospel_clarity(self, f: Dict[str, Any]) -> Dict[str, Any]:
        god = self._n05(f.get("god_score"))
        sin = self._n05(f.get("sin_score"))
        christ = self._n05(f.get("christ_score"))
        response = self._n05(f.get("response_score"))
        score = int(god * 0.25 + sin * 0.25 + christ * 0.30 + response * 0.20)
        risks: List[Dict[str, Any]] = []
        distortions = f.get("detected_distortions") or []
        if distortions:
            risks.append({"type": "gospel_distortion", "items": distortions})
        recs = [{
            "type": "teaching", "title": "复习福音四格",
            "description": "从神、人、基督、回应四个角度重新整理你的福音表达。",
        }]
        if not (god or sin or christ or response):
            recs.append({"type": "start", "title": "先做一次福音清晰度评估",
                         "description": "在「福音清晰度」里写下你如何理解福音，系统会给出四格反馈。"})
        return {"score": score,
                "evidence": {"god": god, "sin": sin, "christ": christ, "response": response},
                "risks": risks, "recommendations": recs}

    def _score_membership(self, f: Dict[str, Any]) -> Dict[str, Any]:
        worship = self._b(f.get("worship_attendance"))
        small_group = self._b(f.get("small_group_participation"))
        service = self._b(bool(f.get("service_roles")))
        pastoral = self._b(f.get("pastoral_connection"))
        membership = MEMBERSHIP_STATUS_SCORE.get(f.get("membership_status", "none"), 0)
        score = int(worship * 0.25 + membership * 0.25 + small_group * 0.20
                    + service * 0.15 + pastoral * 0.15)
        recs: List[Dict[str, Any]] = []
        if score < 50:
            recs.append({"type": "membership_next_step", "title": "从稳定参加主日开始",
                         "description": "先建立稳定的本地教会敬拜节律，再考虑小组、成员课程和服事。"})
        if not f.get("small_group_participation"):
            recs.append({"type": "community", "title": "考虑加入小组或团契",
                         "description": "让自己被真实肢体认识、鼓励和劝勉。"})
        if not f.get("pastoral_connection"):
            recs.append({"type": "pastoral", "title": "认识一位教会带领者",
                         "description": "主动认识牧者/长老/小组长，让自己在牧养关系中被牧养。"})
        return {"score": score,
                "evidence": {"worship_attendance": worship, "membership": membership,
                             "small_group": small_group, "service": service,
                             "pastoral_connection": pastoral},
                "risks": [], "recommendations": recs}

    def _score_expository(self, f: Dict[str, Any]) -> Dict[str, Any]:
        notes = self._b(f.get("has_notes"))
        main_point = self._b(f.get("has_main_point"))
        gospel = self._b(f.get("has_gospel_connection"))
        obedience = self._b(f.get("has_obedience_action"))
        score = int(notes * 0.25 + main_point * 0.25 + gospel * 0.25 + obedience * 0.25)
        recs = [{"type": "sermon_response", "title": "把听道转化为本周顺服",
                 "description": "每篇讲道至少生成一个悔改点、一个信心回应、一个顺服行动。"}]
        return {"score": score,
                "evidence": {"has_notes": notes, "has_main_point": main_point,
                             "has_gospel_connection": gospel, "has_obedience_action": obedience,
                             "sermons_recorded": f.get("sermons_recorded", 0)},
                "risks": [], "recommendations": recs}

    def _score_discipline(self, f: Dict[str, Any]) -> Dict[str, Any]:
        confession = self._b(f.get("confession_notes"))
        steps = min(100, int(f.get("repentance_steps_count", 0)) * 25)
        accountability = self._b(f.get("accountability_plan"))
        restoration = self._b(f.get("repentance_status") in ("restoring", "stable"))
        score = int(confession * 0.30 + steps * 0.25 + accountability * 0.25 + restoration * 0.20)
        risks: List[Dict[str, Any]] = []
        if f.get("risk_level") in ("high", "crisis", "L2", "L3"):
            risks.append({"type": "human_care_needed", "severity": f.get("risk_level"),
                          "description": "此情况需要真人牧养或专业帮助，请勿独自面对。"})
        recs = [{"type": "restoration", "title": "进入恢复性陪伴",
                 "description": "考虑与可信的门训伙伴、小组长或牧者交通，不要独自面对。"}]
        return {"score": score,
                "evidence": {"confession": confession, "repentance_steps": steps,
                             "accountability": accountability, "restoration": restoration},
                "risks": risks, "recommendations": recs}

    def _score_discipleship(self, f: Dict[str, Any]) -> Dict[str, Any]:
        being = self._b(f.get("being_discipled"))
        discipling = self._b(f.get("discipling_others"))
        review = self._b(f.get("weekly_growth_review"))
        imitation = self._b(f.get("service_and_imitation"))
        score = int(being * 0.25 + discipling * 0.25 + review * 0.25 + imitation * 0.25)
        recs: List[Dict[str, Any]] = []
        if not being:
            recs.append({"type": "be_discipled", "title": "找一位门训你的属灵前辈",
                         "description": "成长不只是被教导，也通过效法——让一位成熟肢体陪你走一段。"})
        if not discipling and score >= 40:
            recs.append({"type": "disciple_others", "title": "开始门训一位新人",
                         "description": "把你所领受的传给下一个人（提后 2:2）。"})
        return {"score": score,
                "evidence": {"being_discipled": being, "discipling_others": discipling,
                             "weekly_growth_review": review, "service_and_imitation": imitation},
                "risks": [], "recommendations": recs}

    def _score_evangelism(self, f: Dict[str, Any]) -> Dict[str, Any]:
        prayer = self._b(f.get("prayer_for_unbelievers"))
        conversation = self._b(f.get("gospel_conversation"))
        testimony = self._b(f.get("testimony_prepared"))
        followup = self._b(f.get("followup_love"))
        score = int(prayer * 0.25 + conversation * 0.25 + testimony * 0.25 + followup * 0.25)
        recs: List[Dict[str, Any]] = []
        if not prayer:
            recs.append({"type": "pray", "title": "列一份慕道友代祷名单",
                         "description": "为 3 位尚未信主的亲友天天祷告，是布道的第一步。"})
        if not testimony:
            recs.append({"type": "testimony", "title": "预备你的个人见证",
                         "description": "用「信主前 / 如何认识基督 / 现在的改变」写下 3 分钟见证。"})
        return {"score": score,
                "evidence": {"prayer_for_unbelievers": prayer, "gospel_conversation": conversation,
                             "testimony_prepared": testimony, "followup_love": followup},
                "risks": [], "recommendations": recs}

    def _score_conversion(self, f: Dict[str, Any]) -> Dict[str, Any]:
        testimony = self._n05(f.get("testimony_clarity"))
        repentance = self._n05(f.get("repentance_understanding"))
        faith = self._n05(f.get("faith_understanding"))
        readiness = self._n05(f.get("church_life_readiness"))
        score = int(testimony * 0.30 + repentance * 0.25 + faith * 0.25 + readiness * 0.20)
        recs = [{"type": "conversation", "title": "与牧者/长老面谈你的认信",
                 "description": "AI 不判断一个人是否真正重生；请与带领者当面梳理你的认信与盲点。"}]
        return {"score": score,
                "evidence": {"testimony_clarity": testimony, "repentance_understanding": repentance,
                             "faith_understanding": faith, "church_life_readiness": readiness},
                "risks": [], "recommendations": recs}

    def _score_generic(self, mark_code: str, f: Dict[str, Any]) -> Dict[str, Any]:
        vals = [v for v in f.values() if isinstance(v, (int, float))]
        score = int(sum(vals) / len(vals)) if vals else 0
        recs = [{"type": "explore", "title": f"探索「{MARK_BY_CODE.get(mark_code, {}).get('name_zh', mark_code)}」",
                 "description": MARK_BY_CODE.get(mark_code, {}).get("blurb", "")}]
        return {"score": max(0, min(100, score)), "evidence": f, "risks": [], "recommendations": recs}


_SCORER = ScoringService()


# ═══════════════════════════════════════════════════════════════════════════
# 4. 证据聚合 → 九标志成长概览
# ═══════════════════════════════════════════════════════════════════════════
def compute_overview(evidence: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    evidence: { mark_code: {feature: value, ...}, ... }
    返回：{ marks: [ {mark_code, name_zh, name_en, score, band, evidence, risks, recommendations} ],
            overall_score, band, strongest, weakest, generated_at }
    """
    marks_out: List[Dict[str, Any]] = []
    for mark in NINE_MARKS:
        code = mark["code"]
        feats = evidence.get(code, {}) or {}
        scored = _SCORER.score_mark(code, feats)
        marks_out.append({
            "mark_code": code,
            "name_zh": mark["name_zh"],
            "name_en": mark["name_en"],
            "sort_order": mark["sort_order"],
            "module": mark["module"],
            "score": scored["score"],
            "band": _band(scored["score"]),
            "evidence": scored["evidence"],
            "risks": scored["risks"],
            "recommendations": scored["recommendations"],
        })

    overall = int(round(sum(m["score"] for m in marks_out) / len(marks_out))) if marks_out else 0
    scored_sorted = sorted(marks_out, key=lambda m: m["score"])
    weakest = [m["mark_code"] for m in scored_sorted[:2]]
    strongest = [m["mark_code"] for m in reversed(scored_sorted[-2:])]
    return {
        "marks": marks_out,
        "overall_score": overall,
        "band": _band(overall),
        "strongest": strongest,
        "weakest": weakest,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "九标志成长概览不是属灵身份审判，只用于看见成长方向、给出下一步操练、"
                      "让门训关系更具体，并为教会领袖提供匿名趋势——不做个人控制。",
    }


def _band(score: int) -> str:
    if score >= 75:
        return "healthy"       # 健康
    if score >= 50:
        return "growing"       # 成长中
    if score >= 25:
        return "attention"     # 需留意
    return "seedling"          # 起步


# ═══════════════════════════════════════════════════════════════════════════
# 5. Agents — 讲道回应 / 福音清晰度（LLM + 确定性回退）
# ═══════════════════════════════════════════════════════════════════════════
class SermonFormationOut(BaseModel):
    main_point: str = Field(default="", description="经文主旨")
    gospel_connection: str = Field(default="", description="如何指向基督与福音")
    repentance_prompt: str = Field(default="", description="需要悔改之处")
    faith_prompt: str = Field(default="", description="需要相信之处")
    obedience_action: str = Field(default="", description="本周顺服行动")
    community_action: str = Field(default="", description="在肢体关系中的应用")


class GospelClarityOut(BaseModel):
    god_score: int = Field(default=0, ge=0, le=5)
    sin_score: int = Field(default=0, ge=0, le=5)
    christ_score: int = Field(default=0, ge=0, le=5)
    response_score: int = Field(default=0, ge=0, le=5)
    detected_distortions: List[str] = Field(default_factory=list)
    gentle_reframe: str = Field(default="")
    next_teaching: str = Field(default="")


def _use_llm() -> bool:
    """仅在配置了真实 LLM provider 时走模型；否则用（更有信息量的）确定性回退。"""
    if _llm is None or not hasattr(_llm, "generate_json"):
        return False
    checker = getattr(_llm, "_real_configured", None)
    if checker is None:
        return True
    try:
        return bool(checker())
    except Exception:
        return False


def run_sermon_formation(scripture_ref: str, raw_notes: str,
                         user_reflection: str = "", sermon_title: str = "",
                         email: Optional[str] = None) -> Dict[str, Any]:
    """把主日讲道转化为：主旨→悔改→相信→顺服→肢体应用。"""
    payload = {
        "scripture_ref": scripture_ref,
        "sermon_title": sermon_title,
        "raw_notes": raw_notes,
        "user_reflection": user_reflection,
    }
    system = (SYSTEM_BOUNDARY + "\n你现在扮演 Expository Sermon Formation Agent。"
              "抓住这段经文的主旨（不要脱离经文自由发挥），指出它如何指向基督与福音，"
              "并帮助用户把听道转化为具体的悔改、信心与顺服，以及在肢体关系中的应用。"
              "语气温柔、以福音为中心，不以控告为目的。")
    if _use_llm():
        try:
            model = _llm.generate_json(system, payload, SermonFormationOut,
                                       email=email, agent_name="sermon_formation",
                                       skill_name="church_health.sermon_formation")
            data = model.model_dump()
            if any(data.values()):
                data["source"] = "ai"
                return data
        except Exception:
            pass
    return {**_fallback_sermon(scripture_ref, raw_notes, user_reflection), "source": "fallback"}


def _fallback_sermon(scripture_ref: str, raw_notes: str, user_reflection: str) -> Dict[str, Any]:
    ref = scripture_ref or "这段经文"
    seed = (raw_notes or user_reflection or "").strip()
    hint = (seed[:60] + "…") if len(seed) > 60 else seed
    return SermonFormationOut(
        main_point=f"用一句话写下 {ref} 的经文主旨：这段经文主要在讲什么？" + (f"（你的笔记提到：{hint}）" if hint else ""),
        gospel_connection=f"{ref} 如何指向基督？问：这里显明了神怎样的性情？人怎样的需要？基督怎样成全？",
        repentance_prompt="根据所听的道，我需要向神悔改的一件具体的事是什么？",
        faith_prompt="这段经文邀请我重新相信关于神/基督/福音的哪一个真理？",
        obedience_action="本周一个可执行的顺服行动（具体、可完成、可复盘）。",
        community_action="我可以和哪一位肢体分享这个领受，或在关系中如何应用（道歉/服事/劝勉/代祷）？",
    ).model_dump()


def run_gospel_clarity(source_text: str, source_type: str = "user_reflection",
                       email: Optional[str] = None) -> Dict[str, Any]:
    """
    评估一段表达的福音清晰度（神-人-基督-回应 四格，0-5），并检测常见假福音。
    返回 dict，含四格分数 + detected_distortions + gentle_reframe + 便于评分的 features。
    """
    payload = {"source_type": source_type, "source_text": source_text}
    system = (SYSTEM_BOUNDARY + "\n你现在扮演 Gospel Clarity Agent。"
              "判断用户的表达是否偏离福音，从四个维度打分（0-5）：\n"
              "god_score=是否清楚神的圣洁与创造；sin_score=是否认识人的罪与审判；\n"
              "christ_score=是否以基督的位格/十字架/复活为中心；response_score=是否包含悔改与信心的回应。\n"
              "detected_distortions 从以下集合中选择命中的：道德主义、成功神学、治疗主义、律法主义、廉价恩典、个人主义。\n"
              "gentle_reframe 用温柔、以福音为中心、不控告的语气，把根基重新指回基督已成就的救赎。")
    result: Optional[Dict[str, Any]] = None
    if _use_llm():
        try:
            model = _llm.generate_json(system, payload, GospelClarityOut,
                                       email=email, agent_name="gospel_clarity",
                                       skill_name="church_health.gospel_clarity")
            result = model.model_dump()
            result["source"] = "ai"
        except Exception:
            result = None
    if result is None:
        result = {**_fallback_gospel(source_text), "source": "fallback"}
    # 便于 membership/gospel 评分复用
    result["features"] = {
        "god_score": result.get("god_score", 0),
        "sin_score": result.get("sin_score", 0),
        "christ_score": result.get("christ_score", 0),
        "response_score": result.get("response_score", 0),
        "detected_distortions": result.get("detected_distortions", []),
    }
    return result


# 假福音关键词（回退用；命中即降低相应维度并提示）
_DISTORTION_RULES = [
    ("道德主义", ["表现好", "做得够", "配得", "值得神", "努力换取", "行为好"]),
    ("成功神学", ["一定顺利", "必然成功", "赐我财富", "身体一定得医治", "事业顺利"]),
    ("治疗主义", ["感觉好", "让我快乐", "心理平安就够", "只要开心"]),
    ("律法主义", ["必须守", "靠遵守", "不够属灵", "达标才", "规条"]),
    ("廉价恩典", ["不用悔改", "随便犯", "反正被赦免", "不必认真"]),
    ("个人主义", ["不需要教会", "自己和神就够", "不用聚会", "独自信"]),
]


def _fallback_gospel(text: str) -> Dict[str, Any]:
    t = (text or "").lower()
    def has(words: List[str]) -> bool:
        return any(w.lower() in t for w in words)
    god = 4 if has(["神", "圣洁", "创造", "主", "god", "holy"]) else 1
    sin = 4 if has(["罪", "悔改", "过犯", "sin", "repent"]) else 1
    christ = 4 if has(["基督", "耶稣", "十字架", "复活", "救赎", "christ", "jesus", "cross"]) else 1
    response = 4 if has(["相信", "信靠", "悔改", "顺服", "回应", "faith", "believe", "trust"]) else 1
    distortions = [name for name, kws in _DISTORTION_RULES if has(kws)]
    if distortions:
        # 假福音命中时，把「回应/基督」根基分数拉低，提示重新以基督为根基
        response = min(response, 2)
    reframe = ("你现在的表达里，似乎把「神接纳你」的根基放在表现或感受上。福音提醒你：你被接纳的根基"
               "不是今天的属灵表现，而是基督已经为你成就的救赎。今天的回应不是自责，而是悔改、相信、"
               "重新顺服。") if distortions else \
              ("你的表达触及了福音的重要面向。可以再问自己：神的圣洁、人的罪、基督的十架与复活、"
               "以及悔改与信心的回应，这四格是否都清楚？")
    return GospelClarityOut(
        god_score=god, sin_score=sin, christ_score=christ, response_score=response,
        detected_distortions=distortions, gentle_reframe=reframe,
        next_teaching="复习福音四格：神—人—基督—回应。建议在主日讲道与本地教会教导中被牧养这四格。",
    ).model_dump()


# ═══════════════════════════════════════════════════════════════════════════
# 6. 数据表（懒建表；按 email 归属）
# ═══════════════════════════════════════════════════════════════════════════
SCHEMA_SQL = """
-- 本地教会委身档案（每用户一行）
CREATE TABLE IF NOT EXISTS ch_membership (
    email                         TEXT PRIMARY KEY,
    church_name                   TEXT,
    church_id                     TEXT,
    membership_status             TEXT NOT NULL DEFAULT 'none',
    baptism_status                TEXT NOT NULL DEFAULT 'unknown',
    joined_at                     DATE,
    small_group_name              TEXT,
    worship_attendance            BOOLEAN NOT NULL DEFAULT FALSE,
    small_group_participation     BOOLEAN NOT NULL DEFAULT FALSE,
    pastoral_connection           BOOLEAN NOT NULL DEFAULT FALSE,
    service_roles                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    one_another_notes             TEXT,
    consent_to_share_with_leader  BOOLEAN NOT NULL DEFAULT FALSE,
    consent_to_anonymous_aggregate BOOLEAN NOT NULL DEFAULT TRUE,
    notes                         TEXT,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 主日讲道记录与回应
CREATE TABLE IF NOT EXISTS ch_sermon_records (
    id                SERIAL PRIMARY KEY,
    email             TEXT NOT NULL,
    church_name       TEXT,
    preacher_name     TEXT,
    sermon_title      TEXT,
    scripture_ref     TEXT NOT NULL,
    sermon_date       DATE,
    raw_notes         TEXT,
    main_point        TEXT,
    gospel_connection TEXT,
    repentance_prompt TEXT,
    faith_prompt      TEXT,
    obedience_action  TEXT,
    community_action  TEXT,
    visibility        TEXT NOT NULL DEFAULT 'private',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_sermon_email ON ch_sermon_records(email, created_at DESC);

-- 福音清晰度评估（强隐私，仅本人）
CREATE TABLE IF NOT EXISTS ch_gospel_assessments (
    id                    SERIAL PRIMARY KEY,
    email                 TEXT NOT NULL,
    source_type           TEXT NOT NULL DEFAULT 'user_reflection',
    source_text           TEXT,
    god_score             INT NOT NULL DEFAULT 0,
    sin_score             INT NOT NULL DEFAULT 0,
    christ_score          INT NOT NULL DEFAULT 0,
    response_score        INT NOT NULL DEFAULT 0,
    detected_distortions  JSONB NOT NULL DEFAULT '[]'::jsonb,
    gentle_reframe        TEXT,
    next_teaching         TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_gospel_email ON ch_gospel_assessments(email, created_at DESC);

-- 悔改与恢复记录（极高隐私，默认仅本人；不自动通知领袖）
CREATE TABLE IF NOT EXISTS ch_repentance_patterns (
    id                SERIAL PRIMARY KEY,
    email             TEXT NOT NULL,
    sin_pattern       TEXT NOT NULL,
    trigger_context   TEXT,
    confession_notes  TEXT,
    repentance_steps  JSONB NOT NULL DEFAULT '[]'::jsonb,
    accountability_plan TEXT,
    repentance_status TEXT NOT NULL DEFAULT 'struggling',
    risk_level        TEXT NOT NULL DEFAULT 'low',
    leader_visibility TEXT NOT NULL DEFAULT 'private',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_repent_email ON ch_repentance_patterns(email, created_at DESC);

-- 门训关系
CREATE TABLE IF NOT EXISTS ch_discipleship (
    id                SERIAL PRIMARY KEY,
    email             TEXT NOT NULL,          -- 记录创建者（本人是 mentor 或 mentee 之一）
    counterpart       TEXT,                   -- 对方（昵称或 email）
    relation_type     TEXT NOT NULL DEFAULT 'peer',  -- being_discipled / discipling / peer
    goals             JSONB NOT NULL DEFAULT '[]'::jsonb,
    meeting_rhythm    TEXT,
    last_meeting_at   TIMESTAMPTZ,
    next_meeting_at   TIMESTAMPTZ,
    status            TEXT NOT NULL DEFAULT 'active',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_disciple_email ON ch_discipleship(email, created_at DESC);

-- 九标志个人成长快照（每次 compute 落一批，mark_code 一行）
CREATE TABLE IF NOT EXISTS ch_mark_snapshots (
    id                SERIAL PRIMARY KEY,
    email             TEXT NOT NULL,
    batch_id          TEXT NOT NULL,
    mark_code         TEXT NOT NULL,
    score             INT NOT NULL DEFAULT 0,
    band              TEXT,
    evidence          JSONB NOT NULL DEFAULT '{}'::jsonb,
    risks             JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations   JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall_score     INT NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_snap_email ON ch_mark_snapshots(email, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ch_snap_batch ON ch_mark_snapshots(batch_id);

-- 牧养关怀信号（本人可读；leader 仅在授权/安全策略下可读授权信号）
CREATE TABLE IF NOT EXISTS ch_care_signals (
    id                 SERIAL PRIMARY KEY,
    email              TEXT NOT NULL,
    church_id          TEXT,
    signal_type        TEXT NOT NULL,
    severity           TEXT NOT NULL DEFAULT 'low',
    summary            TEXT,
    recommended_action TEXT,
    consent_share      BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ch_care_email ON ch_care_signals(email, created_at DESC);
"""


def ensure_tables(conn) -> None:
    """在首个请求时懒建表（与本仓库其它 router 的做法一致）。"""
    with conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
    conn.commit()


def meta() -> Dict[str, Any]:
    """给前端的元信息：九标志字典 + 边界说明。"""
    return {
        "marks": [
            {k: m[k] for k in ("code", "name_zh", "name_en", "sort_order", "module", "blurb", "biblical_basis")}
            for m in NINE_MARKS
        ],
        "bands": {
            "healthy": "健康 (≥75)",
            "growing": "成长中 (50-74)",
            "attention": "需留意 (25-49)",
            "seedling": "起步 (<25)",
        },
        "boundaries": [
            "九标志成长概览不是属灵身份审判。",
            "AI 不定罪、不赦罪、不执行教会纪律、不判断一个人是否真正重生。",
            "遇危机优先安全与真人求助（crisis-first）。",
            "悔改/恢复记录默认仅本人可见，除非明确授权或安全策略触发。",
        ],
    }
