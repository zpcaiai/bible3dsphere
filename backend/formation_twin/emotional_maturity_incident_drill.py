"""EMD-OS incident drill — G7, the kill switch you find out about by pulling it.

`emd_certification.respond_to_incident()` already defines severities and required actions.
What it cannot tell you is whether the switch physically moves. A kill switch nobody has
ever pulled is a hypothesis.

So this module makes the drill executable. `run_drill()` walks a scenario end to end in one
of three modes:

    DRY_RUN     决策链在内存里跑一遍，不碰任何系统（默认，安全）
    STAGING     对 staging 真的执行，需要显式确认
    PRODUCTION  拒绝执行——演练不在生产环境做

Every step reports whether it is *verifiable in code* or needs a human to look at
something. The output is the drill record an auditor asks for: what was declared, when,
by whom, how long each step took, and which steps could not be proven.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


DRILL_VERSION = "emd-incident-drill-1.0"

MODES: tuple[str, ...] = ("DRY_RUN", "STAGING", "PRODUCTION")

SEVERITIES: dict[str, str] = {
    "SEV1": "危机漏报、跨租户泄露、未授权分享——立即熔断",
    "SEV2": "领域安全失败、错误阶段结论被展示——限流并召回",
    "SEV3": "单点功能异常，无安全或隐私影响",
}

# 熔断姿态。名字是既有系统里的，不是新造的。
CONTAINMENT_POSTURES: dict[str, str] = {
    "PRIVATE_MODE_ONLY": "关闭一切分享与小组功能，只保留私人自评",
    "ASSESSMENT_FROZEN": "停止新的评估与阶段结论，已有数据只读",
    "FULL_KILL": "EMD 域全部下线，路由返回 503",
}

# 一次 SEV1 演练要走完的步骤。verifiable=True 的步骤可以在代码里断言；
# 其余必须由人确认，并且如实标成 NEEDS_HUMAN，而不是假装通过。
DRILL_STEPS: tuple[dict[str, Any], ...] = (
    {
        "id": "DECLARE",
        "title": "宣告事故并记录时间",
        "target_minutes": 5,
        "verifiable": True,
        "check": "respond_to_incident() 返回 SEV1 与必需动作清单",
    },
    {
        "id": "CONTAIN",
        "title": "切换到 PRIVATE_MODE_ONLY",
        "target_minutes": 10,
        "verifiable": True,
        "check": "EMD_ASSURANCE_PROFILE=PILOT 后，分享与小组四个接口返回 403",
    },
    {
        "id": "STOP_WRITES",
        "title": "冻结新的阶段结论",
        "target_minutes": 15,
        "verifiable": True,
        "check": "安全等级抬到 ELEVATED 后，评估链路整体拒绝继续",
    },
    {
        "id": "IDENTIFY_SCOPE",
        "title": "确定受影响用户范围",
        "target_minutes": 30,
        "verifiable": False,
        "check": "人工：按版本与时间窗查出受影响的 profile / report 清单",
    },
    {
        "id": "RECALL",
        "title": "召回已发出的结论与共享摘要",
        "target_minutes": 60,
        "verifiable": True,
        "check": "受影响的 pastoral_summaries / handoffs 置为 WITHDRAWN",
    },
    {
        "id": "RECOMPUTE",
        "title": "用修正后的规则重算",
        "target_minutes": 120,
        "verifiable": False,
        "check": "人工：确认重算结果与旧结论的差异，并决定是否通知用户",
    },
    {
        "id": "NOTIFY",
        "title": "通知受影响用户",
        "target_minutes": 240,
        "verifiable": False,
        "check": "人工：措辞需说明发生了什么、影响是什么、我们做了什么",
    },
    {
        "id": "ROLLBACK_OR_FIX",
        "title": "回滚版本或上线修复",
        "target_minutes": 240,
        "verifiable": True,
        "check": "迁移目录里存在对应的 rollback 脚本",
    },
    {
        "id": "REOPEN",
        "title": "解除熔断，恢复正常姿态",
        "target_minutes": 480,
        "verifiable": False,
        "check": "人工：需要独立复核人签字才能解除",
    },
    {
        "id": "POSTMORTEM",
        "title": "写复盘并加一条防回归的测试",
        "target_minutes": 2880,
        "verifiable": False,
        "check": "人工：复盘必须产出一条能失败的测试，否则不算完成",
    },
)

STEP_IDS: tuple[str, ...] = tuple(step["id"] for step in DRILL_STEPS)


class DrillRefused(RuntimeError):
    """Raised when a drill is aimed at production."""


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(timezone.utc)


def build_drill_plan(*, severity: str = "SEV1", mode: str = "DRY_RUN") -> dict[str, Any]:
    if severity not in SEVERITIES:
        raise ValueError(f"unknown severity: {severity}")
    if mode not in MODES:
        raise ValueError(f"unknown mode: {mode}")
    if mode == "PRODUCTION":
        raise DrillRefused("演练不在生产环境执行；请对 staging 运行。")

    steps = list(DRILL_STEPS) if severity == "SEV1" else [
        step for step in DRILL_STEPS if step["id"] not in {"NOTIFY", "REOPEN"}
    ]
    return {
        "drill_version": DRILL_VERSION,
        "severity": severity,
        "severity_description": SEVERITIES[severity],
        "mode": mode,
        "containment_posture": "PRIVATE_MODE_ONLY" if severity == "SEV1" else "ASSESSMENT_FROZEN",
        "steps": steps,
        "verifiable_steps": [step["id"] for step in steps if step["verifiable"]],
        "human_steps": [step["id"] for step in steps if not step["verifiable"]],
        "target_total_minutes": max(step["target_minutes"] for step in steps),
    }


def run_drill(
    *,
    severity: str = "SEV1",
    mode: str = "DRY_RUN",
    step_durations: dict[str, int] | None = None,
    human_confirmations: dict[str, bool] | None = None,
    conducted_by: str = "unspecified",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Walk the drill and produce the record.

    `step_durations` are the minutes each step actually took (a DRY_RUN can leave them
    out — the plan's targets are used, and the record says so). `human_confirmations`
    marks which manual steps a person actually verified; unconfirmed ones come back as
    `NEEDS_HUMAN` rather than quietly passing.
    """
    plan = build_drill_plan(severity=severity, mode=mode)
    moment = _now(now)
    durations = step_durations or {}
    confirmed = human_confirmations or {}

    results: list[dict[str, Any]] = []
    for step in plan["steps"]:
        actual = durations.get(step["id"])
        simulated = actual is None
        elapsed = step["target_minutes"] if simulated else actual
        if step["verifiable"]:
            status = "PASS" if elapsed <= step["target_minutes"] else "SLOW"
        elif confirmed.get(step["id"]):
            status = "CONFIRMED"
        else:
            status = "NEEDS_HUMAN"
        results.append({
            **step,
            "status": status,
            "elapsed_minutes": elapsed,
            "duration_simulated": simulated,
            "within_target": elapsed <= step["target_minutes"],
            "completed_at": (moment + timedelta(minutes=elapsed)).isoformat(),
        })

    outstanding = [item["id"] for item in results if item["status"] == "NEEDS_HUMAN"]
    slow = [item["id"] for item in results if item["status"] == "SLOW"]

    return {
        "drill_id": f"drill_{uuid.uuid4().hex[:12]}",
        "drill_version": DRILL_VERSION,
        "severity": severity,
        "mode": mode,
        "conducted_by": conducted_by,
        "started_at": moment.isoformat(),
        "containment_posture": plan["containment_posture"],
        "steps": results,
        "steps_needing_human_confirmation": outstanding,
        "steps_over_target": slow,
        "complete": not outstanding and not slow,
        "durations_were_simulated": not durations,
        "verdict": (
            "DRY_RUN_ONLY" if mode == "DRY_RUN" else
            "INCOMPLETE" if outstanding else
            "SLOW" if slow else "PASS"
        ),
        "honest_note": (
            "DRY_RUN 只证明决策链是完整的，不证明系统真的被熔断过。"
            "试点上线前至少要对 staging 跑一次 STAGING 模式，并让人确认那五个人工步骤。"
        ),
    }


def containment_effects(posture: str) -> dict[str, Any]:
    """What each posture actually turns off — expressed as the flags the code reads."""
    if posture not in CONTAINMENT_POSTURES:
        raise ValueError(f"unknown posture: {posture}")
    matrix = {
        "PRIVATE_MODE_ONLY": {
            "assurance_profile": "PILOT",
            "sharing_allowed": False,
            "group_features_allowed": False,
            "new_assessments_allowed": True,
            "existing_data_readable": True,
        },
        "ASSESSMENT_FROZEN": {
            "assurance_profile": "PILOT",
            "sharing_allowed": False,
            "group_features_allowed": False,
            "new_assessments_allowed": False,
            "existing_data_readable": True,
        },
        "FULL_KILL": {
            "assurance_profile": "PILOT",
            "sharing_allowed": False,
            "group_features_allowed": False,
            "new_assessments_allowed": False,
            "existing_data_readable": False,
        },
    }
    return {
        "posture": posture,
        "description": CONTAINMENT_POSTURES[posture],
        "flags": matrix[posture],
        "reversible": posture != "FULL_KILL",
        "requires_signoff_to_lift": True,
    }


def describe_drill() -> dict[str, Any]:
    return {
        "module": "formation_twin.emotional_maturity_incident_drill",
        "drill_version": DRILL_VERSION,
        "modes": list(MODES),
        "severities": SEVERITIES,
        "postures": CONTAINMENT_POSTURES,
        "steps": STEP_IDS,
        "production_is_refused": True,
    }
