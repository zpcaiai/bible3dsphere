"""
diagnosis_hub.py — 统一诊断适配层（adapter）

既有领域引擎（gospel / checkup / disciple / worldview）在产出结果后，调用本模块把结果
归一化写入 diagnostic_sessions + diagnostic_findings，形成一个可统一查询的诊断面。
不替换任何既有逻辑；全部 best-effort（失败不影响主流程）。email 为用户键。

DB 访问：优先用 init_diagnosis_hub() 注入的 get_db/release_db；否则回退 core.deps。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_state: Dict[str, Any] = {}


def init_diagnosis_hub(get_db, release_db) -> None:
    _state["get_db"] = get_db
    _state["release_db"] = release_db


def _acquire():
    if _state.get("get_db"):
        return _state["get_db"](), _state.get("release_db")
    # 回退到 core.deps（启动时已初始化）
    try:
        from core.deps import acquire_conn, release_conn
        return acquire_conn(), release_conn
    except Exception:
        try:
            from backend.core.deps import acquire_conn, release_conn
            return acquire_conn(), release_conn
        except Exception:
            return None, None


def _Json(obj):
    try:
        from psycopg2.extras import Json
        return Json(obj)
    except Exception:
        import json as _json
        return _json.dumps(obj)


def record_diagnosis(email: str, source_engine: str, *, source_id: Optional[str] = None,
                     session_type: str = "diagnosis", primary_theme: Optional[str] = None,
                     risk_level: str = "low", summary: Optional[str] = None,
                     raw: Optional[dict] = None,
                     findings: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """写入一条统一诊断 session + 其 findings。返回 session_id 或 None（best-effort）。"""
    if not email:
        return None
    conn, release = _acquire()
    if conn is None:
        return None
    session_id = None
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO diagnostic_sessions "
                "(email, source_engine, source_id, session_type, primary_theme, risk_level, summary, raw) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (email, source_engine, source_id, session_type, primary_theme,
                 risk_level, (summary or "")[:2000], _Json(raw or {})),
            )
            session_id = cur.fetchone()[0]
            for f in (findings or []):
                cur.execute(
                    "INSERT INTO diagnostic_findings "
                    "(session_id, email, category, finding_type, title, description, "
                    " possible_root, gospel_truth, scripture_anchors, severity, confidence, risk_level) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (session_id, email, f.get("category", "general"), f.get("finding_type", ""),
                     (f.get("title") or "发现")[:300], f.get("description", ""),
                     f.get("possible_root", ""), f.get("gospel_truth", ""),
                     _Json(f.get("scripture_anchors", [])), f.get("severity"),
                     f.get("confidence"), f.get("risk_level", risk_level)),
                )
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        session_id = None
    finally:
        if release:
            release(conn)
    try:
        import formation_events as _fe
        _sev = {"red": "red", "high": "red", "amber": "amber", "medium": "amber"}.get(str(risk_level or "").lower(), "green")
        _fe.record_event(email, source_engine, "diagnosis", domain=primary_theme,
                         title=(primary_theme or "诊断"), summary=summary, severity=_sev, ref_id=session_id)
    except Exception:
        pass
    return session_id


# ── 领域结果 → 统一 findings 的适配器 ─────────────────────────────────────────

def record_from_gospel(email: str, source_id: Optional[str], result: Dict[str, Any]) -> Optional[str]:
    """福音诊断（钟马田）→ 统一诊断。result 含 idol_type/idol_name/unbelief/gospel_truth/scripture。"""
    idol = result.get("idol_name") or result.get("idol_type") or ""
    scr = result.get("scripture") or {}
    anchors = [scr.get("ref")] if isinstance(scr, dict) and scr.get("ref") else []
    findings = [{
        "category": "identity",
        "finding_type": "false_belief",
        "title": (f"福音诊断：{idol}" if idol else "福音诊断"),
        "description": result.get("unbelief", "") or result.get("emotion", ""),
        "possible_root": result.get("idol_type", ""),
        "gospel_truth": result.get("gospel_truth", ""),
        "scripture_anchors": anchors,
        "severity": 3,
        "confidence": 0.7,
        "risk_level": "low",
    }]
    return record_diagnosis(
        email, "gospel", source_id=source_id,
        primary_theme=(idol or "福音诊断"),
        summary=result.get("gospel_truth", ""),
        raw={k: result.get(k) for k in ("emotion", "idol_type", "unbelief") if k in result},
        findings=findings,
    )


def record_from_checkup(email: str, source_id: Optional[str], result: Dict[str, Any]) -> Optional[str]:
    """属灵低潮体检 → 统一诊断。result 含 index/level/summary。"""
    level = result.get("level", "") or "属灵体检"
    findings = [{
        "category": "spiritual_vitality",
        "finding_type": "low_point",
        "title": level,
        "description": result.get("summary", ""),
        "gospel_truth": result.get("gospel_truth", ""),
        "scripture_anchors": result.get("scripture_anchors", []) or [],
        "severity": 3,
        "confidence": 0.6,
        "risk_level": "low",
    }]
    return record_diagnosis(
        email, "checkup", source_id=source_id,
        primary_theme=level,
        summary=result.get("summary", ""),
        raw={"index": result.get("index"), "level": result.get("level")},
        findings=findings,
    )


def record_from_disciple(email: str, source_id: Optional[str], result: Dict[str, Any]) -> Optional[str]:
    """门徒成长评估 → 统一诊断。result 含 spiritual_state/christlikeness_index/growth_edge/top_idol/risk_level。"""
    risk = result.get("risk_level", "low") or "low"
    growth = result.get("growth_edge", "") or ""
    state = result.get("spiritual_state", "") or ""
    ci = result.get("christlikeness_index")
    findings: List[Dict[str, Any]] = []
    top_idol = result.get("top_idol")
    if top_idol:
        findings.append({
            "category": "idolatry", "finding_type": "idol",
            "title": f"主导偶像：{top_idol}", "description": growth,
            "severity": 4 if risk in ("high", "critical") else 3,
            "confidence": 0.7, "risk_level": risk,
        })
    findings.append({
        "category": "formation", "finding_type": "growth_edge",
        "title": (growth or "成长焦点"), "description": f"属灵状态：{state}",
        "severity": 3, "confidence": 0.7, "risk_level": risk,
    })
    return record_diagnosis(
        email, "disciple", source_id=source_id,
        primary_theme=(growth or state or "门徒评估"), risk_level=risk,
        summary=f"属灵状态：{state}；基督样式指数：{ci}",
        raw={"spiritual_state": state, "christlikeness_index": ci, "top_idol": top_idol},
        findings=findings,
    )


_WV_RISK = {"green": "low", "yellow": "medium", "red": "high", "imminent": "critical"}


def record_from_worldview(email: str, source_id: Optional[str], result: Dict[str, Any]) -> Optional[str]:
    """世界观诊断 → 统一诊断。result 含 diagnosis{...}/idols/crisis。危机已被上游早退，不在此处理。"""
    diag = result.get("diagnosis") or {}
    risk = _WV_RISK.get((result.get("crisis") or {}).get("riskLevelRaw", "green"), "low")
    findings: List[Dict[str, Any]] = []
    for b in (diag.get("extractedBeliefs") or [])[:3]:
        conf = b.get("confidence")
        sev = max(1, min(5, round((conf if conf is not None else 0.5) * 5)))
        findings.append({
            "category": b.get("domain", "worldview") or "worldview",
            "finding_type": "worldview_belief",
            "title": (b.get("beliefStatement", "") or "世界观信念")[:300],
            "description": (b.get("evidence", "") or "")[:1000],
            "gospel_truth": b.get("biblicalTruth", "") or "",
            "scripture_anchors": b.get("scriptureRefs", []) or [],
            "severity": sev, "confidence": conf, "risk_level": risk,
        })
    idols = (result.get("idols") or {}).get("suggestedTargets", []) or []
    if idols:
        first = idols[0]
        name = first.get("name") if isinstance(first, dict) else str(first)
        findings.append({
            "category": "idolatry", "finding_type": "idol",
            "title": f"世界观偶像：{name}", "description": "",
            "severity": 3, "confidence": 0.6, "risk_level": risk,
        })
    if not findings:
        findings.append({"category": "worldview", "finding_type": "summary",
                         "title": "世界观诊断", "description": diag.get("profileSummary", ""),
                         "severity": 2, "confidence": 0.5, "risk_level": risk})
    return record_diagnosis(
        email, "worldview", source_id=source_id,
        primary_theme=(diag.get("currentGrowthFocus") or "世界观诊断"), risk_level=risk,
        summary=diag.get("profileSummary", ""),
        raw={"overallScore": diag.get("overallScore"),
             "detectedDomains": diag.get("detectedDomains", [])},
        findings=findings,
    )
