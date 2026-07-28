"""Batch 1–10 completeness, closure and fit with the pre-existing system.

Three questions, asked as tests rather than as a one-off review:

    完整   EM-01 ~ EM-87 是否都有实现、迁移、路由与测试？
    闭环   各批次是否互相调用形成回路，而不是十座孤岛？
    融洽   是否复用既有能力（crisis_engine / formation_safety / 十个训练引擎），
           而不是另起一套平行系统？

An audit that only runs once rots immediately. These assertions re-derive their facts
from the tree every run, so the next batch cannot quietly break a closure.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).resolve().parents[1]
ENGINE_DIR = BACKEND / "formation_twin"
GOV_DIR = BACKEND / "production_governance"
ROUTER = BACKEND / "routers" / "formation_twin_emotional_maturity.py"
GOV_ROUTER = BACKEND / "routers" / "production_governance.py"
MIGRATIONS = BACKEND / "migrations"
TESTS = BACKEND / "tests"


def engine_files() -> list[Path]:
    return sorted(ENGINE_DIR.glob("emotional_maturity*.py")) + sorted(GOV_DIR.glob("emd_*.py"))


def engine_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in engine_files())


def router_text() -> str:
    return ROUTER.read_text(encoding="utf-8") + GOV_ROUTER.read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# 完整性
# ═════════════════════════════════════════════════════════════════════════════

BATCH_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 10), 2: (11, 19), 3: (20, 27), 4: (28, 37), 5: (38, 46),
    6: (47, 55), 7: (56, 64), 8: (65, 70), 9: (71, 77), 10: (78, 87),
}


def test_every_capability_em01_to_em87_is_implemented():
    present = {int(code) for code in re.findall(r"EM-(\d\d)", engine_text())}
    missing = sorted(set(range(1, 88)) - present)
    assert missing == [], f"capabilities with no implementation: EM-{missing}"


@pytest.mark.parametrize("batch,bounds", sorted(BATCH_RANGES.items()))
def test_each_batch_range_is_fully_covered(batch, bounds):
    low, high = bounds
    present = {int(code) for code in re.findall(r"EM-(\d\d)", engine_text())}
    missing = sorted(set(range(low, high + 1)) - present)
    assert missing == [], f"batch {batch} missing EM-{missing}"


def test_the_ten_batches_partition_em01_to_em87_without_gaps_or_overlap():
    covered: list[int] = []
    for low, high in BATCH_RANGES.values():
        covered.extend(range(low, high + 1))
    assert sorted(covered) == list(range(1, 88))
    assert len(covered) == len(set(covered)), "batch ranges overlap"


def test_every_batch_has_a_report():
    root = BACKEND.parent
    for batch in BATCH_RANGES:
        assert (root / f"EMD_OS_BATCH_{batch:02d}_REPORT.md").exists(), f"batch {batch} report missing"
    assert (root / "EMD_OS_OVERVIEW.md").exists()


def test_every_batch_has_migrations_and_tests():
    emd_migrations = list(MIGRATIONS.glob("*emd*.sql")) + [MIGRATIONS / "0223_formation_twin_emotional_maturity.sql"]
    assert len([path for path in emd_migrations if path.exists()]) >= 10
    emd_tests = list(TESTS.glob("test_*emotional_maturity*.py")) + list(TESTS.glob("test_emd_*.py"))
    assert len(emd_tests) >= 8, f"only {len(emd_tests)} EMD test files"


def test_every_migration_has_a_rollback():
    for path in sorted(MIGRATIONS.glob("*emd*.sql")):
        rollback = MIGRATIONS / "rollback" / f"{path.stem}_down.sql"
        assert rollback.exists(), f"no rollback for {path.name}"


# ═════════════════════════════════════════════════════════════════════════════
# 闭环：批次之间互相调用
# ═════════════════════════════════════════════════════════════════════════════

# (来源模块, 目标模块, 说明) —— 缺一条就说明某个批次是死胡同。
EXPECTED_LINKS: tuple[tuple[str, str, str], ...] = (
    ("emotional_maturity_items", "emotional_maturity", "选题依赖安全等级与维度定义"),
    ("emotional_maturity_events", "emotional_maturity", "真实事件产出 Batch 1 的 EvidenceItem"),
    ("emotional_maturity_regulation", "emotional_maturity", "调节引擎复用安全常量"),
    ("emotional_maturity_family", "emotional_maturity", "家庭/自我模块复用文本安全校验"),
    ("emotional_maturity_conflict", "emotional_maturity", "冲突修复复用第三方措辞校验"),
    ("emotional_maturity_grief", "emotional_maturity", "哀伤模块复用安全常量"),
    ("emotional_maturity_integration", "emotional_maturity", "跨系统编排复用安全等级"),
    ("emotional_maturity_analytics", "emotional_maturity", "分析层复用维度与阶段定义"),
    ("emotional_maturity_pilot_gate", "emd_assurance_profiles", "运行期守卫读取配置档"),
    ("emotional_maturity_presentation", "emotional_maturity", "展示契约复用阶段词表"),
)


@pytest.mark.parametrize("source,target,reason", EXPECTED_LINKS)
def test_batches_are_wired_to_each_other(source, target, reason):
    path = ENGINE_DIR / f"{source}.py"
    if not path.exists():
        path = GOV_DIR / f"{source}.py"
    text = path.read_text(encoding="utf-8")
    assert re.search(rf"from \.?{target} import|from [\w.]*{target} import", text), (
        f"{source} 未引用 {target}：{reason}"
    )


def test_no_emd_module_is_an_island():
    """Every engine module must be imported by the router or by another engine module."""
    orphans = []
    for path in engine_files():
        module = path.stem
        if module in {"emotional_maturity", "emd_certification"}:
            continue  # 基座模块，被大量引用
        referenced_by_router = module in router_text()
        referenced_by_peers = any(
            module in other.read_text(encoding="utf-8")
            for other in engine_files() if other != path
        )
        if not (referenced_by_router or referenced_by_peers):
            orphans.append(module)
    assert orphans == [], f"modules nobody uses: {orphans}"


# ── 三条曾经断裂的回路，各自锁死 ─────────────────────────────────────────────

def test_real_events_flow_back_into_stage_scoring():
    """Batch 4 采集的行为证据必须能回到 Batch 1 的阶段判定，否则个体永远卡在 E3 上限。"""
    text = ROUTER.read_text(encoding="utf-8")
    assert "event_to_batch1_evidence(" in text
    assert "bridged_to_batch1_dimensions" in text
    assert "formation_twin_emd_evidence_items" in text


def test_withdrawing_twin_consent_actually_withdraws_twin_evidence():
    """停掉复测不等于撤回；已写入 Twin 的证据必须一并撤回并触发重算。"""
    text = ROUTER.read_text(encoding="utf-8")
    assert "withdraw_twin_evidence(" in text
    assert "twin_evidence_withdrawn" in text
    assert "SET status='WITHDRAWN'" in text


def test_training_corpus_guard_has_a_call_site():
    text = ROUTER.read_text(encoding="utf-8")
    assert "assert_no_training_material(" in text
    assert "check-corpus" in text


def test_consent_withdrawal_covers_every_scope_with_downstream_effects():
    text = ROUTER.read_text(encoding="utf-8")
    for scope in ("EMD_BEHAVIOR_EVIDENCE", "EMD_LONGITUDINAL_TWIN"):
        assert scope in text, f"{scope} 撤回后没有任何下游动作"


# ═════════════════════════════════════════════════════════════════════════════
# 融洽：复用既有系统而不是另起一套
# ═════════════════════════════════════════════════════════════════════════════

def test_safety_reuses_the_existing_crisis_system():
    text = engine_text()
    assert "crisis_engine" in text or "/api/crisis" in text, "EMD 自建了危机分流，没有复用既有系统"
    assert "CRISIS_AND_SAFETY_SYSTEM" in text


def test_text_safety_reuses_formation_safety():
    base = (ENGINE_DIR / "emotional_maturity.py").read_text(encoding="utf-8")
    assert "from .formation_safety import review_generated_text" in base


def test_growth_routing_points_at_the_existing_training_engines():
    """EMD 是诊断域，训练必须交回既有的十个引擎，而不是自己再实现一遍。"""
    base = (ENGINE_DIR / "emotional_maturity.py").read_text(encoding="utf-8")
    for engine in ("emotionally_healthy", "anger", "lament", "forgiveness", "rule_of_life"):
        assert engine in base, f"成长路由没有指向既有的 {engine} 引擎"
    routes = re.findall(r'"(/api/[a-z0-9\-/]+)"', base)
    assert len(routes) >= 15, f"only {len(routes)} training routes referenced"


def test_certification_extends_the_existing_governance_package():
    """Batch 10 必须长在 production_governance 里，而不是另起一个治理系统。"""
    assert (GOV_DIR / "scenarios.py").exists()
    assert (GOV_DIR / "evaluation.py").exists()
    assert (GOV_DIR / "release.py").exists()
    assert (GOV_DIR / "emd_certification.py").exists()
    init = (GOV_DIR / "__init__.py").read_text(encoding="utf-8")
    assert init.strip(), "production_governance 包结构被破坏"


def test_emd_routes_live_under_the_existing_formation_twin_prefix():
    from routers.formation_twin_emotional_maturity import router

    paths = [route.path for route in router.routes]
    assert paths, "no routes registered"
    assert all(path.startswith("/api/v1/formation-twin/") for path in paths), (
        "EMD 路由没有挂在既有 Formation Twin 前缀下"
    )


def test_router_is_registered_in_main():
    text = (BACKEND / "main.py").read_text(encoding="utf-8")
    assert "formation_twin_emotional_maturity" in text


def test_no_parallel_scoring_system_was_introduced():
    """既有系统没有总分，EMD 也不能偷偷造一个。"""
    text = engine_text()
    for forbidden in ("emotional_maturity_total_score", "maturity_percentile", "spiritual_rank"):
        # 只允许出现在禁用清单里，不允许作为实际输出字段被赋值
        assignments = re.findall(rf'"{forbidden}":\s*(?!None)[^,\n}}]+', text)
        assert assignments == [], f"{forbidden} 被真实赋值：{assignments}"


# ═════════════════════════════════════════════════════════════════════════════
# 规模与体检
# ═════════════════════════════════════════════════════════════════════════════

def test_public_surface_is_substantially_routed():
    """引擎里的公开函数绝大多数应当可以从 API 到达；剩下的是模块间内部件。"""
    routes = router_text()
    total = reachable = 0
    for path in engine_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = [
            node.name for node in tree.body
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        ]
        total += len(names)
        reachable += sum(1 for name in names if re.search(rf"\b{name}\(", routes))
    assert total >= 120, f"engine surface unexpectedly small: {total}"
    assert reachable / total >= 0.75, f"only {reachable}/{total} public functions reachable from the API"


def test_every_emd_table_is_created_by_a_migration_not_at_runtime():
    router_source = ROUTER.read_text(encoding="utf-8")
    assert "CREATE TABLE" not in router_source, "路由层在运行时建表，绕过了迁移审计"
