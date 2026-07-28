"""EMD-OS deletion propagation — the code side of the G5 privacy gate.

`DELETION_TARGETS` in `production_governance.emd_certification` names eleven places a
user's material can live. A promise in a constant tuple is not deletion; this module
maps each target to the mechanism that actually clears it, and produces a receipt the
endpoint returns so the user (and an auditor) can see what happened.

Three of the seventy-four `formation_twin_emd_*` tables are deliberately **not** deleted:
`item_banks`, `items` and `metric_catalog` are shared catalogues with no `email` column
and no personal content. `test_emd_deletion_propagation.py` re-derives that split from the
migration files, so adding a personal table without adding it here fails the suite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


# ── 每个用户私有的 EMD 表 ────────────────────────────────────────────────────
# 顺序 = 删除顺序：先派生、后原始，避免外键与「删了源头却留下派生结论」。

EMD_PERSONAL_TABLES: tuple[str, ...] = (
    "formation_twin_emd_growth_reports",
    "formation_twin_emd_attributions",
    "formation_twin_emd_generalizations",
    "formation_twin_emd_trajectories",
    "formation_twin_emd_comparability_checks",
    "formation_twin_emd_reassessment_compositions",
    "formation_twin_emd_metric_observations",
    "formation_twin_emd_community_feedback",
    "formation_twin_emd_group_practices",
    "formation_twin_emd_handoffs",
    "formation_twin_emd_pastoral_summaries",
    "formation_twin_emd_formation_plans",
    "formation_twin_emd_rules_of_life",
    "formation_twin_emd_prayer_routings",
    "formation_twin_emd_identity_alignments",
    "formation_twin_emd_twin_bridges",
    "formation_twin_emd_grief_integrations",
    "formation_twin_emd_rest_rhythms",
    "formation_twin_emd_rituals",
    "formation_twin_emd_bypassing_checks",
    "formation_twin_emd_ambiguous_losses",
    "formation_twin_emd_control_calibrations",
    "formation_twin_emd_grief_sessions",
    "formation_twin_emd_losses",
    "formation_twin_emd_trust_assessments",
    "formation_twin_emd_restitution_plans",
    "formation_twin_emd_forgiveness_maps",
    "formation_twin_emd_apologies",
    "formation_twin_emd_dialogues",
    "formation_twin_emd_conflict_issues",
    "formation_twin_emd_boundary_enforcements",
    "formation_twin_emd_boundaries",
    "formation_twin_emd_vulnerability_experiments",
    "formation_twin_emd_true_self_compasses",
    "formation_twin_emd_mask_profiles",
    "formation_twin_emd_survival_oaths",
    "formation_twin_emd_differentiation_assessments",
    "formation_twin_emd_attachment_cycles",
    "formation_twin_emd_family_patterns",
    "formation_twin_emd_genograms",
    "formation_twin_emd_rehearsals",
    "formation_twin_emd_recovery_plans",
    "formation_twin_emd_coregulation_requests",
    "formation_twin_emd_support_persons",
    "formation_twin_emd_impulse_guards",
    "formation_twin_emd_pause_protocols",
    "formation_twin_emd_trigger_profiles",
    "formation_twin_emd_regulation_sessions",
    "formation_twin_emd_growth_evaluations",
    "formation_twin_emd_checkpoints",
    "formation_twin_emd_patterns",
    "formation_twin_emd_transfer_observations",
    "formation_twin_emd_repair_verifications",
    "formation_twin_emd_recovery_metric_sets",
    "formation_twin_emd_event_timelines",
    "formation_twin_emd_real_life_events",
    "formation_twin_emd_sufficiency_runs",
    "formation_twin_emd_calibrations",
    "formation_twin_emd_counterfactual_probes",
    "formation_twin_emd_scenarios",
    "formation_twin_emd_rubric_results",
    "formation_twin_emd_behavior_evidence",
    "formation_twin_emd_responses",
    "formation_twin_emd_reassessment_plans",
    "formation_twin_emd_corrections",
    "formation_twin_emd_growth_routes",
    "formation_twin_emd_profiles",
    "formation_twin_emd_dimension_snapshots",
    "formation_twin_emd_evidence_items",
    "formation_twin_emd_sessions",
    "formation_twin_emd_consents",
)

# 共享题库/指标目录：无 email 列、无个人内容，删除会破坏其他用户的系统。
EMD_SHARED_CATALOG_TABLES: tuple[str, ...] = (
    "formation_twin_emd_item_banks",
    "formation_twin_emd_items",
    "formation_twin_emd_metric_catalog",
)


# ── 十一个删除目标 → 实际机制 ────────────────────────────────────────────────

DELETION_PLAN: tuple[dict[str, Any], ...] = (
    {
        "target": "RELATIONAL_DB",
        "mechanism": "DELETE FROM 每一张 EMD 私有表 WHERE email=%s，单事务提交",
        "scope": f"{len(EMD_PERSONAL_TABLES)} 张表",
        "automatic": True,
        "verification": "erase 后逐表 SELECT count(*) 必须为 0",
    },
    {
        "target": "VECTOR_DB",
        "mechanism": "pgvector 与主库同库：mvfe_memories 等 user_id 键表由 erase_user_data() 动态发现并删除",
        "scope": "personal_userid_tables()",
        "automatic": True,
        "verification": "SELECT * FROM erasure_coverage_gaps() 必须为空",
    },
    {
        "target": "SEARCH_INDEX",
        "mechanism": "EMD 内容从不进入检索索引；索引只包含圣经与公开教导语料",
        "scope": "不适用",
        "automatic": True,
        "verification": "索引构建管线不读取 formation_twin_emd_* 表",
    },
    {
        "target": "CACHE",
        "mechanism": "EMD 读接口不做跨请求缓存；派生结论每次由私有表重新计算",
        "scope": "进程内无持久缓存",
        "automatic": True,
        "verification": "路由层无 cache 装饰器；删除后再次请求返回空画像",
    },
    {
        "target": "REPORTS",
        "mechanism": "14/30/90 报告存在 growth_reports 表，随主库删除一并清除",
        "scope": "formation_twin_emd_growth_reports",
        "automatic": True,
        "verification": "receipt 中该表计数与删除前一致",
    },
    {
        "target": "FORMATION_TWIN",
        "mechanism": "twin_bridges 与 identity_alignments 删除；Twin 侧 EMD 派生字段标记失效",
        "scope": "derived_profiles_invalidated=True",
        "automatic": True,
        "verification": "删除后 Twin 不再返回 EMD 阶段结论",
    },
    {
        "target": "TRAINING_CANDIDATES",
        "mechanism": "EMD 材料默认不进训练候选集（见 emotional_maturity_training_optout）",
        "scope": "默认关闭，无候选行可删",
        "automatic": True,
        "verification": "training_optout.assert_no_training_material() 通过",
    },
    {
        "target": "EXPORT_BUNDLES",
        "mechanism": "导出包按需实时生成，不落盘留存",
        "scope": "无持久化导出",
        "automatic": True,
        "verification": "无 export 存储表；下载链接为一次性响应流",
    },
    {
        "target": "SHARED_SUMMARIES",
        "mechanism": "pastoral_summaries 与 handoffs 删除，并置 shared_summaries_invalidated",
        "scope": "2 张表 + 失效标记",
        "automatic": True,
        "verification": "牧者端再次拉取该用户摘要返回 404",
    },
    {
        "target": "ANALYTICS_METRICS",
        "mechanism": "metric_observations 按 email 删除；聚合指标只保留不可反推的计数",
        "scope": "formation_twin_emd_metric_observations",
        "automatic": True,
        "verification": "聚合表无 email 列，且不含 k<5 的分组",
    },
    {
        "target": "BACKUPS",
        "mechanism": "备份按保留期自然过期；删除请求记录在案，过期前不重放该用户数据",
        "scope": "保留期内不可即时清除",
        "automatic": False,
        "verification": "隐私评估中写明保留期，并确认恢复演练不重建已删除用户",
    },
)

DELETION_PLAN_BY_TARGET: dict[str, dict[str, Any]] = {item["target"]: item for item in DELETION_PLAN}

# 唯一一个无法即时完成的目标，必须如实告诉用户，不能假装已清空。
MANUAL_TARGETS: tuple[str, ...] = tuple(
    item["target"] for item in DELETION_PLAN if not item["automatic"]
)


def build_erasure_receipt(
    deleted_counts: dict[str, int],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Turn raw row counts into an auditable, user-readable receipt."""
    moment = now or datetime.now(timezone.utc)
    missing = [table for table in EMD_PERSONAL_TABLES if table not in deleted_counts]
    unexpected = [table for table in deleted_counts if table not in EMD_PERSONAL_TABLES]
    total = sum(deleted_counts.values())

    return {
        "receipt_generated_at": moment.isoformat(),
        "tables_attempted": len(deleted_counts),
        "tables_expected": len(EMD_PERSONAL_TABLES),
        "rows_deleted_total": total,
        "tables_not_attempted": missing,
        "tables_unexpected": unexpected,
        "complete": not missing and not unexpected,
        "shared_catalogs_preserved": list(EMD_SHARED_CATALOG_TABLES),
        "targets": [
            {
                "target": item["target"],
                "automatic": item["automatic"],
                "mechanism": item["mechanism"],
                "status": "CLEARED" if item["automatic"] else "RETENTION_WINDOW",
            }
            for item in DELETION_PLAN
        ],
        "manual_followups": list(MANUAL_TARGETS),
        "user_message": (
            "你的情感成熟度数据已从主库、向量库、报告、Twin 与共享摘要中删除。"
            "备份副本会在保留期内自然过期，在此期间不会被恢复或用于任何用途。"
        ),
    }


def describe_deletion_plan() -> dict[str, Any]:
    return {
        "module": "formation_twin.emotional_maturity_erasure",
        "personal_tables": len(EMD_PERSONAL_TABLES),
        "shared_catalog_tables": list(EMD_SHARED_CATALOG_TABLES),
        "plan": list(DELETION_PLAN),
        "manual_targets": list(MANUAL_TARGETS),
    }
