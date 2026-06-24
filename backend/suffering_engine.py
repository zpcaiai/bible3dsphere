"""
suffering_engine.py — Advanced Batch · Module 6
Suffering Theology & Crisis Linkage.

Pipeline:
    user text
      → detect_crisis (floors the risk; the model may raise but never lower it)
      → SufferingTheologyAgent (generate_json, schema-validated, safety-reviewed)
      → low/medium : suffering_case + lament_prayer + suffering_care_plan
      → high/critical : ALSO crisis_event + care_signal escalation, and the
        response MUST name real-human next steps (never scripture-only).

``analyze_suffering`` is pure (no DB) so it is unit-testable under ``-m no_db``.
``run_and_persist`` adds best-effort persistence + crisis/care linkage.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, List, Optional

try:
    from backend import llm_provider as _llm  # type: ignore
except Exception:  # pragma: no cover
    import llm_provider as _llm
try:
    from backend import theological_safety as _safety  # type: ignore
except Exception:  # pragma: no cover
    import theological_safety as _safety
try:
    from backend.llm_schemas import SufferingAgentOutput  # type: ignore
except Exception:  # pragma: no cover
    from llm_schemas import SufferingAgentOutput

SUFFERING_SYSTEM_PROMPT = """你是 Suffering Theology & Care Agent。
你的任务：根据用户的痛苦、危机、哀伤、失败、疑惑或长期压力，生成符合圣经、温柔真实、不过度简化的属灵关怀建议。
先判断状态（普通压力/属灵干旱/哀伤/失败与羞耻/关系破裂/长期苦难/信仰疑惑/绝望危机/自伤风险/家庭暴力或安全威胁）。
如果出现危机：risk_level 必须 high 或 critical；必须建议联系真实可信的人、牧者、家人、专业帮助或当地紧急服务；
不可只给经文；不可把危机归因为不够属灵。
如果不是危机：生成苦难类型、神学主题、可以哀哭的空间、合适经文、祷告引导、群体陪伴建议、本周一个小行动、是否建议专业帮助。
严格输出 JSON，符合 SufferingAgentOutput schema。禁止：'你痛苦是因为你信心不足'、'不要难过，基督徒应该喜乐'、
'只要祷告就会立刻好'、'AI 可以替代牧者陪你走过危机'、'苦难一定是某个具体罪导致的'。AI 不是牧者。"""

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_RISK_TO_CRISIS = {"low": "green", "medium": "yellow", "high": "orange", "critical": "red"}

_DEFAULT_REAL_PERSON_ACTIONS = [
    "现在就联系一位你信任的真实的人（牧者、家人或可信的属灵同伴）。",
    "若你有立即的危险或想伤害自己，请联系当地紧急服务或危机热线。",
    "邀请一位同伴今天陪你，不要独自一人。",
]


def analyze_suffering(email: str, content: str, *, source_type: str = "reflection_log",
                      source_id: Optional[str] = None, agent_run_id: Optional[int] = None
                      ) -> Dict[str, Any]:
    """Return the structured suffering analysis + linkage decisions (no DB)."""
    floor = str(_safety.detect_crisis(content)["risk_level"])
    payload = {"content": content, "source_type": source_type}
    try:
        out = _llm.generate_json(
            SUFFERING_SYSTEM_PROMPT, payload, SufferingAgentOutput,
            email=email, agent_run_id=agent_run_id, agent_name="SufferingTheologyAgent", skill_name="suffering",
        ).model_dump()
    except Exception:
        out = SufferingAgentOutput.model_validate(
            _llm.MockLLMProvider().structured(SufferingAgentOutput, payload)
        ).model_dump()

    # Floor the risk — words of danger win over a calmer model.
    if _RISK_ORDER.get(out.get("risk_level", "low"), 0) < _RISK_ORDER.get(floor, 0):
        out["risk_level"] = floor

    is_crisis = out["risk_level"] in ("high", "critical")
    if is_crisis:
        out["professional_help_recommended"] = out["risk_level"] == "critical" or out.get("professional_help_recommended", False)
        out["community_support_needed"] = True
        # NEVER scripture-only in a crisis — guarantee real-human steps.
        if not out.get("real_person_actions"):
            out["real_person_actions"] = list(_DEFAULT_REAL_PERSON_ACTIONS)

    # Safety review of the user-visible content.
    review = _safety.TheologicalSafetyService().review(
        json.dumps(out, ensure_ascii=False), agent_name="SufferingTheologyAgent",
        skill_name="suffering", email=email, agent_run_id=agent_run_id, user_risk_hint=floor,
    )
    if not review.ok:
        out = SufferingAgentOutput.model_validate(
            _llm.MockLLMProvider().structured(SufferingAgentOutput, payload)
        ).model_dump()
        out["risk_level"] = floor
        if is_crisis and not out.get("real_person_actions"):
            out["real_person_actions"] = list(_DEFAULT_REAL_PERSON_ACTIONS)

    return {
        "analysis": out,
        "risk_level": out["risk_level"],
        "is_crisis": is_crisis,
        "requires_real_person": is_crisis,
        "real_person_actions": out.get("real_person_actions", []),
        "safety_verdict": review.verdict,
        "disclaimer": "AI 不是牧者，不能替代教会、牧者或专业帮助；如有危机请立刻联系真实的人或当地紧急服务。",
    }


def run_and_persist(email: str, content: str, *, source_type: str = "reflection_log",
                    source_id: Optional[str] = None, get_db: Optional[Callable] = None,
                    release_db: Optional[Callable] = None) -> Dict[str, Any]:
    run_id = _start_run(email, content, get_db, release_db)
    result = analyze_suffering(email, content, source_type=source_type,
                               source_id=source_id, agent_run_id=run_id)
    out = result["analysis"]

    if get_db is None:
        return result

    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            case_id = _insert_case(cur, email, content, source_type, source_id, out)
            result["suffering_case_id"] = case_id

            if out.get("lament_needed") or out.get("guided_prayer"):
                result["lament_prayer_id"] = _insert_lament(cur, email, case_id, content, out)

            if out.get("care_plan"):
                result["care_plan_id"] = _insert_care_plan(cur, email, case_id, out)

            if result["is_crisis"]:
                crisis_id = _insert_crisis_event(cur, email, content, out)
                result["crisis_event_id"] = crisis_id
                cur.execute(
                    "UPDATE suffering_cases SET crisis_event_id=%s, should_link_crisis_system=TRUE WHERE id=%s",
                    (crisis_id, case_id),
                )
                signal_id = _create_care_signal(cur, email, out, case_id)
                if signal_id:
                    result["care_signal_id"] = signal_id
        conn.commit()
        _finish_run(run_id, result, get_db, release_db)
    except Exception as exc:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        result["persist_error"] = str(exc)[:200]
    finally:
        if conn is not None and release_db is not None:
            release_db(conn)
    return result


# ── persistence helpers ──────────────────────────────────────────────────────
def _insert_case(cur, email, content, source_type, source_id, out) -> str:
    cur.execute(
        """
        INSERT INTO suffering_cases
          (email, source_type, source_id, suffering_text, case_type, title, summary,
           risk_level, suffering_stage, theological_theme, lament_needed,
           community_support_needed, professional_help_recommended,
           recommended_scripture_refs, lament_prayer, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,'open')
        RETURNING id
        """,
        (email, source_type, source_id, content, out.get("case_type"),
         out.get("case_type") or "苦难关怀", out.get("summary"), out["risk_level"],
         out.get("suffering_stage"), out.get("theological_theme"),
         bool(out.get("lament_needed")), bool(out.get("community_support_needed")),
         bool(out.get("professional_help_recommended")),
         json.dumps(out.get("scripture_anchors", [])), out.get("guided_prayer")),
    )
    return str(cur.fetchone()[0])


def _insert_lament(cur, email, case_id, content, out) -> str:
    cur.execute(
        """
        INSERT INTO lament_prayers
          (email, suffering_case_id, title, raw_lament, guided_prayer, scripture_anchors)
        VALUES (%s,%s,%s,%s,%s,%s::jsonb)
        RETURNING id
        """,
        (email, case_id, "我的哀歌", content, out.get("guided_prayer"),
         json.dumps(out.get("scripture_anchors", []))),
    )
    return str(cur.fetchone()[0])


def _insert_care_plan(cur, email, case_id, out) -> str:
    cp = out["care_plan"]
    cur.execute(
        """
        INSERT INTO suffering_care_plans
          (email, suffering_case_id, title, description, plan_type, scripture_path,
           prayer_path, community_actions, professional_help_notes, duration_days, status)
        VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,'active')
        RETURNING id
        """,
        (email, case_id, cp.get("title", "苦难关怀计划"), out.get("summary", ""),
         out.get("suffering_stage") or "lament", json.dumps(cp.get("scripture_path", [])),
         json.dumps(cp.get("prayer_path", [])), json.dumps(cp.get("community_actions", [])),
         ("建议寻求专业帮助。" if out.get("professional_help_recommended") else None),
         int(cp.get("duration_days", 14))),
    )
    return str(cur.fetchone()[0])


def _insert_crisis_event(cur, email, content, out) -> str:
    crisis_id = str(uuid.uuid4())
    risk = _RISK_TO_CRISIS.get(out["risk_level"], "yellow")
    workflow = "red_emergency" if out["risk_level"] == "critical" else "orange_safety_plan"
    matched = _safety.detect_crisis(content)["matched"]
    cur.execute(
        """
        INSERT INTO crisis_events
          (id, user_id, risk_level, risk_types, evidence, triggering_message,
           system_response, workflow_started)
        VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
        """,
        (crisis_id, email, risk, json.dumps(["suffering"]),
         json.dumps([{"matched": matched}]),
         "[redacted]", " / ".join(out.get("real_person_actions", [])), workflow),
    )
    return crisis_id


def _create_care_signal(cur, email, out, case_id) -> Optional[str]:
    try:
        import care_engine as ce
    except Exception:
        return None
    church_id = None
    try:
        cur.execute("SELECT church_id FROM church_members WHERE email=%s LIMIT 1", (email,))
        row = cur.fetchone()
        church_id = row[0] if row else None
    except Exception:
        church_id = None
    return ce.create_signal(
        cur, email=email, church_id=church_id, signal_type="crisis_linked",
        signal_level=out["risk_level"], title="进入危机关怀流程",
        summary="系统检测到高危信号，已建议连接真实的人与专业帮助。请按教会关怀流程尽快联系本人。",
        suggested_action="尽快联系本人，并通知牧者/可信同伴；如有立即危险请联系当地紧急服务。",
        source_type="suffering_case", source_id=case_id,
        consent_share=False,                 # crisis escalation does not require prior consent
        visible_to_group_leader=True, visible_to_pastor=True, requires_followup=True,
    )


# ── agent_runs bookkeeping ───────────────────────────────────────────────────
def _start_run(email, content, get_db, release_db) -> Optional[int]:
    if get_db is None:
        return None
    conn = None
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO agent_runs (email, agent_name, event_type, input_payload, status) "
                "VALUES (%s,%s,%s,%s::jsonb,'RUNNING') RETURNING id",
                (email, "SufferingTheologyAgent", "suffering.analyze",
                 json.dumps(_llm._redact({"content": content}))),
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
                "UPDATE agent_runs SET status='DONE', output_payload=%s::jsonb WHERE id=%s AND status<>'FAILED'",
                (json.dumps({"risk_level": result["risk_level"], "is_crisis": result["is_crisis"],
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
