"""EMD-OS privacy impact assessment — G5, the part that can be derived rather than typed.

A PIA is mostly two things: an accurate inventory of what you hold, and a set of legal
judgements about why you may hold it. The first is a fact about the schema and can be
generated — and generated is *better*, because a hand-written inventory is out of date the
day someone adds a table. The second needs a lawyer.

So this module builds the inventory from the migrations and maps each category onto the
PIPL / GDPR articles it engages, then marks every remaining question `NEEDS_LEGAL_REVIEW`
with the specific thing that must be decided. It never fills those in. An assessment that
guesses at a legal basis is worse than no assessment: it looks finished.

Both regimes treat religious belief and health-related data as a special category
(PIPL 敏感个人信息 / GDPR Art. 9), which is most of what EMD holds — so the honest default
throughout is the strict one.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

try:  # 与仓库其它模块一致的双路径导入
    from ..core.schema_catalog import catalog
except ImportError:
    from core.schema_catalog import catalog
from typing import Any


ASSESSMENT_VERSION = "emd-pia-1.0"

# 表名片段 → 数据类别。顺序即优先级：先命中的胜出，所以最敏感的放前面。
_CATEGORY_RULES: tuple[tuple[str, str, str], ...] = (
    ("crisis|safety|safeguard", "CRISIS_AND_SAFETY", "P4_SEALED_SAFETY"),
    ("prayer|ritual|bypass|identity_alignment", "RELIGIOUS_BELIEF", "P3_HIGHLY_SENSITIVE"),
    ("genogram|family_pattern|attachment|survival_oath|mask", "FAMILY_HISTORY", "P3_HIGHLY_SENSITIVE"),
    ("grief|loss|trauma|ambiguous", "BEREAVEMENT_AND_TRAUMA", "P3_HIGHLY_SENSITIVE"),
    ("regulation|impulse|body|pause|trigger", "HEALTH_ADJACENT_SIGNAL", "P3_HIGHLY_SENSITIVE"),
    ("pastoral|handoff|group|community|share", "THIRD_PARTY_DISCLOSURE", "P3_HIGHLY_SENSITIVE"),
    ("conflict|dialogue|apolog|forgive|boundary|trust|restitution", "RELATIONSHIP_EVENT", "P2_SENSITIVE"),
    ("event|timeline|behavior|evidence|transfer|repair", "BEHAVIOURAL_RECORD", "P2_SENSITIVE"),
    ("profile|snapshot|trajector|attribution|generalis|generaliz|pattern", "DERIVED_PROFILE", "P2_SENSITIVE"),
    ("consent", "CONSENT_RECORD", "P1_PERSONAL"),
    ("catalog|item|metric", "SHARED_CATALOGUE", "P0_PUBLIC"),
)

CATEGORY_PURPOSES: dict[str, str] = {
    "CRISIS_AND_SAFETY": "把处于风险中的用户路由到既有危机系统，并避免在不安全处境下继续评估",
    "RELIGIOUS_BELIEF": "在用户自己的信仰语境内提供反思材料",
    "FAMILY_HISTORY": "帮助用户理解当下反应的来处，不作任何家庭成员诊断",
    "BEREAVEMENT_AND_TRAUMA": "支持哀伤与失落的自我整理",
    "HEALTH_ADJACENT_SIGNAL": "识别身体红旗并转向医疗提示，而不是当成情绪解释",
    "THIRD_PARTY_DISCLOSURE": "仅在用户逐字段确认后生成脱敏摘要",
    "RELATIONSHIP_EVENT": "作为阶段判定的行为证据",
    "BEHAVIOURAL_RECORD": "作为阶段判定的行为证据",
    "DERIVED_PROFILE": "生成个人纵向趋势，仅供本人查看",
    "CONSENT_RECORD": "证明每一项处理都有对应授权，并支持分项撤回",
    "SHARED_CATALOGUE": "题库与指标定义，不含个人内容",
}

SPECIAL_CATEGORIES: frozenset[str] = frozenset({
    "CRISIS_AND_SAFETY", "RELIGIOUS_BELIEF", "FAMILY_HISTORY",
    "BEREAVEMENT_AND_TRAUMA", "HEALTH_ADJACENT_SIGNAL", "THIRD_PARTY_DISCLOSURE",
})

# 每条法律映射都只陈述「这条适用」，不替人判断「我们满足了」。
REGULATORY_MAP: tuple[dict[str, Any], ...] = (
    {"regime": "PIPL", "article": "第 28 条", "topic": "敏感个人信息",
     "engages": "宗教信仰、医疗健康、行踪等属敏感个人信息，需单独同意与必要性说明"},
    {"regime": "PIPL", "article": "第 29 条", "topic": "单独同意",
     "engages": "处理敏感个人信息须取得单独同意，不能与总体条款捆绑"},
    {"regime": "PIPL", "article": "第 31 条", "topic": "未成年人",
     "engages": "不满十四周岁的，须取得父母或监护人同意并制定专门规则"},
    {"regime": "PIPL", "article": "第 38–39 条", "topic": "跨境",
     "engages": "向境外提供需通过安全评估 / 认证 / 标准合同，并单独告知"},
    {"regime": "PIPL", "article": "第 44–47 条", "topic": "个人权利",
     "engages": "查阅、复制、更正、删除、解释说明与可携带"},
    {"regime": "PIPL", "article": "第 55–56 条", "topic": "影响评估",
     "engages": "处理敏感个人信息、对外提供、跨境传输前须做个人信息保护影响评估并留存三年"},
    {"regime": "GDPR", "article": "Art. 9(1)-(2)", "topic": "special categories",
     "engages": "宗教信仰与健康数据原则上禁止处理，除非落入 9(2) 的例外（此处最可能是 (a) 明示同意）"},
    {"regime": "GDPR", "article": "Art. 6(1)", "topic": "lawful basis",
     "engages": "除 Art.9 例外外，仍需一个 Art.6 依据"},
    {"regime": "GDPR", "article": "Art. 8", "topic": "children",
     "engages": "信息社会服务对儿童的同意年龄由成员国定为 13–16 岁"},
    {"regime": "GDPR", "article": "Art. 13–14", "topic": "transparency",
     "engages": "收集时须告知目的、依据、留存期与权利"},
    {"regime": "GDPR", "article": "Art. 15–22", "topic": "data subject rights",
     "engages": "访问、更正、删除、限制、可携带、反对与自动化决策"},
    {"regime": "GDPR", "article": "Art. 22", "topic": "automated decisions",
     "engages": "若阶段结论对用户产生法律或类似重大影响，则受限——本系统据此永久禁止高影响用途"},
    {"regime": "GDPR", "article": "Art. 35", "topic": "DPIA",
     "engages": "大规模处理特殊类别数据须做 DPIA"},
    {"regime": "GDPR", "article": "Art. 44–49", "topic": "transfers",
     "engages": "跨境传输需要充分性决定、SCC 或其它保障"},
)

# 只有人能回答的问题。写清楚「要决定什么」，而不是留一个空格。
LEGAL_QUESTIONS: tuple[dict[str, str], ...] = (
    {"id": "LAWFUL_BASIS", "question": "每一类敏感数据分别依据哪一条？",
     "why_human": "同意是否「自由给出」取决于是否存在牧养关系中的权力不对等，这是判断题"},
    {"id": "CONTROLLER_ROLE", "question": "教会部署时，谁是控制者、谁是处理者？",
     "why_human": "决定告知义务、协议形式与责任分配"},
    {"id": "MINORS", "question": "是否面向未成年人？年龄门槛与验证方式？",
     "why_human": "PIPL 十四周岁与 GDPR 各成员国门槛不同，且需要监护人同意机制"},
    {"id": "CROSS_BORDER", "question": "推理与存储发生在哪些法域？",
     "why_human": "模型供应商所在地决定是否触发跨境机制"},
    {"id": "RETENTION", "question": "各类数据保留多久？备份保留期是多久？",
     "why_human": "留存期是业务与法律的平衡，不能由代码推断"},
    {"id": "PASTORAL_ACCESS", "question": "牧者能看到什么，在什么条件下？",
     "why_human": "涉及第三方访问与权力关系，试点期已默认全部关闭"},
    {"id": "DPO", "question": "是否需要指定个人信息保护负责人 / DPO？",
     "why_human": "取决于处理规模与是否属于大规模特殊类别处理"},
    {"id": "BREACH_NOTIFICATION", "question": "泄露通知的时限与对象？",
     "why_human": "GDPR 72 小时与 PIPL 的要求不同，且需与事故流程对齐"},
)


def _classify(table: str) -> tuple[str, str]:
    for pattern, category, sensitivity in _CATEGORY_RULES:
        if re.search(pattern, table):
            return category, sensitivity
    return "DERIVED_PROFILE", "P2_SENSITIVE"


def build_data_inventory() -> dict[str, Any]:
    """Derive the inventory from the migrations, not from memory.

    Uses the shared catalog parser rather than a local copy: this module briefly had its
    own, and a privacy inventory built by a second, subtly different parser is exactly the
    place where drift does the most damage.
    """
    tables = {
        name: columns for name, columns in catalog().items()
        if name.startswith("formation_twin_emd_")
    }

    entries: list[dict[str, Any]] = []
    for table, columns in sorted(tables.items()):
        category, sensitivity = _classify(table)
        entries.append({
            "table": table,
            "category": category,
            "sensitivity": sensitivity,
            "special_category": category in SPECIAL_CATEGORIES,
            "purpose": CATEGORY_PURPOSES[category],
            "personal": "email" in columns,
            "columns": len(columns),
        })

    by_category: dict[str, int] = {}
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1

    return {
        "tables": entries,
        "table_count": len(entries),
        "personal_table_count": sum(1 for entry in entries if entry["personal"]),
        "special_category_tables": sum(1 for entry in entries if entry["special_category"]),
        "by_category": dict(sorted(by_category.items())),
        "derived_from": "backend/migrations/*.sql",
    }


def build_privacy_assessment(
    *,
    jurisdictions: list[str] | None = None,
    profile: str = "PILOT",
    now: datetime | None = None,
) -> dict[str, Any]:
    """The assessment: everything derivable, plus an explicit list of what is not."""
    moment = now or datetime.now(timezone.utc)
    regions = jurisdictions or ["CN", "EU"]
    inventory = build_data_inventory()

    applicable = [
        entry for entry in REGULATORY_MAP
        if (entry["regime"] == "PIPL" and "CN" in regions)
        or (entry["regime"] == "GDPR" and "EU" in regions)
    ]

    # 代码层已经能证明的控制措施，逐条给出证据位置。
    implemented_controls = [
        {"control": "分项同意与独立撤回", "evidence": "emotional_maturity.CONSENT_SCOPES / withdraw_consent"},
        {"control": "撤回后停止使用并撤回 Twin 证据", "evidence": "routers 的 consent/withdraw + withdraw_twin_evidence"},
        {"control": "删除传播覆盖全部个人表", "evidence": "migrations/0233 的 erasure_coverage_gaps()"},
        {"control": "默认不进入模型训练", "evidence": "emotional_maturity_training_optout.sanitize_provider_call"},
        {"control": "牧者零默认权限，试点期完全关闭", "evidence": "emotional_maturity_pilot_gate.guard_feature"},
        {"control": "高影响用途永久禁止", "evidence": "emd_certification.FORBIDDEN_USES / IU_X"},
        {"control": "不产生总分、排名或诊断", "evidence": "emotional_maturity_presentation.validate_ui_payload"},
        {"control": "危机路由优先于一切评估", "evidence": "tests/test_emd_safety_end_to_end.py"},
        {"control": "开放文本拒绝标记注入", "evidence": "emotional_maturity.validate_safe_text"},
    ]

    outstanding = [
        {**question, "status": "NEEDS_LEGAL_REVIEW"} for question in LEGAL_QUESTIONS
    ]

    return {
        "assessment_version": ASSESSMENT_VERSION,
        "generated_at": moment.isoformat(),
        "assurance_profile": profile,
        "jurisdictions": regions,
        "inventory": inventory,
        "applicable_provisions": applicable,
        "implemented_controls": implemented_controls,
        "outstanding_legal_questions": outstanding,
        "status": "DRAFT_PENDING_LEGAL_REVIEW",
        "may_be_filed_as_complete": False,
        "honest_note": (
            "清单与控制措施是从代码和迁移推导出来的，会随 schema 变化自动更新；"
            f"但 {len(outstanding)} 个法律判断必须由具备资质的人作出。"
            "在它们被回答之前，这份文件是草稿，不是评估。"
        ),
    }


def describe_privacy_assessment() -> dict[str, Any]:
    return {
        "module": "formation_twin.emotional_maturity_privacy_assessment",
        "assessment_version": ASSESSMENT_VERSION,
        "categories": sorted(CATEGORY_PURPOSES),
        "special_categories": sorted(SPECIAL_CATEGORIES),
        "regimes": sorted({entry["regime"] for entry in REGULATORY_MAP}),
        "legal_questions": [question["id"] for question in LEGAL_QUESTIONS],
    }
