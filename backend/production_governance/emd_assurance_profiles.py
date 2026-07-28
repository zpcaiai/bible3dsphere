"""EMD-OS assurance profiles — realistic gates for solo / pilot deployments.

Batch 10 的默认阈值是按「面向公众的高风险产品」写的（每语言 300 个试点样本、15 场认知访谈、
九项独立签署）。对于个人或小规模试点，这些数字既不现实也不必要。

本模块提供两档配置：

    PILOT       个人或少数试点用户，最高只能认证到 RESTRICTED_PILOT
    PRODUCTION  面向公众，沿用 Batch 10 的原始阈值

**只有心理测量（G1）与公平性（G3）的阈值会被放宽。**
以下四道闸门在两档配置中完全一致，永不放宽：

    G0 用途与禁止用途      IU-X 永久禁止，未成年人独立认证
    G4 领域安全            15 类伤害必须覆盖，7 类零容忍
    G5 隐私与个人权利      删除传播、分项同意、默认关闭训练、牧者零默认权限
    G6 LLM / Agent 安全    六项零容忍红队结果

放宽阈值不等于放宽结论：PILOT 档只能拿到 `RESTRICTED_PILOT` 证书，
报告必须继续标注 `exploratory`，且不得开启牧养分享或小组功能。
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


PROFILE_NAMES: tuple[str, ...] = ("PILOT", "PRODUCTION")

UNCHANGED_GATES: tuple[str, ...] = (
    "G0_INTENDED_USE", "G4_DOMAIN_SAFETY", "G5_PRIVACY", "G6_LLM_SECURITY",
)

ASSURANCE_PROFILES: dict[str, dict[str, Any]] = {
    "PILOT": {
        "name": "PILOT",
        "description": "个人或少数试点用户；心理测量与公平性按现实可达水平校准。",
        "max_certifiable_level": "RESTRICTED_PILOT",
        "psychometric": {
            "content_expert_agreement_default": 0.80,
            "open_response_inter_rater_default": 0.70,
            "individual_trend_reliability_default": 0.70,
            "stable_construct_retest_default": 0.60,
            "minimum_pilot_sample_per_primary_locale": 20,
            "minimum_cognitive_interviews_per_locale": 5,
            "minimum_real_behavior_events_for_individual_stage": 3,
            "max_evidence_level": "PM3_PILOT_CALIBRATED",
        },
        "fairness": {
            "minimum_group_sample": 5,
            "require_all_locales": False,
            "accessibility_required": True,
        },
        "required_signoffs": (
            "product", "engineering", "privacy", "domain_safety", "independent_reviewer",
        ),
        "required_labels": ("exploratory", "非临床", "个人反思用途"),
        "sharing_allowed": False,
        "group_features_allowed": False,
    },
    "PRODUCTION": {
        "name": "PRODUCTION",
        "description": "面向公众的部署；沿用 Batch 10 原始阈值。",
        "max_certifiable_level": "COMMUNITY_RESTRICTED",
        "psychometric": {
            "content_expert_agreement_default": 0.80,
            "open_response_inter_rater_default": 0.75,
            "individual_trend_reliability_default": 0.80,
            "stable_construct_retest_default": 0.70,
            "minimum_pilot_sample_per_primary_locale": 300,
            "minimum_cognitive_interviews_per_locale": 15,
            "minimum_real_behavior_events_for_individual_stage": 3,
            "max_evidence_level": "PM5_LONGITUDINAL_RESPONSIVE",
        },
        "fairness": {
            "minimum_group_sample": 30,
            "require_all_locales": True,
            "accessibility_required": True,
        },
        "required_signoffs": (
            "product", "engineering", "security", "privacy", "psychometric",
            "domain_safety", "pastoral_theology", "data_science", "independent_reviewer",
        ),
        "required_labels": ("exploratory", "非临床"),
        "sharing_allowed": True,
        "group_features_allowed": True,
    },
}


def resolve_profile(profile: str = "PRODUCTION") -> dict[str, Any]:
    if profile not in ASSURANCE_PROFILES:
        raise ValueError(f"unknown assurance profile: {profile}")
    return ASSURANCE_PROFILES[profile]


def psychometric_thresholds(profile: str = "PRODUCTION") -> dict[str, Any]:
    return dict(resolve_profile(profile)["psychometric"])


def fairness_thresholds(profile: str = "PRODUCTION") -> dict[str, Any]:
    return dict(resolve_profile(profile)["fairness"])


def required_signoffs(profile: str = "PRODUCTION") -> tuple[str, ...]:
    return tuple(resolve_profile(profile)["required_signoffs"])


def profile_diff() -> dict[str, Any]:
    """What PILOT relaxes — and what it explicitly does not."""
    pilot = ASSURANCE_PROFILES["PILOT"]
    production = ASSURANCE_PROFILES["PRODUCTION"]
    relaxed: list[dict[str, Any]] = []
    for group in ("psychometric", "fairness"):
        for key, pilot_value in pilot[group].items():
            production_value = production[group].get(key)
            if pilot_value != production_value:
                relaxed.append({
                    "gate": "G1_PSYCHOMETRIC" if group == "psychometric" else "G3_FAIRNESS",
                    "setting": key,
                    "pilot": pilot_value,
                    "production": production_value,
                })
    return {
        "relaxed": relaxed,
        "unchanged_gates": list(UNCHANGED_GATES),
        "signoffs_dropped_in_pilot": [
            role for role in production["required_signoffs"] if role not in pilot["required_signoffs"]
        ],
        "pilot_ceiling": pilot["max_certifiable_level"],
        "pilot_restrictions": ["不允许牧养分享", "不允许小组功能", "报告必须标注 exploratory"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 可执行清单
# ─────────────────────────────────────────────────────────────────────────────

CHECKLIST_PRIORITIES: tuple[str, ...] = ("MUST_DO_NOW", "BEFORE_MORE_USERS", "BEFORE_PUBLIC_LAUNCH")

CHECKLIST_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "id": "SAFETY_E2E",
        "priority": "MUST_DO_NOW",
        "gate": "G4_DOMAIN_SAFETY",
        "title": "危机路由端到端验证",
        "why": "唯一一条出错可能伤人的路径。",
        "effort": "已自动化",
        "verification": "pytest tests/test_emd_safety_end_to_end.py",
        "automatable": True,
        "evidence": {"test": "tests/test_emd_safety_end_to_end.py"},
    },
    {
        "id": "DELETION_PROPAGATION",
        "priority": "MUST_DO_NOW",
        "gate": "G5_PRIVACY",
        "title": "删除传播验证（结构 + 真实数据库）",
        "why": "承诺写在常量里不等于删除；必须证明每张个人表都在覆盖范围内，且账户级删除不会漏掉 EMD。",
        "effort": "已自动化（结构）+ 集成测试（需 DB）",
        "verification": "pytest tests/test_emd_deletion_propagation.py；迁移 0233 的 erasure_coverage_gaps() 必须返回空",
        "automatable": True,
        "evidence": {
            "test": "tests/test_emd_deletion_propagation.py",
            "module": "formation_twin.emotional_maturity_erasure",
            "migration": "migrations/0233_emd_erasure_propagation.sql",
        },
    },
    {
        "id": "MODEL_TRAINING_OPTOUT",
        "priority": "MUST_DO_NOW",
        "gate": "G5_PRIVACY",
        "title": "模型供应商训练退出（代码强制 + 控制台确认）",
        "why": "P3 级材料（祷告、家庭历史、危机状态）默认不得进入训练。",
        "effort": "代码已强制；控制台确认约 1 小时",
        "verification": "sanitize_provider_call 对未登记供应商抛异常；POST /emotional-maturity/training-optout/audit 返回 PASS",
        "automatable": True,
        "evidence": {
            "test": "tests/test_emd_pilot_readiness.py",
            "module": "formation_twin.emotional_maturity_training_optout",
        },
    },
    {
        "id": "UI_LABELS",
        "priority": "MUST_DO_NOW",
        "gate": "G0_INTENDED_USE",
        "title": "展示契约：exploratory / 非临床，且不得有分数感",
        "why": "代码已禁掉分数，UI 不能再制造分数感或诊断感。",
        "effort": "已自动化（后端契约）+ 前端接入",
        "verification": "GET /emotional-maturity/display-contract 提供必填字段与禁用词；validate_ui_payload 拒绝分数、百分位、排名与诊断措辞",
        "automatable": True,
        "evidence": {
            "test": "tests/test_emd_pilot_readiness.py",
            "module": "formation_twin.emotional_maturity_presentation",
        },
    },
    {
        "id": "SHARING_OFF",
        "priority": "MUST_DO_NOW",
        "gate": "G0_INTENDED_USE",
        "title": "试点期关闭牧养分享与小组功能",
        "why": "PILOT 档证书上限是 RESTRICTED_PILOT，不覆盖第三方分享。",
        "effort": "已自动化",
        "verification": "同意接口不提供 EMD_PASTORAL_SHARE；分享 / 小组四个接口返回 403（guard_feature）",
        "automatable": True,
        "evidence": {
            "test": "tests/test_emd_pilot_readiness.py",
            "module": "formation_twin.emotional_maturity_pilot_gate",
            "router_marker": 'guard_feature("PASTORAL_SUMMARY")',
        },
    },
    {
        "id": "RED_TEAM_LIGHT",
        "priority": "BEFORE_MORE_USERS",
        "gate": "G6_LLM_SECURITY",
        "title": "红队：确定性层已自动化，模型层仍需人工",
        "why": "重点验证日记正文里的指令不会被当成系统指令。",
        "effort": "确定性层已自动化；真实 RAG + 工具栈仍需 1 天",
        "verification": "pytest tests/test_emd_red_team.py（14 面全覆盖、六项零容忍全 PASS）；真实模型栈另行人工",
        "automatable": True,
        "evidence": {"test": "tests/test_emd_red_team.py"},
        "still_needs_humans": "接上真实模型与 RAG 后重跑一轮",
    },
    {
        "id": "COGNITIVE_INTERVIEWS",
        "priority": "BEFORE_MORE_USERS",
        "gate": "G1_PSYCHOMETRIC",
        "title": "认知访谈 5–10 人（协议与分析已就绪）",
        "why": "便宜地发现题目被误解，例如「真我」在不同语境下的歧义。",
        "effort": "工具已就绪；访谈本身 5–10 人 × 30 分钟",
        "verification": "POST /emotional-maturity/psychometrics/interview-analysis 返回 gate_status=PASS",
        "automatable": False,
        "evidence": {
            "test": "tests/test_emd_before_more_users.py",
            "module": "formation_twin.emotional_maturity_psychometrics",
        },
        "still_needs_humans": "跑访谈；样本不足时工具会返回 INSUFFICIENT_SAMPLE，不会替人放行",
    },
    {
        "id": "INTER_RATER",
        "priority": "BEFORE_MORE_USERS",
        "gate": "G1_PSYCHOMETRIC",
        "title": "开放文本评分一致性（κ 与分歧裁决已就绪）",
        "why": "行为锚点评分若不稳定，阶段结论就不可信。",
        "effort": "计算已自动化；第二位评分者仍需人",
        "verification": "POST /emotional-maturity/psychometrics/agreement 返回 status=PASS（一致率 ≥ 0.70 且 κ ≥ 0.40）",
        "automatable": False,
        "evidence": {
            "test": "tests/test_emd_before_more_users.py",
            "module": "formation_twin.emotional_maturity_psychometrics",
        },
        "still_needs_humans": "第二位评分者独立评 30 条；单人评分只会得到 INSUFFICIENT_DATA",
    },
    {
        "id": "PRIVACY_ASSESSMENT",
        "priority": "BEFORE_MORE_USERS",
        "gate": "G5_PRIVACY",
        "title": "隐私影响评估（清单已自动生成，法律判断待审）",
        "why": "宗教信仰与健康类信号属敏感数据；CN/EU 部署有真实义务。",
        "effort": "清单与条款映射已自动生成；8 个法律问题需专业审查",
        "verification": "GET /emotional-maturity/privacy-assessment 的 outstanding_legal_questions 全部被回答后，状态才可离开 DRAFT",
        "automatable": False,
        "evidence": {
            "test": "tests/test_emd_before_more_users.py",
            "module": "formation_twin.emotional_maturity_privacy_assessment",
        },
        "still_needs_humans": "8 个法律判断；工具永远返回 DRAFT_PENDING_LEGAL_REVIEW",
    },
    {
        "id": "INCIDENT_DRILL",
        "priority": "BEFORE_MORE_USERS",
        "gate": "G7_ENGINEERING",
        "title": "事故熔断与回滚演练（harness 已就绪）",
        "why": "PRIVATE_MODE_ONLY 与 kill switch 必须真的能按下去。",
        "effort": "决策链可 DRY_RUN；对 staging 实跑仍需半天",
        "verification": "POST /emotional-maturity/incident-drill 以 mode=STAGING 返回 verdict=PASS（五个人工步骤须逐一确认）",
        "automatable": False,
        "evidence": {
            "test": "tests/test_emd_before_more_users.py",
            "module": "formation_twin.emotional_maturity_incident_drill",
        },
        "still_needs_humans": "对 staging 实跑一次；DRY_RUN 永远只返回 DRY_RUN_ONLY",
    },
    {
        "id": "PILOT_SAMPLE",
        "priority": "BEFORE_PUBLIC_LAUNCH",
        "gate": "G1_PSYCHOMETRIC",
        "title": "每主要语言 300 份试点样本",
        "why": "结构分析、DIF 与常模都需要样本量。",
        "effort": "数月",
        "verification": "达到 PM4 及以上证据等级",
        "automatable": False,
        "still_needs_humans": "招募并跟踪每语言 300 名试点用户，数月",
    },
    {
        "id": "FAIRNESS_FULL",
        "priority": "BEFORE_PUBLIC_LAUNCH",
        "gate": "G3_FAIRNESS",
        "title": "完整公平性审计（DIF、测量不变性、安全公平）",
        "why": "跨语言、跨传统的误判率必须分组分析。",
        "effort": "数周",
        "verification": "每组样本 ≥ 30 且六条硬阻断全部不触发",
        "automatable": False,
        "still_needs_humans": "分组抽样与 DIF 分析，需要统计人员",
    },
    {
        "id": "FULL_SIGNOFFS",
        "priority": "BEFORE_PUBLIC_LAUNCH",
        "gate": "G9_SIGNOFF",
        "title": "九项独立签署",
        "why": "同一人不应包办全部高风险签署。",
        "effort": "组织流程",
        "verification": "含心理测量负责人、牧养神学审核者与独立复核人",
        "automatable": False,
        "still_needs_humans": "九个角色各自签署；同一人不得包办",
    },
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = BACKEND_ROOT / "routers" / "formation_twin_emotional_maturity.py"


def _evidence_present(evidence: dict[str, Any]) -> tuple[bool, list[str]]:
    """Is the automated verification for an item actually in the tree?

    Deliberately structural: it proves the test file, implementation module and router
    wiring exist and import cleanly. It does not claim the suite passed — CI does that.
    An item cannot mark itself done just by being listed.
    """
    missing: list[str] = []

    for key in ("test", "migration"):
        relative = evidence.get(key)
        if relative and not (BACKEND_ROOT / relative).exists():
            missing.append(f"{key}:{relative}")

    module = evidence.get("module")
    if module:
        try:
            import_module(module)
        except Exception as exc:  # pragma: no cover - only on a broken tree
            missing.append(f"module:{module} ({exc})")

    marker = evidence.get("router_marker")
    if marker:
        try:
            if marker not in ROUTER_PATH.read_text(encoding="utf-8"):
                missing.append(f"router_marker:{marker}")
        except OSError as exc:  # pragma: no cover
            missing.append(f"router:{exc}")

    return not missing, missing


def auto_verified_ids() -> dict[str, dict[str, Any]]:
    """Items whose automated verification is wired up and importable."""
    results: dict[str, dict[str, Any]] = {}
    for item in CHECKLIST_ITEMS:
        evidence = item.get("evidence")
        if not evidence or not item.get("automatable"):
            # 工具就绪 ≠ 事情做完。需要人的项目即便有实现模块，也不自动打勾。
            continue
        ok, missing = _evidence_present(evidence)
        results[item["id"]] = {"verified": ok, "missing": missing, "evidence": evidence}
    return results


def generate_checklist(
    *,
    profile: str = "PILOT",
    completed_ids: list[str] | None = None,
    auto_verify: bool = True,
) -> dict[str, Any]:
    """An ordered, verifiable checklist for the chosen profile."""
    resolved = resolve_profile(profile)
    done = set(completed_ids or [])
    auto = auto_verified_ids() if auto_verify else {}
    done |= {item_id for item_id, result in auto.items() if result["verified"]}
    scope = {
        "PILOT": {"MUST_DO_NOW", "BEFORE_MORE_USERS"},
        "PRODUCTION": set(CHECKLIST_PRIORITIES),
    }[profile]

    items = []
    for item in CHECKLIST_ITEMS:
        in_scope = item["priority"] in scope
        verification_result = auto.get(item["id"])
        items.append({
            **item,
            "in_scope_for_profile": in_scope,
            "status": "DONE" if item["id"] in done else ("TODO" if in_scope else "LATER"),
            "auto_verified": bool(verification_result and verification_result["verified"]),
            "missing_evidence": (verification_result or {}).get("missing", []),
        })

    blocking = [item for item in items if item["priority"] == "MUST_DO_NOW" and item["status"] == "TODO"]
    return {
        "profile": profile,
        "profile_description": resolved["description"],
        "max_certifiable_level": resolved["max_certifiable_level"],
        "items": items,
        "counts": {
            priority: sum(1 for item in items if item["priority"] == priority)
            for priority in CHECKLIST_PRIORITIES
        },
        "outstanding_blocking_items": [item["id"] for item in blocking],
        "ready_for_pilot_use": not blocking,
        "auto_verified_items": sorted(item_id for item_id, result in auto.items() if result["verified"]),
        "auto_verification_note": (
            "自动核验只证明测试文件、实现模块与路由接线存在且可导入；"
            "「测试通过」由 CI 判定，清单不会替 CI 下结论。"
        ),
        "unchanged_gates": list(UNCHANGED_GATES),
        "reminder": (
            "放宽阈值不等于放宽结论：试点档只能拿到 RESTRICTED_PILOT 证书，"
            "报告必须继续标注 exploratory，且不得开启牧养分享或小组功能。"
        ),
    }


def describe_profiles() -> dict[str, Any]:
    return {
        "module": "production_governance.emd_assurance_profiles",
        "profiles": ASSURANCE_PROFILES,
        "unchanged_gates": list(UNCHANGED_GATES),
        "unchanged_gate_reason": "安全、隐私、红队与用途分级与规模无关，任何配置档都不放宽。",
        "diff": profile_diff(),
        "checklist_priorities": list(CHECKLIST_PRIORITIES),
    }
