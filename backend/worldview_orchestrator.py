"""
worldview_orchestrator.py — Kingdom Lens OS / 世界观塑造编排层

这是 "Worldview Formation OS" 的上层认知编排器。它本身不做神学分析，而是把既有的
独立引擎（idolatry / gospel / stronghold / crisis / decision / formation …）串成一个
**闭环管线**，并在最前面挂一道**危机优先 (crisis-first) 守卫**。

闭环（规格第 0 节）：
    真实输入(日记/祷告/对话/情绪/决策/苦难)
      → [守卫] 危机分级 (crisis_engine.triage)        ← 高危时立即转向，跳过世界观分析
      → 世界观诊断 (worldview_diagnoser_engine)
      → 偶像与扭曲信念 (idolatry_engine)
      → 圣经真理映射 (truth_mapper_engine / gospel_engine + stronghold_rag)
      → 福音叙事重写 (narrative_engine)
      → 具体领域重塑 (apologetics / cultural / vocation / suffering)
      → 操练任务 (spiritual_formation_engine)
      → 复盘快照 (worldview_metric_snapshots)

设计原则
========
1. **安全优先**：任何世界观/苦难分析之前必须先过 `crisis_guard()`。high/imminent 直接
   返回危机路由建议，绝不输出复杂神学分析。
2. **复用而非复制**：下游全部委托既有引擎；本模块只负责编排、降级与审计。
3. **优雅降级**：任一下游引擎缺失/异常都不应让整条链崩溃 —— 捕获并记录，继续可用部分。
4. **无状态纯函数**：便于被 router 与测试复用；DB 落库由 router 负责。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# 规格 worldview_agent_type 顺序（供前端 / 审计引用）
AGENT_SEQUENCE: List[str] = [
    "worldview_diagnoser",
    "idol_detector",
    "biblical_truth_mapper",
    "narrative_rewriter",
    "apologetics_lens",
    "cultural_discernment",
    "vocation_worldview",
    "suffering_theology",
    "decision_formation",
    "formation_practice",
]


# ---------------------------------------------------------------------------
# 危机等级映射：既有 crisis_engine 用 green/yellow/orange/red；
# 规格 crisis_risk_level 用 none/low/medium/high/imminent。
# ---------------------------------------------------------------------------
_CRISIS_LEVEL_MAP = {
    "green": "none",
    "yellow": "medium",
    "orange": "high",
    "red": "imminent",
}
# high/imminent：必须跳过神学分析，先安全
_BLOCK_LEVELS = {"orange", "red"}


def _import_engine(name: str):
    """兼容 backend.* 与顶层两种导入路径；失败返回 None（优雅降级）。"""
    try:
        return __import__(f"backend.{name}", fromlist=[name])
    except Exception:
        try:
            return __import__(name)
        except Exception:
            return None


def map_crisis_level(level: str) -> str:
    """green/yellow/orange/red → none/low/medium/high/imminent。"""
    return _CRISIS_LEVEL_MAP.get((level or "green").lower(), "none")


# ---------------------------------------------------------------------------
# 危机优先守卫
# ---------------------------------------------------------------------------
def crisis_guard(
    text: str,
    *,
    locale: Optional[str] = None,
    context_levels: Optional[List[str]] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    在任何世界观/苦难分析之前调用。先跑 crisis_engine.triage()。

    返回 (safe_to_analyze, assessment)：
      safe_to_analyze=False  →  高危，必须转向危机/苦难安全路由，**不得**输出世界观分析
      assessment = {
        riskLevelRaw, crisisRiskLevel, riskTypes, evidence, confidence,
        requiresImmediateSafetyResponse, shouldAvoidTheologicalAnalysis,
        recommendedResponseMode, recommendedNextAgents
      }
    若 crisis_engine 不可用，则保守地放行但标注 degraded（永不因守卫缺失而误判为高危阻断）。
    """
    ce = _import_engine("crisis_engine")
    if ce is None:  # 守卫缺失：保守放行但记录降级
        return True, {
            "riskLevelRaw": "green",
            "crisisRiskLevel": "none",
            "riskTypes": [],
            "evidence": [],
            "confidence": 0.0,
            "requiresImmediateSafetyResponse": False,
            "shouldAvoidTheologicalAnalysis": False,
            "recommendedResponseMode": "normal",
            "recommendedNextAgents": [],
            "degraded": True,
        }

    tri = ce.triage(text or "", context_levels=context_levels)
    raw = tri.get("riskLevel", "green")
    block = (raw in _BLOCK_LEVELS) or bool(tri.get("requiresHumanEscalation")) \
        or bool(tri.get("requiresDirectSafetyQuestion"))

    next_agents: List[str] = []
    if block:
        # 高危：只走苦难神学的安全路由（它内部还会再次危机分级）
        next_agents = ["suffering_theology"]

    assessment = {
        "riskLevelRaw": raw,
        "crisisRiskLevel": map_crisis_level(raw),
        "riskTypes": tri.get("riskTypes", []),
        "evidence": tri.get("evidence", []),
        "confidence": tri.get("confidence", 0.0),
        "requiresImmediateSafetyResponse": bool(tri.get("requiresHumanEscalation")),
        "shouldAvoidTheologicalAnalysis": block,
        "recommendedResponseMode": "crisis_safety" if block else "normal",
        "recommendedNextAgents": next_agents,
        "degraded": False,
    }
    return (not block), assessment


# ---------------------------------------------------------------------------
# 主管线：诊断闭环（Batch 1+ 逐步接入下游引擎）
# ---------------------------------------------------------------------------
def run_pipeline(
    *,
    user_id: Optional[str],
    text: str,
    source_type: str = "journal",
    locale: Optional[str] = None,
    context_levels: Optional[List[str]] = None,
    signals: Optional[Dict[str, Any]] = None,
    stages: Optional[List[str]] = None,
    use_ai: bool = False,
) -> Dict[str, Any]:
    """
    运行世界观闭环。stages 控制要跑哪些阶段（默认核心诊断链）。

    返回：
      {
        crisis: {...},                 # 危机守卫结果（总是存在）
        blocked: bool,                 # True = 高危，已跳过世界观分析
        stagesRun: [...],
        diagnosis: {...} | None,       # Worldview Diagnoser（Batch 1）
        idols: {...} | None,           # Idol Detector
        truthMap: {...} | None,        # Biblical Truth Mapper
        narrative: {...} | None,       # Narrative Rewriter
        recommendedNextAgents: [...],
        notes: [...],                  # 降级 / 跳过等说明
      }
    """
    out: Dict[str, Any] = {
        "blocked": False,
        "stagesRun": [],
        "diagnosis": None,
        "idols": None,
        "truthMap": None,
        "narrative": None,
        "recommendedNextAgents": [],
        "notes": [],
    }

    # 1) 危机优先守卫
    safe, crisis = crisis_guard(text, locale=locale, context_levels=context_levels)
    out["crisis"] = crisis
    if crisis.get("degraded"):
        out["notes"].append("crisis_engine 不可用：已保守放行，但请尽快修复危机守卫。")
    if not safe:
        out["blocked"] = True
        out["recommendedNextAgents"] = crisis.get("recommendedNextAgents", ["suffering_theology"])
        out["notes"].append("检测到高风险：已跳过世界观分析，转向危机/苦难安全路由。")
        return out

    default_stages = ["worldview_diagnoser", "idol_detector",
                      "biblical_truth_mapper", "narrative_rewriter"]
    stages = stages or default_stages

    # 2) 世界观诊断（Batch 1）
    if "worldview_diagnoser" in stages:
        diag = _safe_call_diagnoser(user_id, text, source_type, locale, signals, use_ai)
        if diag is not None:
            out["diagnosis"] = diag
            out["stagesRun"].append("worldview_diagnoser")
            for a in diag.get("recommendedNextAgents", []):
                if a not in out["recommendedNextAgents"]:
                    out["recommendedNextAgents"].append(a)
        else:
            out["notes"].append("worldview_diagnoser_engine 尚未接入或不可用。")

    # 3) 偶像识别：综合「诊断信念的 idolHint」与（可选）情绪/注意力信号
    if "idol_detector" in stages:
        diag0 = out.get("diagnosis") or {}
        hint_idols = [b.get("idolHint") for b in diag0.get("extractedBeliefs", [])
                      if b.get("idolHint")]
        sig = _safe_suggest_idols(signals) or {}
        sig_idols = sig.get("suggestedTargets", []) if isinstance(sig, dict) else []
        targets = list(dict.fromkeys([*hint_idols, *sig_idols]))
        out["idols"] = {"suggestedTargets": targets}
        out["stagesRun"].append("idol_detector")

    diag = out.get("diagnosis") or {}
    beliefs = diag.get("extractedBeliefs", [])

    # 4) 圣经真理映射
    if "biblical_truth_mapper" in stages and beliefs:
        tmap = _safe_truth_map(beliefs, use_ai)
        if tmap is not None:
            out["truthMap"] = tmap
            out["stagesRun"].append("biblical_truth_mapper")

    # 5) 福音叙事重写（取最突出的一条信念）
    if "narrative_rewriter" in stages and beliefs:
        top = beliefs[0]
        narr = _safe_narrative(top, raw_text=text, use_ai=use_ai)
        if narr is not None:
            out["narrative"] = narr
            out["stagesRun"].append("narrative_rewriter")

    return out


def _safe_call_diagnoser(user_id, text, source_type, locale, signals, use_ai=False):
    eng = _import_engine("worldview_diagnoser_engine")
    if eng is None or not hasattr(eng, "diagnose"):
        return None
    try:
        return eng.diagnose(
            user_id=user_id, text=text, source_type=source_type,
            locale=locale, signals=signals, use_ai=use_ai,
        )
    except Exception:
        return None


def _safe_suggest_idols(signals):
    eng = _import_engine("idolatry_engine")
    if eng is None or not hasattr(eng, "suggested_targets"):
        return None
    try:
        targets = eng.suggested_targets(signals or {})
        return {"suggestedTargets": targets} if targets else {"suggestedTargets": []}
    except Exception:
        return None


def _safe_truth_map(beliefs, use_ai=False):
    eng = _import_engine("truth_mapper_engine")
    if eng is None or not hasattr(eng, "map_beliefs"):
        return None
    try:
        return eng.map_beliefs(beliefs, use_ai=use_ai)
    except Exception:
        return None


def _safe_narrative(top_belief, raw_text="", use_ai=False):
    eng = _import_engine("narrative_engine")
    if eng is None or not hasattr(eng, "rewrite"):
        return None
    try:
        return eng.rewrite(
            raw_text=raw_text,
            idol_category=top_belief.get("idolHint") or top_belief.get("idol_category"),
            domain=top_belief.get("domain"),
            use_ai=use_ai,
        )
    except Exception:
        return None


def meta() -> Dict[str, Any]:
    """静态配置：暴露 agent 序列与危机等级映射，供前端/审计。"""
    return {
        "module": "Kingdom Lens OS",
        "agentSequence": AGENT_SEQUENCE,
        "crisisLevelMap": _CRISIS_LEVEL_MAP,
        "blockLevels": sorted(_BLOCK_LEVELS),
    }
