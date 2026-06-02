#!/usr/bin/env python3
"""
Disciple Formation DAG — 形式化编排器 (LangGraph 风格，但零外部依赖)
==================================================================

把门徒塑造的处理管线从"硬编码的顺序调用"升级为"声明式有向无环图"：
每个节点声明自己的依赖，编排器拓扑排序后依次在共享 state 上执行，并记录 trace。

这正是规格书里 LangGraph StateGraph 的本质（节点 + 依赖 + 共享状态 + 可追溯），
只是用纯 Python 实现，不引入 langgraph/langchain（项目未装、部署不确定）。
未来要给某个引擎换成独立 AI Agent，只需替换对应节点函数，拓扑不变。

管线 DAG：
    input_normalize
        → retrieve_memory   (统一数字孪生：吸收 idolatry/waiting/checkup/gospel/decision/virtues)
        → assess_core       (11 维 / 偶像 / 品格 / 11 引擎 / 导师七段；确定性+AI)
        → fuse_idols        (并入外部偶像证据)
        → fuse_character    (并入外部品格证据)
        → state_transition  (状态机迁移建议)
        → compose_report    (附 provenance / 收口)

节点是纯函数 fn(state)->dict（增量合并进 state）；编排器只管调度与追踪。
落库与事件由 routers/disciple.py 在拿到 result 后处理（图只负责"推理"，不碰副作用）。
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List

try:
    from backend import disciple_engine as de
    from backend import disciple_integration as di
except Exception:  # pragma: no cover
    import disciple_engine as de  # type: ignore
    import disciple_integration as di  # type: ignore


# ─────────────────────────────────────────────────────────────────────────────
# 通用 DAG 执行器
# ─────────────────────────────────────────────────────────────────────────────

class Node:
    def __init__(self, name: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]],
                 deps: List[str] = None):
        self.name = name
        self.fn = fn
        self.deps = deps or []


class Graph:
    """极简 DAG：拓扑排序 + 顺序执行 + trace。节点失败不致命（记录后续用兜底）。"""

    def __init__(self, nodes: List[Node]):
        self.nodes = {n.name: n for n in nodes}
        self._order = self._toposort()

    def _toposort(self) -> List[str]:
        visited, order, temp = set(), [], set()

        def visit(name: str):
            if name in visited:
                return
            if name in temp:
                raise ValueError(f"DAG 存在环：{name}")
            temp.add(name)
            for d in self.nodes[name].deps:
                if d in self.nodes:
                    visit(d)
            temp.discard(name)
            visited.add(name)
            order.append(name)

        for n in self.nodes:
            visit(n)
        return order

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        for name in self._order:
            node = self.nodes[name]
            t0 = time.time()
            ok = True
            try:
                upd = node.fn(state) or {}
                state.update(upd)
            except Exception as exc:  # 单节点失败不拖垮整图
                ok = False
                state.setdefault("_errors", []).append(f"{name}: {exc}")
            trace.append({"node": name, "ok": ok,
                          "ms": round((time.time() - t0) * 1000, 1)})
        state["_trace"] = trace
        return state


# ─────────────────────────────────────────────────────────────────────────────
# 门徒塑造管线节点
# ─────────────────────────────────────────────────────────────────────────────

def _n_input_normalize(state: Dict[str, Any]) -> Dict[str, Any]:
    inputs = state.get("inputs") or {}
    # 轻清洗：去首尾空白
    return {"inputs": {k: (v.strip() if isinstance(v, str) else v) for k, v in inputs.items()}}


def _n_retrieve_memory(state: Dict[str, Any]) -> Dict[str, Any]:
    cur = state.get("cur")
    email = state.get("email")
    if cur is None or not email:
        return {"unified": {"dim_prior": {}, "idol_prior": {}, "char_prior": {}, "provenance": []}}
    unified = di.gather_unified_twin(cur, email, user_id=state.get("user_id"),
                                     settings=state.get("settings"))
    twin = di.apply_unified_prior_to_twin(state.get("twin") or {}, unified)
    return {"unified": unified, "twin": twin}


def _n_assess_core(state: Dict[str, Any]) -> Dict[str, Any]:
    result = de.assess(state.get("inputs") or {},
                       twin=state.get("twin"),
                       network=state.get("network") or {},
                       settings=state.get("settings"),
                       use_ai=state.get("use_ai", True))
    return {"result": result}


def _n_fuse_idols(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"result": di.fuse_external_idols(state["result"], state.get("unified") or {})}


def _n_fuse_character(state: Dict[str, Any]) -> Dict[str, Any]:
    return {"result": di.fuse_external_character(state["result"], state.get("unified") or {})}


def _n_state_transition(state: Dict[str, Any]) -> Dict[str, Any]:
    r = state["result"]
    # assess 已算 spiritual_state/next_state；这里把它显式化进 trace 友好字段
    r["next_state"] = de.next_state(r.get("spiritual_state", "SEEKER"))
    return {"result": r}


def _n_compose_report(state: Dict[str, Any]) -> Dict[str, Any]:
    r = state["result"]
    r["provenance"] = (state.get("unified") or {}).get("provenance", [])
    return {"result": r}


def build_formation_graph() -> Graph:
    return Graph([
        Node("input_normalize", _n_input_normalize),
        Node("retrieve_memory", _n_retrieve_memory, deps=["input_normalize"]),
        Node("assess_core", _n_assess_core, deps=["retrieve_memory"]),
        Node("fuse_idols", _n_fuse_idols, deps=["assess_core"]),
        Node("fuse_character", _n_fuse_character, deps=["fuse_idols"]),
        Node("state_transition", _n_state_transition, deps=["fuse_character"]),
        Node("compose_report", _n_compose_report, deps=["state_transition"]),
    ])


_GRAPH = build_formation_graph()


def run_formation(cur, email: str, *, user_id=None, inputs: Dict[str, Any],
                  twin: Dict[str, Any] = None, network: Dict[str, Any] = None,
                  settings: Any = None, use_ai: bool = True):
    """执行门徒塑造 DAG，返回 (result, trace)。只做推理，不落库/不发事件。"""
    state = {
        "cur": cur, "email": email, "user_id": user_id,
        "inputs": inputs, "twin": twin or {}, "network": network or {},
        "settings": settings, "use_ai": use_ai,
    }
    out = _GRAPH.run(state)
    return out.get("result"), out.get("_trace", [])


def graph_topology() -> List[Dict[str, Any]]:
    """暴露 DAG 结构（给前端/调试展示编排拓扑）。"""
    return [{"node": n.name, "deps": n.deps} for n in _GRAPH.nodes.values()]
