"""
routers/expansion_pack.py — 内容与神学扩充聚合器（content-theology-expansion 批次）

把本批次 14 个子路由聚合为一个可挂载的 router，并提供统一 init。
设计为「单个模块加载/初始化失败不影响其余」，保持与现有系统解耦、可回退。
每个子路由自带 /api/* 前缀，故本聚合器不加前缀。
"""
from __future__ import annotations

import importlib
from typing import Any, List, Tuple

from fastapi import APIRouter

# (模块名, init 函数名)
_SUBMODULES: List[Tuple[str, str]] = [
    ("lament", "init_lament_router"),
    ("affections", "init_affections_router"),
    ("ordo_amoris_augustine", "init_ordo_amoris_augustine_router"),
    ("tender_heart", "init_tender_heart_router"),
    ("formation_liturgy", "init_formation_liturgy_router"),
    ("spirits", "init_spirits_router"),
    ("union", "init_union_router"),
    ("delight", "init_delight_router"),
    ("emotionally_healthy", "init_emotionally_healthy_router"),
    ("contentment", "init_contentment_router"),
    ("knowgod", "init_knowgod_router"),
    ("renovation", "init_renovation_router"),
    ("chinese", "init_chinese_router"),
    ("expansion_resources", "init_expansion_resources_router"),
]


def _import_sub(name: str):
    for attempt in ("routers." + name, "." + name):
        try:
            if attempt.startswith("."):
                return importlib.import_module(attempt, package=__package__)
            return importlib.import_module(attempt)
        except Exception:
            continue
    raise ImportError("cannot import submodule: " + name)


router = APIRouter()
_loaded: List[Tuple[str, str, Any]] = []
for _name, _init in _SUBMODULES:
    try:
        _mod = _import_sub(_name)
        router.include_router(getattr(_mod, "router"))
        _loaded.append((_name, _init, _mod))
    except Exception as exc:  # pragma: no cover
        print(f"[expansion_pack] WARNING: failed to load '{_name}': {exc}", flush=True)


def init_expansion_pack(*, get_db, release_db, get_session_user, to_shanghai_iso) -> int:
    """统一初始化所有子路由；返回成功初始化的数量。单个失败不影响其余。"""
    ok = 0
    for _name, _init, _mod in _loaded:
        try:
            getattr(_mod, _init)(get_db=get_db, release_db=release_db,
                                 get_session_user=get_session_user, to_shanghai_iso=to_shanghai_iso)
            ok += 1
        except Exception as exc:  # pragma: no cover
            print(f"[expansion_pack] WARNING: init '{_name}' failed: {exc}", flush=True)
    print(f"[expansion_pack] initialized {ok}/{len(_SUBMODULES)} modules", flush=True)
    return ok
