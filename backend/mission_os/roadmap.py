"""Evidence-backed Mission OS journey roadmap.

The roadmap is a projection over existing domain records. It deliberately
does not let a user mark safety or sending gates complete by hand.
"""
from __future__ import annotations

from typing import Any


COMPLETE = "complete"
ACTIVE = "active"
BLOCKED = "blocked"
UPCOMING = "upcoming"


def _item(
    key: str,
    label: str,
    *,
    done: bool = False,
    started: bool = False,
    blocked: bool = False,
    optional: bool = False,
    detail: str | None = None,
) -> dict[str, Any]:
    status = BLOCKED if blocked else COMPLETE if done else ACTIVE if started else UPCOMING
    return {
        "key": key,
        "label": label,
        "status": status,
        "optional": optional,
        "detail": detail,
    }


def _stage(
    key: str,
    number: int,
    title: str,
    eyebrow: str,
    description: str,
    workspace_panel: str,
    action_label: str,
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    required = [item for item in items if not item["optional"]]
    completed = sum(item["status"] == COMPLETE for item in required)
    if any(item["status"] == BLOCKED for item in required):
        status = BLOCKED
    elif required and completed == len(required):
        status = COMPLETE
    elif any(item["status"] in (ACTIVE, COMPLETE) for item in required):
        status = ACTIVE
    else:
        status = UPCOMING
    return {
        "key": key,
        "number": number,
        "title": title,
        "eyebrow": eyebrow,
        "description": description,
        "status": status,
        "progress": round((completed / len(required)) * 100) if required else 0,
        "completedItems": completed,
        "totalItems": len(required),
        "workspacePanel": workspace_panel,
        "actionLabel": action_label,
        "items": items,
    }


def build_roadmap(facts: dict[str, Any]) -> dict[str, Any]:
    """Build a user-facing roadmap from normalized repository facts."""
    calling = facts.get("calling") or {}
    readiness = facts.get("readiness") or {}
    training = facts.get("training") or {}
    sending = facts.get("sending") or {}
    team = facts.get("team") or {}
    preparation = facts.get("preparation") or {}
    gate = facts.get("gate") or {}

    calling_status = calling.get("status")
    calling_blocked = calling_status in {"paused", "withdrawn"} or int(calling.get("hardBlocks") or 0) > 0

    readiness_status = readiness.get("status")
    readiness_level = readiness.get("level")
    readiness_done = readiness_status == "completed" and readiness_level in {
        "team_discernment_ready", "deployment_candidate"
    }
    readiness_blocked = readiness_status == "paused" or readiness_level == "pause_and_restore"

    training_status = training.get("status")
    training_done = training_status == "completed"
    training_blocked = training_status in {"paused", "cancelled"} or int(training.get("blockingGaps") or 0) > 0

    application_status = sending.get("applicationStatus")
    decision = sending.get("decision")
    sending_done = decision in {"approved_for_next_stage", "conditionally_approved"}
    sending_blocked = decision in {"declined_current_application", "revoked"}

    membership_status = team.get("membershipStatus")
    team_done = membership_status in {"provisional", "probation", "active"}
    partner_done = int(team.get("approvedPartners") or 0) > 0

    identity_status = preparation.get("identityStatus")
    finance_status = preparation.get("financeStatus")
    compliance_status = preparation.get("complianceStatus")
    family_status = preparation.get("familyStatus")
    identity_done = identity_status in {"approved", "active"}
    finance_done = finance_status in {"approved", "active"}
    compliance_done = compliance_status == "cleared_for_next_stage"
    family_done = family_status in {"approved", "active", "completed"}

    gate_status = gate.get("status")
    gate_done = gate_status == "ready_for_deployment_planning"
    gate_blocked = gate_status in {"blocked", "revoked"}

    stages = [
        _stage(
            "calling", 1, "聆听与辨识", "从一次感动到可同行的呼召旅程",
            "记录祷告、反思与教会/导师反馈，让呼召在群体中被辨识，而不是由系统替你下结论。",
            "calling", "继续呼召辨识",
            [
                _item("journey", "已开始呼召旅程", done=bool(calling), started=bool(calling), blocked=calling_blocked, detail=calling_status),
                _item("reflection", "留下祷告与反思记录", done=int(calling.get("reflections") or 0) > 0, started=bool(calling)),
                _item("confirmation", "获得导师或教会的观察反馈", done=bool(calling.get("hasCommunityEvidence")), started=int(calling.get("evidence") or 0) > 0),
            ],
        ),
        _stage(
            "readiness", 2, "准备度评估", "看见恩赐，也诚实面对缺口",
            "从属灵生命、关系、跨文化能力、家庭与专业等维度收集证据，由本人、导师与教会共同评估。",
            "readiness", "打开准备度评估",
            [
                _item("assessment", "建立准备度评估", done=bool(readiness), started=bool(readiness), blocked=readiness_blocked, detail=readiness_status),
                _item("dimensions", "完成关键维度与证据", done=int(readiness.get("dimensions") or 0) >= 15, started=int(readiness.get("dimensions") or 0) > 0, detail=f"{int(readiness.get('dimensions') or 0)}/15"),
                _item("panel", "完成人工评审结论", done=readiness_done, started=readiness_status in {"mentor_review", "church_review", "panel_review"}, blocked=readiness_blocked, detail=readiness_level),
            ],
        ),
        _stage(
            "training", 3, "装备与实践", "把准备缺口变成可执行的成长计划",
            "以训练计划、语言学习和受督导的本地实践回应真实缺口；完成课程不自动等于可以差派。",
            "training", "查看装备计划",
            [
                _item("plan", "建立个性化装备计划", done=bool(training), started=bool(training), blocked=training_blocked, detail=training_status),
                _item("modules", "完成计划中的必修模块", done=bool(training) and int(training.get("requiredModules") or 0) > 0 and int(training.get("completedModules") or 0) >= int(training.get("requiredModules") or 0), started=int(training.get("completedModules") or 0) > 0, detail=f"{int(training.get('completedModules') or 0)}/{int(training.get('requiredModules') or 0)}"),
                _item("approval", "由导师与教会确认装备完成", done=training_done, started=training_status in {"awaiting_mentor_review", "approved", "active"}, blocked=training_blocked),
            ],
        ),
        _stage(
            "sending", 4, "教会差派", "从个人预备进入教会共同承担",
            "差派申请、教会确认和委员会决议彼此独立；任何附带条件都会保留在后续预备中。",
            "sending", "进入差派申请",
            [
                _item("application", "建立并提交差派申请", done=application_status in {"committee_ready", "approved"}, started=bool(application_status), blocked=sending_blocked, detail=application_status),
                _item("decision", "完成差派委员会决议", done=sending_done, started=bool(decision), blocked=sending_blocked, detail=decision),
            ],
        ),
        _stage(
            "team", 5, "团队与在地伙伴", "先建立彼此负责的关系，再谈进入禾场",
            "明确团队角色、盟约、监督与申诉路径，并由在地伙伴真实参与决策，而不是只作为资源联系人。",
            "team", "查看团队与伙伴",
            [
                _item("membership", "加入并确认宣教团队", done=team_done, started=bool(membership_status), detail=membership_status),
                _item("partner", "确认经审核的在地伙伴", done=partner_done, started=int(team.get("partners") or 0) > 0, detail=f"{int(team.get('approvedPartners') or 0)} 个已审核"),
            ],
        ),
        _stage(
            "preparation", 6, "整全预备", "合法、财务、家庭与合规同步推进",
            "合法身份必须与实际活动一致；家庭成员保有独立同意权。财务、专业意见和敏感证件都按最小权限管理。",
            "identity", "处理部署预备",
            [
                _item("identity", "合法身份路径已获批准", done=identity_done, started=bool(identity_status), blocked=identity_status in {"not_viable", "revoked"}, detail=identity_status),
                _item("finance", "财务方案与储备已获批准", done=finance_done, started=bool(finance_status), blocked=finance_status in {"underfunded", "paused"}, detail=finance_status),
                _item("compliance", "专业合规审查已放行", done=compliance_done, started=bool(compliance_status), blocked=compliance_status == "blocked", detail=compliance_status),
                _item("family", "家庭准备与独立同意", done=family_done, started=bool(family_status), blocked=family_status in {"does_not_consent", "blocked"}, optional=True, detail=family_status or "按家庭情况"),
            ],
        ),
        _stage(
            "gate", 7, "部署就绪 Gate", "就绪只解锁规划，不会自动激活部署",
            "由人工小组检查未解决的安全、法律、家庭、财务与照护问题。系统不会把高需要抵消硬阻塞。",
            "gate", "运行部署就绪检查",
            [
                _item("gate", "人工小组完成部署就绪检查", done=gate_done, started=bool(gate_status), blocked=gate_blocked, detail=gate_status),
                _item("blocks", "所有硬阻塞已解决", done=gate_done and not gate.get("blockingFindings"), started=bool(gate_status), blocked=bool(gate.get("blockingFindings")), detail=("、".join(gate.get("blockingFindings") or []) or None)),
            ],
        ),
    ]

    current_index = next((i for i, stage in enumerate(stages) if stage["status"] != COMPLETE), len(stages) - 1)
    if stages[current_index]["status"] == UPCOMING:
        stages[current_index]["status"] = ACTIVE

    required_items = [item for stage in stages for item in stage["items"] if not item["optional"]]
    completed_items = sum(item["status"] == COMPLETE for item in required_items)
    blocked_items = sum(item["status"] == BLOCKED for item in required_items)
    started = any(item["status"] in {ACTIVE, COMPLETE, BLOCKED} for item in required_items)
    return {
        "version": 1,
        "mode": "evidence_backed",
        "hasJourney": started,
        "summary": {
            "progress": round((completed_items / len(required_items)) * 100) if required_items else 0,
            "completedItems": completed_items,
            "totalItems": len(required_items),
            "blockedItems": blocked_items,
            "currentStageKey": stages[current_index]["key"],
            "currentStageTitle": stages[current_index]["title"],
        },
        "principles": [
            "AI 只提供整理与建议，不宣告个人呼召，也不作最终差派决定。",
            "当地教会、在地伙伴、配偶与家庭成员保有真实且可撤回的同意权。",
            "任何安全、法律、儿童保护或严重照护风险都不能被进度分数抵消。",
        ],
        "stages": stages,
    }
