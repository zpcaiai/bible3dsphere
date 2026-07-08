"""
formation_bridge.py — 让各子系统（偶像监测 / 等候之路 / 省察…）把洞察「回流」到
统一的 Formation 八维成长档案，闭合 HIDOS 反馈环。

设计：best-effort、静默失败。任何异常都不影响调用方的主流程。适配「同步 FastAPI
端点（线程池）」场景：直接用连接池做同步写入（record_formation_event_sync），
不再用 event-loop 派发协程——后者在 worker 线程里会静默 no-op、事件丢失却仍返回 True。
只有真正落库成功才返回 True。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional


def record_formation_event_sync(
    eng,
    *,
    user_id: str,
    session_id: str,
    pattern_categories: List[str],
    loop_broken: bool,
    dimension_deltas: Dict[str, float],
    decision_category: str = "other",
) -> bool:
    """Synchronously persist a formation event to TimescaleDB.

    Executes the write directly on a pooled psycopg2 connection (no event-loop
    dispatch / no orphaned ``ensure_future``), so it works correctly from sync
    FastAPI endpoints running in the threadpool. Mirrors
    ``FormationEngine.record_formation_event``'s insert. Returns True *only* if
    the row was actually committed.
    """
    pool = getattr(eng, "_db_pool", None)
    if pool is None:
        return False
    try:
        from formation_engine import _canon_uid  # type: ignore
    except Exception:
        def _canon_uid(_conn, uid):  # type: ignore
            return str(uid or "")
    conn = None
    try:
        conn = pool.getconn()
        uid = _canon_uid(conn, user_id)
        with conn.cursor() as cur:
            now = datetime.now(tz=timezone.utc)
            cur.execute(
                """
                INSERT INTO sfds_formation_metrics (
                    user_id, session_id, recorded_at, decision_category,
                    loop_broken, pattern_categories,
                    humility_delta, fear_tendency_delta, pride_tendency_delta,
                    emotional_stability_delta, truth_alignment_delta,
                    relational_health_delta, resilience_delta, spiritual_clarity_delta
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    uid, session_id, now, decision_category,
                    loop_broken, pattern_categories,
                    dimension_deltas.get("humility", 0.0),
                    dimension_deltas.get("fear_tendency", 0.0),
                    dimension_deltas.get("pride_tendency", 0.0),
                    dimension_deltas.get("emotional_stability", 0.0),
                    dimension_deltas.get("truth_alignment", 0.0),
                    dimension_deltas.get("relational_health", 0.0),
                    dimension_deltas.get("resilience", 0.0),
                    dimension_deltas.get("spiritual_clarity", 0.0),
                ),
            )
        conn.commit()
        return True
    except Exception as exc:  # pragma: no cover
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        print(f"[formation_bridge] sync insert failed: {exc}", flush=True)
        return False
    finally:
        if conn is not None:
            try:
                pool.putconn(conn)
            except Exception:
                pass


def record_formation(
    user_id: Optional[str],
    pattern_categories: Optional[List[str]],
    *,
    loop_broken: bool = False,
    reflection_active: bool = True,
    emotional_intensity: float = 5.0,
    decision_category: str = "other",
) -> bool:
    """写一条 formation 事件。成功返回 True，任何失败返回 False（静默）。"""
    if not user_id or not pattern_categories:
        return False
    try:
        import uuid
        from formation_engine import get_formation_engine

        eng = get_formation_engine()
        if eng is None:
            return False

        session_id = str(uuid.uuid4())
        insight = eng.analyze_sync(
            user_id=str(user_id),
            pattern_categories=pattern_categories,
            loop_broken=loop_broken,
            decision_category=decision_category,
            session_id=session_id,
            emotional_intensity=emotional_intensity,
            reflection_active=reflection_active,
        )
        deltas = {
            dim: sc.delta
            for dim, sc in insight.current_snapshot.dimensions.items()
        }

        # Synchronous write path (replaces the event-loop hack that silently
        # no-op'd in worker threads). Only report True if the row was committed.
        return record_formation_event_sync(
            eng,
            user_id=str(user_id),
            session_id=session_id,
            pattern_categories=pattern_categories,
            loop_broken=loop_broken,
            dimension_deltas=deltas,
            decision_category=decision_category,
        )
    except Exception as exc:  # pragma: no cover
        print(f"[formation_bridge] skip ({decision_category}): {exc}", flush=True)
        return False
