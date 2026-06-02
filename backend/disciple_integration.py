#!/usr/bin/env python3
"""
Disciple Integration Layer — 把散落的属灵子系统打通成一个孪生 + 一个导师 + 一张图。
============================================================================

这一层是"整合宪章"的落地：门徒塑造引擎不再是孤岛，而是吸收并编排既有引擎：

  统一数字孪生 (gather_unified_twin)
      从 idolatry(依附指数) / waiting(等候) / checkup(属灵低潮) /
      gospel(福音诊断) / decision(决策辨识) / virtues(信望爱·若有 formation 快照)
      读取每用户最新信号，映射进门徒塑造的 11 维 / 偶像 / 品格先验。

  统一导师上下文 (gather_mentor_context)
      把最近的福音诊断、属灵体检、等候模式喂给门徒塑造导师，
      让 gospel/checkup/pastoral 的牧养成果成为导师的记忆。

  Neo4j 图谱同步 (sync_graph / graph_insights)
      把 Person/State/Belief/Idol/Disciple 关系写进既有的真 Neo4j 图层
      (graph_layer.get_neo4j)，并查询偶像路径与门徒复制链。未配置 Neo4j 时静默降级。

  周/月复盘 (weekly_review / monthly_review)
      聚合 disciple_assessments，给出维度趋势、主导偶像、成长边界、状态迁移建议。

  事件流 (log_event → domain_events)
      记录 ReflectionAssessed / StateChanged / IdolDetected 等领域事件。

设计铁律：每个外部读取都在自己的 try/except 里，任何子系统缺失/报错都只是"少一个来源"，
绝不破坏已经跑通的门徒塑造主流程。所有纯映射函数与 DB 解耦，便于单测。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

try:
    from backend import disciple_engine as de
except Exception:  # pragma: no cover
    import disciple_engine as de  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 映射表：外部子系统的"偶像/品格/维度"词汇 → 门徒塑造的标准 key
# ─────────────────────────────────────────────────────────────────────────────

# idolatry_engine target_type → disciple idol key
_IDOL_FROM_ATTACHMENT = {
    "success": "success", "money": "investment", "approval": "approval",
    "control": "control", "relationship": "relationship", "comfort": "comfort",
    "spiritual_image": "ministry",
}
# gospel_engine idol_type → disciple idol key
_IDOL_FROM_GOSPEL = {
    "control": "control", "approval": "approval", "comfort": "comfort",
    "security": "control", "success": "success", "relationship": "relationship",
    "power": "power", "ministry": "ministry",
}
# virtues_engine 9 品格 key → disciple character key
_CHAR_FROM_VIRTUE = {
    "humility": "humility", "obedience": "faithfulness", "holiness": "holiness",
    "wisdom": "gentleness", "courage": "courage", "perseverance": "patience",
    "love": "love", "faith": None, "hope": None,
}


def _clip100(x: float) -> float:
    return max(1.0, min(99.0, float(x)))


# ─────────────────────────────────────────────────────────────────────────────
# 1. 统一数字孪生：从所有子系统读取 → 标准化先验
# ─────────────────────────────────────────────────────────────────────────────

def _safe(cur, sql, params) -> List[tuple]:
    try:
        cur.execute(sql, params)
        return cur.fetchall()
    except Exception:
        try:
            cur.connection.rollback()
        except Exception:
            pass
        return []


def gather_unified_twin(cur, email: str, user_id: Optional[str] = None,
                        settings: Any = None) -> Dict[str, Any]:
    """
    汇总外部子系统信号 → 返回:
      {
        "dim_prior": {dim: score},          # 部分维度的外部先验(0~100)
        "idol_prior": {idol_key: score},    # 部分偶像的外部证据(0~100)
        "char_prior": {char_key: score},    # 部分品格外部先验(0~100)
        "provenance": [{"source","label","detail"}...],  # 哪些子系统供了数
      }
    任何来源缺失都只是少一项。纯读，不写。
    """
    dim_prior: Dict[str, float] = {}
    idol_prior: Dict[str, float] = {}
    char_prior: Dict[str, float] = {}
    prov: List[Dict[str, str]] = []

    # —— 偶像监测 / 依附强度指数 (attachment_sessions + attachment_patterns) ——
    try:
        rows = _safe(cur,
            "SELECT top_target, top_intensity, risk_level FROM attachment_sessions "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            tt, inten, risk = rows[0]
            k = _IDOL_FROM_ATTACHMENT.get(tt)
            if k and inten is not None:
                idol_prior[k] = max(idol_prior.get(k, 0), _clip100(float(inten) * 100))
            prov.append({"source": "idolatry", "label": "偶像监测",
                         "detail": f"{tt or '—'} · {risk or ''}"})
        # 各 idol 的细分强度
        prows = _safe(cur,
            "SELECT target_type, MAX(intensity) FROM attachment_patterns "
            "WHERE email=%s GROUP BY target_type", (email,))
        for tt, inten in prows:
            k = _IDOL_FROM_ATTACHMENT.get(tt)
            if k and inten is not None:
                idol_prior[k] = max(idol_prior.get(k, 0), _clip100(float(inten) * 100))
    except Exception:
        pass

    # —— 等候之路 (waiting_cases) → hope / faith / obedience ——
    try:
        rows = _safe(cur,
            "SELECT hope_level, trust_level, anxiety_level, obedience_readiness, waiting_type "
            "FROM waiting_cases WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            hope_l, trust_l, anx_l, obed_r, wtype = rows[0]
            if hope_l is not None:
                dim_prior["hope"] = _clip100(float(hope_l) * 10)
            if trust_l is not None:
                dim_prior["faith"] = _clip100(float(trust_l) * 10)
            if anx_l is not None and "hope" in dim_prior:
                dim_prior["hope"] = _clip100((dim_prior["hope"] + (100 - float(anx_l) * 10)) / 2)
            if obed_r is not None:
                dim_prior["obedience"] = _clip100(float(obed_r) * 10)
            prov.append({"source": "waiting", "label": "等候之路", "detail": wtype or ""})
    except Exception:
        pass

    # —— 属灵低潮体检 (spiritual_checkups) → 反转为安康度，影响 hope / character ——
    try:
        rows = _safe(cur,
            "SELECT index_score, level FROM spiritual_checkups "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            idx, level = rows[0]
            if idx is not None:
                wellbeing = _clip100((1 - float(idx)) * 100)  # index 高=低潮重
                dim_prior["hope"] = _clip100((dim_prior.get("hope", wellbeing) + wellbeing) / 2)
                char_prior["patience"] = wellbeing
            prov.append({"source": "checkup", "label": "属灵低潮体检", "detail": level or ""})
    except Exception:
        pass

    # —— 福音诊断 (gospel_diagnoses) → 偶像证据 ——
    try:
        rows = _safe(cur,
            "SELECT idol_type, emotion FROM gospel_diagnoses "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            it, emo = rows[0]
            k = _IDOL_FROM_GOSPEL.get(it)
            if k:
                idol_prior[k] = max(idol_prior.get(k, 0), 60.0)
            prov.append({"source": "gospel", "label": "福音诊断",
                         "detail": (de.IDOLS.get(k, {}).get("zh", it) if k else (emo or ""))})
    except Exception:
        pass

    # —— 决策辨识 (decision_discernments) → calling/obedience 轻先验 ——
    try:
        rows = _safe(cur,
            "SELECT analysis_json FROM decision_discernments "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows and rows[0][0]:
            aj = rows[0][0] if isinstance(rows[0][0], dict) else json.loads(rows[0][0])
            opts = aj.get("options") or []
            if opts:
                best = max(opts, key=lambda o: o.get("score", 0))
                if best.get("obedience") is not None:
                    dim_prior.setdefault("obedience", _clip100(float(best["obedience"]) * 10))
            prov.append({"source": "decision", "label": "决策辨识", "detail": ""})
    except Exception:
        pass

    # —— 信望爱 / formation 八维(若有快照) → faith/hope/love + 9 品格 ——
    #   formation 用 user_id 标识，且为增量 delta 累积，难以直接取绝对值；
    #   这里尽力而为：若 virtues_engine 能从某处给出 indices 则纳入，否则跳过。
    try:
        sv = _load_formation_state_vector(cur, [user_id, email])
        if sv:
            try:
                from backend import virtues_engine as ve
            except Exception:
                import virtues_engine as ve  # type: ignore
            res = ve.evaluate(sv)
            if res.get("has_data"):
                idx = res.get("indices", {})
                for d in ("faith", "hope", "love"):
                    if idx.get(d) is not None:
                        v = _clip100(float(idx[d]) * 100 if float(idx[d]) <= 1 else float(idx[d]))
                        dim_prior[d] = _clip100((dim_prior.get(d, v) + v) / 2)
                for v in res.get("virtues", []):
                    ck = _CHAR_FROM_VIRTUE.get(v.get("key"))
                    if ck and v.get("score") is not None:
                        s = float(v["score"]); s = s * 100 if s <= 1 else s
                        char_prior[ck] = _clip100(s)
                prov.append({"source": "virtues", "label": "信望爱星系", "detail": ""})
    except Exception:
        pass

    return {"dim_prior": dim_prior, "idol_prior": idol_prior,
            "char_prior": char_prior, "provenance": prov}


def _load_formation_state_vector(cur, candidates) -> Optional[Dict[str, float]]:
    """尝试把 sfds_formation_metrics 的 *_delta 累积成一个粗略 state_vector(0~1)。
    formation 用 user_id（本项目=数字 users.id）；为彻底对齐，依次尝试
    [user_id, email] 多个候选标识，任一查到即用。"""
    cols = ["humility", "fear_tendency", "pride_tendency", "emotional_stability",
            "truth_alignment", "relational_health", "resilience", "spiritual_clarity"]
    sel = ", ".join(f"COALESCE(SUM({c}_delta),0)" for c in cols)
    vals = None
    for cand in candidates:
        if not cand:
            continue
        rows = _safe(cur,
            f"SELECT {sel} FROM sfds_formation_metrics WHERE user_id=%s", (str(cand),))
        if rows and rows[0] is not None and not all(
                (v is None or float(v) == 0) for v in rows[0]):
            vals = rows[0]
            break
    if vals is None:
        return None
    # 把累积 delta 经 sigmoid 压到 0.05~0.95，中心 0.5
    import math
    sv = {}
    for c, v in zip(cols, vals):
        x = float(v or 0)
        sv[c] = max(0.05, min(0.95, 1 / (1 + math.exp(-x))))
    return sv


# ── 把统一先验融进 assess 的输入/结果 ─────────────────────────────────────────

def apply_unified_prior_to_twin(twin: Dict[str, Any], unified: Dict[str, Any]) -> Dict[str, Any]:
    """把外部 dim_prior 叠加到 twin['dims']，作为 assess 的更聪明先验。"""
    twin = dict(twin or {})
    dims = dict(twin.get("dims") or {k: 50.0 for k in de.DIM_KEYS})
    for k, v in (unified.get("dim_prior") or {}).items():
        if k in de.DIM_KEYS:
            dims[k] = round((dims.get(k, 50.0) + float(v)) / 2, 1)  # 与既有先验各半
    twin["dims"] = dims
    return twin


def fuse_external_idols(result: Dict[str, Any], unified: Dict[str, Any]) -> Dict[str, Any]:
    """assess 后，把外部偶像证据并入 result.idol_scores（取较大值），重算 top/risk。"""
    idol_prior = unified.get("idol_prior") or {}
    if not idol_prior:
        return result
    scores = dict(result.get("idol_scores") or {})
    for k, v in idol_prior.items():
        if k in de.IDOL_KEYS:
            scores[k] = round(max(scores.get(k, 0), float(v)), 1)
    tops = sorted(scores, key=scores.get, reverse=True)[:3]
    result["idol_scores"] = scores
    result["top_idols"] = tops
    result["top_idol"] = tops[0] if tops and scores[tops[0]] > 25 else None
    result["risk_level"] = de._risk_level(scores[tops[0]]) if tops else "LOW"
    # 同步进 idol 引擎卡
    if "engines" in result and "idol" in result["engines"]:
        result["engines"]["idol"]["scores"] = scores
        result["engines"]["idol"]["top_idols"] = tops
        result["engines"]["idol"]["risk_level"] = result["risk_level"]
    return result


def fuse_external_character(result: Dict[str, Any], unified: Dict[str, Any]) -> Dict[str, Any]:
    char_prior = unified.get("char_prior") or {}
    if not char_prior:
        return result
    cs = dict(result.get("character_scores") or {})
    for k, v in char_prior.items():
        if k in de.CHAR_KEYS:
            cs[k] = round((cs.get(k, 50.0) + float(v)) / 2, 1)
    result["character_scores"] = cs
    if "engines" in result and "character" in result["engines"]:
        result["engines"]["character"]["scores"] = cs
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. 统一导师上下文
# ─────────────────────────────────────────────────────────────────────────────

def gather_mentor_context(cur, email: str) -> Dict[str, Any]:
    """把最近的福音诊断 / 体检 / 等候 牧养成果，作为导师的记忆上下文。"""
    ctx: Dict[str, Any] = {}
    try:
        rows = _safe(cur,
            "SELECT idol_type, gospel_truth, action FROM gospel_diagnoses "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            ctx["gospel"] = {"idol": rows[0][0], "truth": rows[0][1], "action": rows[0][2]}
    except Exception:
        pass
    try:
        rows = _safe(cur,
            "SELECT level, summary FROM spiritual_checkups "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            ctx["checkup"] = {"level": rows[0][0], "summary": rows[0][1]}
    except Exception:
        pass
    try:
        rows = _safe(cur,
            "SELECT waiting_type, waiting_for FROM waiting_cases "
            "WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
        if rows:
            ctx["waiting"] = {"type": rows[0][0], "for": rows[0][1]}
    except Exception:
        pass
    return ctx


def mentor_context_text(ctx: Dict[str, Any]) -> str:
    if not ctx:
        return ""
    parts = []
    if ctx.get("gospel"):
        g = ctx["gospel"]
        parts.append(f"最近福音诊断：偶像={de.IDOLS.get(g.get('idol'), {}).get('zh', g.get('idol') or '—')}；"
                     f"上次行动={g.get('action') or '—'}")
    if ctx.get("checkup"):
        c = ctx["checkup"]
        parts.append(f"最近属灵体检：{c.get('level') or ''} {c.get('summary') or ''}".strip())
    if ctx.get("waiting"):
        w = ctx["waiting"]
        parts.append(f"正在等候：{w.get('for') or ''}（{w.get('type') or ''}）".strip())
    return "（牧养记忆，供你连续地牧养，不必复述）：" + "；".join(p for p in parts if p)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Neo4j 图谱同步与查询（接既有真 graph_layer，未配置则静默降级）
# ─────────────────────────────────────────────────────────────────────────────

def _neo4j():
    try:
        try:
            from backend.graph_layer import get_neo4j
        except Exception:
            from graph_layer import get_neo4j  # type: ignore
        conn = get_neo4j()
        return conn if conn and conn.is_connected() else None
    except Exception:
        return None


def sync_graph(email: str, result: Dict[str, Any],
               relationships: Optional[List[Dict[str, Any]]] = None) -> bool:
    """把门徒塑造结果写进 Neo4j：Person→State，Person→Idol，Person→FalseBelief，
    Person→DISCIPLES→Person。未连接则返回 False（不报错）。"""
    conn = _neo4j()
    if not conn:
        return False
    try:
        conn.run(
            "MERGE (p:DisciplePerson {email:$email}) "
            "SET p.state=$state, p.ci=$ci, p.updated=timestamp()",
            email=email, state=result.get("spiritual_state", ""),
            ci=float(result.get("christlikeness_index", 0)))
        top_idol = result.get("top_idol")
        if top_idol:
            conn.run(
                "MERGE (p:DisciplePerson {email:$email}) "
                "MERGE (i:Idol {key:$idol}) "
                "MERGE (p)-[r:STRUGGLES_WITH]->(i) SET r.updated=timestamp()",
                email=email, idol=top_idol)
        for fb in (result.get("engines", {}).get("faith", {}).get("false_beliefs") or [])[:5]:
            if fb:
                conn.run(
                    "MERGE (p:DisciplePerson {email:$email}) "
                    "MERGE (b:Belief {content:$c}) SET b.truth_level='false' "
                    "MERGE (p)-[:HAS_BELIEF]->(b)",
                    email=email, c=str(fb)[:200])
        for rel in (relationships or []):
            dn = (rel.get("disciple_email") or rel.get("disciple_name") or "").strip()
            if not dn:
                continue
            conn.run(
                "MERGE (p:DisciplePerson {email:$email}) "
                "MERGE (d:DisciplePerson {email:$dn}) "
                "MERGE (p)-[r:DISCIPLES]->(d) SET r.type=$t",
                email=email, dn=dn, t=rel.get("relationship_type", "DISCIPLER"))
        return True
    except Exception:
        return False


def graph_insights(email: str) -> Dict[str, Any]:
    """查询：当前偶像、复制链深度、影响的人数。未连接返回 enabled=False。"""
    conn = _neo4j()
    if not conn:
        return {"enabled": False, "insights": []}
    out: Dict[str, Any] = {"enabled": True, "insights": []}
    try:
        rows = conn.run(
            "MATCH (p:DisciplePerson {email:$email})-[:STRUGGLES_WITH]->(i:Idol) "
            "RETURN i.key AS idol", email=email)
        idols = [r.get("idol") for r in rows if r.get("idol")]
        if idols:
            out["insights"].append({"type": "idols", "label": "图谱中的偶像",
                                    "value": [de.IDOLS.get(k, {}).get("zh", k) for k in idols]})
        rows = conn.run(
            "MATCH path=(p:DisciplePerson {email:$email})-[:DISCIPLES*1..5]->(d:DisciplePerson) "
            "RETURN length(path) AS depth ORDER BY depth DESC LIMIT 1", email=email)
        if rows:
            out["insights"].append({"type": "depth", "label": "门徒复制链深度",
                                    "value": rows[0].get("depth", 0)})
        rows = conn.run(
            "MATCH (p:DisciplePerson {email:$email})-[:DISCIPLES*1..5]->(d:DisciplePerson) "
            "RETURN count(DISTINCT d) AS reach", email=email)
        if rows:
            out["insights"].append({"type": "reach", "label": "影响的门徒总数",
                                    "value": rows[0].get("reach", 0)})
    except Exception:
        pass
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 4. 周 / 月复盘（聚合 disciple_assessments）
# ─────────────────────────────────────────────────────────────────────────────

def _aggregate_assessments(cur, email: str, days: int) -> Dict[str, Any]:
    rows = _safe(cur,
        "SELECT christlikeness_index, growth_edge, top_idol, spiritual_state, report, created_at "
        "FROM disciple_assessments WHERE email=%s AND created_at >= NOW() - (%s || ' days')::interval "
        "ORDER BY created_at ASC", (email, str(days)))
    if not rows:
        return {"has_data": False, "count": 0}

    cis = [float(r[0]) for r in rows if r[0] is not None]
    edges = [r[1] for r in rows if r[1]]
    idols = [r[2] for r in rows if r[2]]
    states = [r[3] for r in rows if r[3]]

    # 维度均值（从 report.dimensions）
    dim_sum: Dict[str, float] = {k: 0.0 for k in de.DIM_KEYS}
    dim_n = 0
    for r in rows:
        rep = r[4] if isinstance(r[4], dict) else (json.loads(r[4]) if r[4] else {})
        dims = (rep or {}).get("dimensions") or {}
        if dims:
            dim_n += 1
            for k in de.DIM_KEYS:
                dim_sum[k] += float(dims.get(k, 0))
    dim_avg = {k: round(dim_sum[k] / dim_n, 1) for k in de.DIM_KEYS} if dim_n else {}

    def _mode(xs):
        return max(set(xs), key=xs.count) if xs else None

    ci_trend = round(cis[-1] - cis[0], 1) if len(cis) >= 2 else 0.0
    return {
        "has_data": True, "count": len(rows),
        "ci_avg": round(sum(cis) / len(cis), 1) if cis else 0,
        "ci_trend": ci_trend,
        "dim_avg": dim_avg,
        "weakest": (min(dim_avg, key=dim_avg.get) if dim_avg else None),
        "strongest": (max(dim_avg, key=dim_avg.get) if dim_avg else None),
        "dominant_idol": _mode(idols),
        "dominant_edge": _mode(edges),
        "latest_state": states[-1] if states else None,
    }


_REVIEW_DIMS = ["faith", "hope", "love", "obedience", "character", "mission", "multiplication"]


def make_review(cur, email: str, kind: str, settings: Any = None,
                use_ai: bool = True) -> Dict[str, Any]:
    """kind = 'weekly' | 'monthly'。聚合 + 可选 AI 牧养式总结。"""
    days = 7 if kind == "weekly" else 30
    agg = _aggregate_assessments(cur, email, days)
    if not agg.get("has_data"):
        return {"ok": True, "kind": kind, "has_data": False,
                "message": f"最近{days}天还没有评估记录，先去写一篇反思吧。"}

    weakest = agg.get("weakest")
    nxt = None
    if agg.get("latest_state"):
        nxt = de.next_state(agg["latest_state"])

    summary = (f"最近{days}天共 {agg['count']} 次反思，像基督指数均值 {agg['ci_avg']}"
               f"（{'↑' if agg['ci_trend'] > 0 else '↓' if agg['ci_trend'] < 0 else '→'}{abs(agg['ci_trend'])}）。"
               f"最稳的是「{de.DIM_ZH.get(agg.get('strongest'), '—')}」，"
               f"成长边界在「{de.DIM_ZH.get(weakest, '—')}」。")
    invitation = de._default_obedience_step(weakest or "faith", agg.get("dominant_idol"))
    scripture = {"ref": "腓立比书 1:6",
                 "text": "那在你们心里动了善工的，必成全这工，直到耶稣基督的日子。"}

    if use_ai:
        try:
            try:
                from backend.waiting_engine import call_ai_provider
            except Exception:
                from waiting_engine import call_ai_provider  # type: ignore
            msgs = [
                {"role": "system", "content": de.MENTOR_SYSTEM_PROMPT +
                 " 你在写一段温柔的牧养式复盘，不定罪、不堆术语。"},
                {"role": "user", "content":
                 f"这是某门徒最近{days}天的塑造聚合数据：{json.dumps(agg, ensure_ascii=False)}。"
                 "请用简体中文输出 JSON：{\"summary\":\"两三句神这段时间在他身上的工作\","
                 "\"invitation\":\"一个具体的下一步邀请\",\"scripture\":{\"ref\":\"\",\"text\":\"\"}}"}
            ]
            ai = call_ai_provider(msgs, settings=settings)
            if ai:
                summary = ai.get("summary") or summary
                invitation = ai.get("invitation") or invitation
                if isinstance(ai.get("scripture"), dict) and ai["scripture"].get("text"):
                    scripture = {"ref": ai["scripture"].get("ref", ""), "text": ai["scripture"]["text"]}
        except Exception:
            pass

    return {
        "ok": True, "kind": kind, "has_data": True, "days": days,
        "count": agg["count"], "ci_avg": agg["ci_avg"], "ci_trend": agg["ci_trend"],
        "dim_avg": agg.get("dim_avg", {}),
        "strongest": agg.get("strongest"), "weakest": weakest,
        "dominant_idol": agg.get("dominant_idol"),
        "latest_state": agg.get("latest_state"), "next_state": nxt,
        "summary": summary, "invitation": invitation, "scripture": scripture,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. 领域事件流
# ─────────────────────────────────────────────────────────────────────────────

def log_event(cur, aggregate_type: str, aggregate_id: str,
              event_type: str, payload: Dict[str, Any]) -> None:
    """写一条 domain_events。失败静默（事件流是增益，不能拖垮主流程）。"""
    try:
        try:
            from psycopg2.extras import Json
            pj = Json(payload)
        except Exception:
            pj = json.dumps(payload)
        cur.execute(
            "INSERT INTO domain_events (aggregate_type, aggregate_id, event_type, payload) "
            "VALUES (%s,%s,%s,%s)",
            (aggregate_type, str(aggregate_id), event_type, pj))
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
# 6. 事件消费者 (event consumer) — domain_events → 规则 Agent → agent_runs
# ─────────────────────────────────────────────────────────────────────────────

def _state_zh(k: str) -> str:
    return de.STATE_BY_KEY.get(k, {}).get("zh", k or "")


def _count_assess(cur, email: str, days: int) -> int:
    rows = _safe(cur,
        "SELECT COUNT(*) FROM disciple_assessments WHERE email=%s "
        "AND created_at >= NOW() - (%s || ' days')::interval", (email, str(days)))
    return int(rows[0][0]) if rows and rows[0] else 0


def _recent_agent(cur, email: str, agent: str, days: int) -> bool:
    rows = _safe(cur,
        "SELECT 1 FROM agent_runs WHERE email=%s AND agent_name=%s "
        "AND created_at >= NOW() - (%s || ' days')::interval LIMIT 1", (email, agent, str(days)))
    return bool(rows)


def _insert_agent_run(cur, email, agent, etype, inp, out) -> None:
    try:
        cur.execute(
            "INSERT INTO agent_runs (email, agent_name, event_type, input_payload, output_payload) "
            "VALUES (%s,%s,%s,%s,%s)",
            (email, agent, etype, _AsJson(inp), _AsJson(out)))
    except Exception:
        pass


def _AsJson(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        return json.dumps(obj)


def _run_agents(cur, email: str, etype: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """对一条领域事件运行规则 Agent，产出 0..n 条反应(里程碑/提醒)。"""
    out: List[Dict[str, Any]] = []
    if etype == "SpiritualStateChanged":
        frm, to = payload.get("from"), payload.get("to")
        up = de.STATE_ORDER.get(to, 0) > de.STATE_ORDER.get(frm, 0)
        out.append({"agent": "StateTransitionAgent", "kind": "milestone",
                    "title": "属灵进阶" if up else "状态调整",
                    "body": f"{_state_zh(frm)} → {_state_zh(to)}",
                    "up": up})
    elif etype == "IdolDetected":
        if payload.get("risk") in ("HIGH", "CRITICAL"):
            idol = payload.get("idol")
            out.append({"agent": "IdolWatchAgent", "kind": "nudge",
                        "title": "偶像警戒",
                        "body": f"{de.IDOLS.get(idol, {}).get('zh', idol)}风险偏高："
                                f"{de.IDOLS.get(idol, {}).get('remedy', '')}"})
    elif etype == "ReflectionAssessed":
        c7 = _count_assess(cur, email, 7)
        c30 = _count_assess(cur, email, 30)
        if c7 >= 5 and not _recent_agent(cur, email, "CadenceAgent", 6):
            out.append({"agent": "CadenceAgent", "kind": "nudge",
                        "title": "周复盘就绪",
                        "body": f"最近 7 天已有 {c7} 次反思，去看看本周复盘吧。",
                        "review": "weekly"})
        elif c30 >= 18 and not _recent_agent(cur, email, "CadenceAgent", 20):
            out.append({"agent": "CadenceAgent", "kind": "nudge",
                        "title": "月复盘就绪",
                        "body": f"本月已有 {c30} 次反思，去看看本月复盘吧。",
                        "review": "monthly"})
    return out


def process_user_events(cur, email: str, limit: int = 50) -> List[Dict[str, Any]]:
    """消费该用户未处理的领域事件：跑规则 Agent → 写 agent_runs → 标记 processed。
    返回本轮产生的反应列表（供前端展示 nudge/里程碑）。失败静默。"""
    rows = _safe(cur,
        "SELECT id, event_type, payload FROM domain_events "
        "WHERE aggregate_id=%s AND processed=FALSE ORDER BY created_at ASC LIMIT %s",
        (email, limit))
    if not rows:
        return []
    reactions: List[Dict[str, Any]] = []
    done_ids: List[int] = []
    for ev_id, etype, payload in rows:
        p = payload if isinstance(payload, dict) else (json.loads(payload) if payload else {})
        try:
            for run in _run_agents(cur, email, etype, p):
                _insert_agent_run(cur, email, run["agent"], etype, p, run)
                reactions.append(run)
            done_ids.append(ev_id)
        except Exception:
            pass
    if done_ids:
        try:
            cur.execute("UPDATE domain_events SET processed=TRUE, processed_at=NOW() "
                        "WHERE id = ANY(%s)", (done_ids,))
        except Exception:
            pass
    return reactions


def get_milestones(cur, email: str, limit: int = 30) -> List[Dict[str, Any]]:
    """属灵里程碑/提醒时间线：从 agent_runs 读取（状态进阶、偶像警戒、复盘提醒）。"""
    rows = _safe(cur,
        "SELECT agent_name, event_type, output_payload, created_at FROM agent_runs "
        "WHERE email=%s ORDER BY created_at DESC LIMIT %s", (email, limit))
    items = []
    for agent, etype, out, ts in rows:
        o = out if isinstance(out, dict) else (json.loads(out) if out else {})
        items.append({"agent": agent, "event_type": etype,
                      "kind": o.get("kind", ""), "title": o.get("title", ""),
                      "body": o.get("body", ""), "up": o.get("up"),
                      "review": o.get("review"),
                      "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts)})
    return items
