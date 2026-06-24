"""
diagnosis_agent.py — Advanced Batch · Module 1 (reference real agent)

Demonstrates the full production path every structured agent should follow:

    create agent_run  →  generate_json(schema)  →  TheologicalSafetyService.review
                      →  deterministic fallback on failure/block
                      →  finish agent_run (DONE/FAILED) + provider events

Crisis-safety: if the user's words contain self-harm / danger signals, the
diagnosis risk is floored at high/critical and pastor attention is forced ON —
the model can raise risk but never lower it below what the words demand.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, Optional

try:
    from backend import llm_provider as _llm  # type: ignore
except Exception:  # pragma: no cover
    import llm_provider as _llm
try:
    from backend import theological_safety as _safety  # type: ignore
except Exception:  # pragma: no cover
    import theological_safety as _safety
try:
    from backend.llm_schemas import DiagnosisAgentOutput  # type: ignore
except Exception:  # pragma: no cover
    from llm_schemas import DiagnosisAgentOutput

DIAGNOSIS_SYSTEM_PROMPT = """你是 Spiritual Diagnosis Agent。
你的任务：根据用户的属灵日志、每日打卡、操练记录、历史属灵画像，生成温柔、诚实、福音中心的属灵诊断。
你必须识别：表层情绪、重复行为模式、底层谎言、可能的偶像、罪与试探模式、与神关系状态、群体连接状态、苦难回应状态、需要真实人介入的风险。
你必须避免：羞辱用户、简化痛苦、用"信心不足"解释一切、以行为表现定义用户价值、给医学诊断、替代牧者判断。
输出必须是严格 JSON，符合 DiagnosisAgentOutput schema。
如果出现自伤、自杀、不想活、活不下去、没有希望、被暴力威胁、成瘾失控、严重精神崩溃等信号：
risk_level 必须是 high 或 critical，并在 findings 中标记 requires_pastor_attention = true，
且 recommended_community_action 必须指向真实的人（牧者/家人/可信同伴/专业帮助/当地紧急服务），不可只给经文。
AI 不是牧者，绝不声称替代教会、小组或牧者。"""

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _user_text(payload: Dict[str, Any]) -> str:
    parts = []
    for v in (payload or {}).values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v)
    return "\n".join(parts)


def run_diagnosis(
    email: str,
    payload: Dict[str, Any],
    *,
    get_db: Optional[Callable] = None,
    release_db: Optional[Callable] = None,
) -> Dict[str, Any]:
    """Run the diagnosis agent and return a UI-safe result dict."""
    run_id = _start_run(email, payload, get_db, release_db)

    # Floor risk at whatever the user's words demand — model may only raise it.
    crisis = _safety.detect_crisis(_user_text(payload))
    floor = str(crisis["risk_level"])

    try:
        out = _llm.generate_json(
            DIAGNOSIS_SYSTEM_PROMPT, payload, DiagnosisAgentOutput,
            email=email, agent_run_id=run_id, agent_name="SpiritualDiagnosisAgent", skill_name="diagnosis",
        )
        data = out.model_dump()
    except Exception:
        # Deterministic, schema-valid fallback (never leave the user with nothing).
        data = _llm.MockLLMProvider().structured(DiagnosisAgentOutput, payload)
        data = DiagnosisAgentOutput.model_validate(data).model_dump()

    data = _enforce_floor(data, floor)

    review = _safety.TheologicalSafetyService().review(
        json.dumps(data, ensure_ascii=False), agent_name="SpiritualDiagnosisAgent",
        skill_name="diagnosis", email=email, agent_run_id=run_id, user_risk_hint=floor,
    )
    if not review.ok:  # blocked content -> replace with a safe deterministic version
        data = _enforce_floor(
            DiagnosisAgentOutput.model_validate(
                _llm.MockLLMProvider().structured(DiagnosisAgentOutput, payload)
            ).model_dump(), floor)

    result = {
        "ok": True,
        "diagnosis": data,
        "risk_level": data["risk_level"],
        "requires_real_person": data["risk_level"] in ("high", "critical"),
        "safety_verdict": review.verdict,
        "disclaimer": "本辨识仅为辅助，不能替代牧者、辅导员或专业帮助；如有危机请联系真实的人或当地紧急服务。",
    }
    _finish_run(run_id, result, get_db, release_db)
    return result


def _enforce_floor(data: Dict[str, Any], floor: str) -> Dict[str, Any]:
    if _RISK_ORDER.get(data.get("risk_level", "low"), 0) < _RISK_ORDER.get(floor, 0):
        data["risk_level"] = floor
    if floor in ("high", "critical"):
        for f in data.get("findings", []):
            f["requires_pastor_attention"] = True
            if _RISK_ORDER.get(f.get("risk_level", "low"), 0) < _RISK_ORDER.get(floor, 0):
                f["risk_level"] = floor
            if not f.get("recommended_community_action"):
                f["recommended_community_action"] = "尽快联系牧者、家人或可信的属灵同伴；若有立即危险请联系当地紧急服务。"
    return data


# ── agent_runs bookkeeping (best-effort) ─────────────────────────────────────
def _start_run(email, payload, get_db, release_db) -> Optional[int]:
    if get_db is None:
        return None
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO agent_runs (email, agent_name, event_type, input_payload, status) "
                "VALUES (%s,%s,%s,%s::jsonb,'RUNNING') RETURNING id",
                (email, "SpiritualDiagnosisAgent", "diagnosis.request",
                 json.dumps(_safety_redact(payload))),
            )
            rid = cur.fetchone()[0]
        conn.commit()
        return rid
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return None
    finally:
        if conn is not None and release_db is not None:
            release_db(conn)


def _finish_run(run_id, result, get_db, release_db) -> None:
    if get_db is None or run_id is None:
        return
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_runs SET status='DONE', output_payload=%s::jsonb WHERE id=%s "
                "AND status <> 'FAILED'",
                (json.dumps({"risk_level": result["risk_level"],
                             "safety_verdict": result["safety_verdict"]}), run_id),
            )
        conn.commit()
    except Exception:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
    finally:
        if conn is not None and release_db is not None:
            release_db(conn)


def _safety_redact(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Store only a redacted preview of free-text in agent_runs.input_payload.
    return _llm._redact(payload)
