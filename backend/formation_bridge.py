"""
formation_bridge.py — 让各子系统（偶像监测 / 等候之路 / 省察…）把洞察「回流」到
统一的 Formation 八维成长档案，闭合 HIDOS 反馈环。

设计：best-effort、静默失败。任何异常都不影响调用方的主流程。镜像 main.py 中
checkin 已验证的 formation 事件写入方式，但适配「同步 FastAPI 端点（线程池）」场景：
此处用全新 event loop 跑 record_formation_event，避免依赖线程内已存在的 loop。
"""
from __future__ import annotations

from typing import List, Optional


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
        import asyncio
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

        coro = eng.record_formation_event(
            user_id=str(user_id),
            session_id=session_id,
            pattern_categories=pattern_categories,
            loop_broken=loop_broken,
            dimension_deltas=deltas,
            decision_category=decision_category,
        )

        try:
            running = asyncio.get_event_loop().is_running()
        except RuntimeError:
            running = False
        if running:
            asyncio.ensure_future(coro)
        else:
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[formation_bridge] skip ({decision_category}): {exc}", flush=True)
        return False
