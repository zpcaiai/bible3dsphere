"""Executable enforcement for the Guardrails section of every SKILL.md.

Each SKILL.md states its guardrails as policy prose.  This module maps that
prose onto rule *families* with real checks over a skill's output payload.
A guardrail line that matches no family is not silently dropped - it is
reported as ``manual_review`` so coverage stays honest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

Payload = dict[str, Any]
Check = Callable[[Payload, Payload], list[str]]


@dataclass
class GuardrailFinding:
    rule_id: str
    guardrail: str
    status: str  # "pass" | "violation" | "manual_review"
    details: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "guardrail": self.guardrail,
            "status": self.status,
            "details": list(self.details),
        }


@dataclass(frozen=True)
class GuardrailRule:
    rule_id: str
    patterns: tuple[str, ...]
    check: Check
    description: str = ""

    def matches(self, guardrail: str) -> bool:
        return any(re.search(p, guardrail, re.IGNORECASE) for p in self.patterns)


def _text(payload: Payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _iter_dicts(value: Any) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _iter_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_dicts(item)


# --- individual checks -----------------------------------------------------

_DIAGNOSTIC_TERMS = (
    "抑郁症", "焦虑症", "双相", "精神分裂", "人格障碍", "自恋型人格", "PTSD", "ADHD",
)
_HEDGES = ("可能", "似乎", "值得察验", "假设", "may ", "might ", "possible")


def _check_no_clinical_diagnosis(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = []
    for term in _DIAGNOSTIC_TERMS:
        if term in blob and not any(h in blob for h in _HEDGES):
            problems.append(f"输出以断定语气使用临床术语「{term}」")
    return problems


_SALVATION_VERDICTS = ("没得救", "一定下地狱", "神已经定他的罪", "神已定他的罪", "必被咒诅")


def _check_no_salvation_judgment(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出包含得救状态判决「{p}」" for p in _SALVATION_VERDICTS if p in blob]


_ABUSE_PHRASES = ("你还没认够罪", "认罪不够", "神会惩罚你", "必须现在认罪", "被鬼附")


def _check_no_spiritual_abuse(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出包含属灵强迫措辞「{p}」" for p in _ABUSE_PHRASES if p in blob]


def _check_no_mind_reading(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if "interpretation_hypothesis" in node or "possible_pattern" in node:
            if not node.get("alternative_explanations"):
                problems.append(
                    f"动机类判断缺少替代解释: {node.get('hypothesis_id') or node.get('possible_pattern')}"
                )
            if not node.get("evidence_level"):
                problems.append("动机类判断缺少证据等级")
    return problems


def _check_evidence_level_floor(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        level = str(node.get("evidence_level", ""))
        if level in {"E0", "E1", "E2"} and node.get("is_conclusion"):
            problems.append(f"{level} 线索被标记为结论")
    return problems


def _check_no_fabricated_evidence(out: Payload, ctx: Payload) -> list[str]:
    known = set()
    for node in _iter_dicts(ctx):
        for key in ("evidence_id", "claim_id", "source_id", "citation_id", "control_id"):
            if key in node:
                known.add(str(node[key]))
    for key in ("evidence_ids", "known_evidence"):
        for item in ctx.get(key, []) or []:
            known.add(str(item))
    if not known:
        return []
    problems = []
    for node in _iter_dicts(out):
        for ref in node.get("evidence_references", []) or node.get("evidence_links", []) or []:
            if str(ref) not in known:
                problems.append(f"引用了输入中不存在的证据 id: {ref}")
    return problems


def _check_no_ai_self_certification(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        severity = str(node.get("severity", ""))
        decision = str(node.get("decision", "")).lower()
        if severity in {"C3", "C4"} and decision in {"pass", "approved"}:
            if not node.get("human_reviewer") and not node.get("human_review"):
                problems.append(
                    f"高危控制项 {node.get('control_id', '?')} 在无人工复核下被判定通过"
                )
    return problems


def _check_no_blanket_privacy_claim(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = []
    for phrase in ("完全合规", "fully compliant", "全面符合隐私", "GDPR compliant"):
        if phrase in blob:
            problems.append(f"出现笼统的隐私合规声明「{phrase}」")
    return problems


def _check_rollback_required(out: Payload, ctx: Payload) -> list[str]:
    status = str(out.get("status", "")).upper()
    if "APPROVED_FOR_PRODUCTION" in status and not (
        out.get("rollback_target") or out.get("rollback_ready")
    ):
        return ["生产批准缺少回滚目标或回滚演练证据"]
    return []


def _check_no_silent_expiry(out: Payload, ctx: Payload) -> list[str]:
    for node in _iter_dicts(out):
        if "certificate_id" in node and not node.get("expires_at"):
            return [f"证书 {node['certificate_id']} 缺少到期时间"]
    return []


def _check_no_score_override(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("critical_blockers") and str(node.get("decision", "")).lower() in {
            "pass",
            "approved",
        }:
            problems.append("存在关键阻断项时仍给出通过决定")
    return problems


def _check_consent_required(out: Payload, ctx: Payload) -> list[str]:
    consent = ctx.get("consent_scope") or ctx.get("consent") or {}
    if not consent:
        return []
    blob = _text(out)
    problems = []
    if consent.get("allow_gospel_bridge") is False and (
        "gospel_bridge" in out or "福音" in blob
    ):
        problems.append("未获福音桥接同意却输出了福音内容")
    if consent.get("allow_spiritual_analysis") is False and (
        "pride_hypotheses" in out or "desire_map" in out
    ):
        problems.append("未获属灵分析同意却输出了属灵剖析")
    return problems


_PII_KEYS = ("phone", "id_card", "身份证", "address", "住址", "email", "real_name", "真实姓名")


def _check_minimize_pii(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        for key in node:
            if any(p in str(key).lower() for p in _PII_KEYS):
                problems.append(f"输出中出现应最小化的个人信息字段: {key}")
    return problems


def _check_public_material_only(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("public_material_only") is False:
            problems.append("对公众人物使用了非公开材料")
    return problems


def _check_preserve_structural(out: Payload, ctx: Payload) -> list[str]:
    structural_input = any(
        key in _text(ctx) for key in ("structural", "结构", "裁员", "贫困", "创伤")
    )
    if not structural_input:
        return []
    if "structural" not in _text(out) and "结构" not in _text(out):
        return ["输入含结构性因素，但输出未保留结构性归因"]
    return []


_DEFAMATION = ("骗子", "人渣", "垃圾人", "恶棍", "邪教头子")


def _check_no_defamation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出包含诽谤式措辞「{p}」" for p in _DEFAMATION if p in blob]


def _check_minor_protection(out: Payload, ctx: Payload) -> list[str]:
    if ctx.get("possible_minor") and not out.get("human_review_required"):
        return ["涉及未成年人但未要求人工复核"]
    return []


def _check_tenant_isolation(out: Payload, ctx: Payload) -> list[str]:
    expected = ctx.get("tenant_id")
    if not expected:
        return []
    problems = []
    for node in _iter_dicts(out):
        if "tenant_id" in node and node["tenant_id"] != expected:
            problems.append(f"输出跨租户引用: {node['tenant_id']} != {expected}")
    return problems


def _check_disagreement_not_pride(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        observation = str(node.get("observation", ""))
        if node.get("possible_pattern") and observation and (
            "不同意" in observation or "反对" in observation
        ):
            if not node.get("alternative_explanations"):
                problems.append("仅凭不同意见推断自高，且未给出替代解释")
    return problems


def _check_no_compulsive_confession(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    if ctx.get("sensitivity") == "mental_health" or "scrupulosity" in _text(ctx):
        problems = []
        for phrase in ("继续省察你的罪", "还需要更深的认罪", "再仔细找找你的罪"):
            if phrase in blob:
                problems.append(f"对强迫性认罪风险用户输出了加压措辞「{phrase}」")
        return problems
    return []


def _check_no_new_revelation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = []
    for phrase in ("神对你说", "神告诉我你", "我从神领受关于你"):
        if phrase in blob:
            problems.append(f"输出以先知口吻代神发言「{phrase}」")
    return problems


def _check_human_review_preserved(out: Payload, ctx: Payload) -> list[str]:
    dissent = ctx.get("human_reviews") or []
    if not dissent:
        return []
    recorded = _text(out)
    problems = []
    for review in dissent:
        if isinstance(review, dict) and review.get("dissent"):
            marker = str(review.get("reviewer") or review.get("review_id") or "")
            if marker and marker not in recorded:
                problems.append(f"人工异议未被保留: {marker}")
    return problems


# --- extended check families ------------------------------------------------

_TRAUMA_DISMISSALS = (
    "你想多了", "没那么严重", "过去了就别提", "别再抓着不放", "这不算什么",
    "你太敏感", "早该放下",
)


def _check_no_trauma_invalidation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出否定了用户所报的伤害「{p}」" for p in _TRAUMA_DISMISSALS if p in blob]


_FORCED_RECONCILIATION = (
    "必须马上和好", "必须原谅", "不恢复接触就不算饶恕", "应该回到他身边",
    "先和解再谈", "不和好就是不顺服",
)


def _check_no_forced_reconciliation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = [f"输出要求强制和解「{p}」" for p in _FORCED_RECONCILIATION if p in blob]
    if ctx.get("abuse_present") and "饶恕" in blob and "安全" not in blob:
        problems.append("在施虐情境下谈饶恕却未同时处理安全")
    return problems


_SCRUPULOSITY_AMPLIFIERS = (
    "继续省察你的罪", "还需要更深的认罪", "再仔细找找你的罪", "你认得还不够",
    "再多认一次", "还有没有隐藏的罪",
)


def _check_no_scrupulosity_amplification(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = [f"输出放大了强迫性自我审查「{p}」" for p in _SCRUPULOSITY_AMPLIFIERS if p in blob]
    scrupulous = ctx.get("sensitivity") == "mental_health" or "scrupulosity" in _text(ctx)
    if scrupulous and problems:
        problems.append("用户处于强迫性认罪风险中，此类措辞必须移除")
    return problems


def _check_no_disabling_recertification(out: Payload, ctx: Payload) -> list[str]:
    for node in _iter_dicts(out):
        if node.get("recertification_enabled") is False:
            return ["输出关闭了持续复检"]
        if "certificate_id" in node and node.get("recertification_triggers") == []:
            return ["证书未声明任何复检触发条件"]
    return []


_QUESTION_MARKS = ("?", "？")


def _check_no_hidden_multi_question(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        for key in ("question", "next_question", "priority_question", "prompt_question"):
            value = node.get(key)
            if isinstance(value, str):
                count = sum(value.count(m) for m in _QUESTION_MARKS)
                if count > 1:
                    problems.append(f"单轮问题里藏了 {count} 个问句: {value[:40]}")
    return problems


_CHRIST_MARKERS = ("基督", "耶稣", "Christ", "十字架", "福音")
_PRACTICE_KEYS = ("practice", "practices", "actionable_response", "next_step")


def _check_no_moralism(out: Payload, ctx: Payload) -> list[str]:
    has_practice = any(
        key in node for node in _iter_dicts(out) for key in _PRACTICE_KEYS
    )
    if not has_practice:
        return []
    blob = _text(out)
    if not any(marker in blob for marker in _CHRIST_MARKERS):
        return ["输出只给了行为清单，没有基督的位格与工作"]
    return []


_REPENTANCE_MARKERS = ("悔改", "认罪", "罪", "转向", "repent")


def _check_no_cheap_grace(out: Payload, ctx: Payload) -> list[str]:
    gospel_nodes = [
        node
        for node in _iter_dicts(out)
        if "gospel_bridge" in node or "christ_person_and_work" in node or "gospel_path" in node
    ]
    if not gospel_nodes:
        return []
    blob = _text(out)
    if not any(marker in blob for marker in _REPENTANCE_MARKERS):
        return ["福音输出未指明罪与悔改，落入廉价恩典"]
    return []


_PROSPERITY_PROMISES = (
    "必得医治", "一定会富足", "神必赐你成功", "信了就不再受苦", "必然脱贫",
    "保证得到", "立刻解决所有痛苦",
)


def _check_no_prosperity_promises(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出作出成功神学式承诺「{p}」" for p in _PROSPERITY_PROMISES if p in blob]


def _check_no_denominational_overreach(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        tier = str(node.get("tier", ""))
        if tier in {"D2", "D3", "tier2", "tier3"}:
            labelled = (
                node.get("tradition_label")
                or node.get("tradition_scope")
                or node.get("denominational_label")
            )
            if not labelled:
                problems.append(f"{tier} 层教义未标注传统归属即作普遍陈述")
    return problems


_SALVATION_SCORE_KEYS = ("salvation_score", "得救分数", "salvation_probability", "assurance_score")


def _check_no_salvation_scoring(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        for key in node:
            if str(key).lower() in _SALVATION_SCORE_KEYS:
                problems.append(f"输出为得救状态打分: {key}")
    return problems


_MATURITY_SCORE_KEYS = (
    "maturity_score", "spiritual_score", "overall_maturity", "成熟度分数", "属灵分数",
)


def _check_no_single_maturity_score(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        for key in node:
            if str(key).lower() in _MATURITY_SCORE_KEYS:
                problems.append(f"输出给出单一属灵成熟度总分: {key}")
    return problems


_VICTIM_BLAMING = (
    "是你自己招来的", "你也有责任被打", "苍蝇不叮无缝的蛋", "你要先反省自己为什么被",
    "如果你顺服一点就不会",
)


def _check_no_victim_blaming(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出包含责备受害者的措辞「{p}」" for p in _VICTIM_BLAMING if p in blob]


def _check_no_public_person_private_twin(out: Payload, ctx: Payload) -> list[str]:
    subject = str(ctx.get("subject_type") or (ctx.get("case") or {}).get("subject_type", ""))
    if subject != "person":
        return []
    twin_keys = ("formation_chain", "formation_twin", "identity_migration", "window_review")
    for node in _iter_dicts(out):
        for key in twin_keys:
            if key in node:
                return [f"为公众人物构建了纵向塑造画像: {key}"]
    return []


_CARE_REFERRAL_MARKERS = ("专业", "牧者", "医疗", "心理", "热线", "转介", "professional")


def _check_no_replacing_professional_care(out: Payload, ctx: Payload) -> list[str]:
    risky = str(ctx.get("sensitivity", "")) in {"crisis", "abuse", "mental_health"} or any(
        node.get("risk_level") in {"high", "critical"} for node in _iter_dicts(out)
    )
    if not risky:
        return []
    blob = _text(out)
    if not any(marker in blob for marker in _CARE_REFERRAL_MARKERS):
        return ["高风险情境下未指向教会或专业照护，等同于取代专业帮助"]
    return []


_DETERMINISTIC_WORDS = ("一定会", "必然会", "肯定会", "will certainly", "必将")


def _check_no_deterministic_prediction(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    blob = _text(out)
    for word in _DETERMINISTIC_WORDS:
        if word in blob:
            problems.append(f"输出作出确定性预测「{word}」")
    for node in _iter_dicts(out):
        for key in ("probability", "certainty"):
            value = node.get(key)
            if isinstance(value, (int, float)) and value >= 1:
                problems.append(f"{key} 被设为 {value}，等于宣称确定性")
    return problems


def _check_no_unlimited_pastoral_access(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if "allowed_fields" in node or "disclosure_id" in node:
            if not node.get("expires_at"):
                problems.append("披露未设置到期时间，构成无限期访问")
            if not node.get("purpose"):
                problems.append("披露未声明用途，构成无限用途访问")
    return problems


_SURVEILLANCE_MARKERS = (
    "偷偷监控", "不让他知道", "查看全部聊天记录", "定位追踪", "covert monitoring",
)


def _check_no_surveillance_accountability(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    problems = [f"输出建议监控式问责「{p}」" for p in _SURVEILLANCE_MARKERS if p in blob]
    for node in _iter_dicts(out):
        if node.get("covert") is True or node.get("notify_subject") is False:
            problems.append("问责安排对当事人不透明")
    return problems


def _check_no_hidden_resharing(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("recipient_actor_id") or node.get("shared_with"):
            if not (node.get("basis") or node.get("consent_id") or node.get("audit_id")):
                problems.append("再次共享缺少同意依据或审计记录")
    return problems


def _check_no_internal_only_abuse(out: Payload, ctx: Payload) -> list[str]:
    abuse = bool(ctx.get("abuse_present")) or str(ctx.get("sensitivity", "")) == "abuse"
    if not abuse:
        return []
    blob = _text(out)
    problems = []
    if "内部处理" in blob and "报告" not in blob and "external" not in blob:
        problems.append("可报告的虐待被限制为内部处理")
    for node in _iter_dicts(out):
        if node.get("external_report_required") is False and node.get("reportable") is True:
            problems.append("可报告事项被标记为无需外部报告")
    return problems


_PROFESSIONAL_DOMAINS = ("诊断", "处方", "用药", "起诉", "法律意见", "投资", "报税")


def _check_no_professional_claims_without_review(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    hits = [d for d in _PROFESSIONAL_DOMAINS if d in blob]
    if not hits:
        return []
    reviewed = any(
        node.get("human_reviewer") or node.get("qualified_review") or node.get("reviewer")
        for node in _iter_dicts(out)
    )
    if reviewed:
        return []
    return [f"输出涉及专业领域 {hits} 但无合资格复核"]


def _check_no_proof_texting(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("used_as_proof"):
            has_context = any(
                node.get(key)
                for key in (
                    "context", "literary_context", "historical_context",
                    "passage_context", "discourse", "canonical_context",
                )
            )
            if not has_context:
                problems.append("经文被当作证据引用但未提供语境")
    return problems


def _check_no_strong_number_only(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("strong_number") or node.get("strongs"):
            if not (
                node.get("corpus_usage")
                or node.get("context_usage")
                or node.get("usage_examples")
            ):
                problems.append("词义仅依据 Strong 编号，缺少语料用法证据")
    return problems


def _check_no_copyright_leakage(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    limit = int(ctx.get("quote_char_limit", 500))
    for node in _iter_dicts(out):
        quote = node.get("quote_text") or node.get("quote")
        if isinstance(quote, str) and len(quote) > limit:
            problems.append(f"引文长度 {len(quote)} 超过许可上限 {limit}")
        status = str(node.get("rights_status", ""))
        if status in {
            "prohibited_for_embedding",
            "prohibited_for_generation",
            "metadata_only",
        } and quote:
            problems.append(f"权利状态 {status} 的材料仍被引用原文")
    return problems


_CERTAINTY_WORDS = ("毫无疑问", "显然就是", "可以确定", "certainly", "无可争辩")


def _check_no_unsupported_certainty(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    hits = [w for w in _CERTAINTY_WORDS if w in blob]
    if not hits:
        return []
    strong = any(
        str(node.get("evidence_level", "")) in {"E3", "E4"} for node in _iter_dicts(out)
    )
    return [] if strong else [f"使用确定性措辞 {hits} 但无 E3/E4 证据支持"]


_ABUSIVE_SCRIPTURE = (
    "圣经说你必须顺服我", "神要你忍耐不要离开", "不听我的就是不听神的",
    "你若真信就不会质疑",
)


def _check_no_abusive_scripture_application(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"经文被用于施压「{p}」" for p in _ABUSIVE_SCRIPTURE if p in blob]


def _check_no_offline_external_verification(out: Payload, ctx: Payload) -> list[str]:
    if ctx.get("network_available"):
        return []
    return [
        "离线状态下把外部事实标记为已核实"
        for node in _iter_dicts(out)
        if node.get("externally_verified") is True
    ]


_DEMONISATION = ("就是魔鬼", "撒但的工具", "都是邪灵", "魔鬼的思想")


def _check_no_blanket_demonisation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出把观点简单标记为魔鬼「{p}」" for p in _DEMONISATION if p in blob]


_DIGNITY_VIOLATION = ("这种人不配", "低等", "愚民", "没救的人", "废物一个")


def _check_no_dignity_violation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出贬低人格尊严「{p}」" for p in _DIGNITY_VIOLATION if p in blob]


_HARASSMENT_TOOLING = ("开盒", "人肉", "网暴", "举报轰炸", "身份追踪", "扒出他的")


def _check_no_harassment_tooling(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出可用于骚扰「{p}」" for p in _HARASSMENT_TOOLING if p in blob]


def _check_no_extreme_sampling(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        strategy = str(node.get("sampling_strategy", ""))
        if strategy in {"most_extreme", "top_outliers"}:
            problems.append(f"仅采样最极端内容: {strategy}")
        total = node.get("corpus_size")
        sampled = node.get("sample_size")
        if isinstance(total, int) and isinstance(sampled, int) and total >= 10 and sampled <= 1:
            problems.append(f"从 {total} 条材料中只取 {sampled} 条即下结论")
    return problems


def _check_no_malice_from_rhetoric(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("malice_inferred") and not node.get("behavioral_evidence"):
            problems.append("仅凭修辞强度推断恶意，无行为证据")
        if node.get("possible_pattern") and node.get("rhetoric_only") is True:
            problems.append("模式判断只建立在修辞之上")
    return problems


def _check_no_commercialisation_as_sin(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [
        f"把商业化本身视为罪「{p}」"
        for p in ("收费本身就是罪", "卖课就是贪财", "商业化即堕落")
        if p in blob
    ]


_PLATFORM_MANIPULATION = ("刷量", "规避平台审核", "操纵推荐算法", "买粉", "养号")


def _check_no_platform_manipulation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"输出提供平台操纵方案「{p}」" for p in _PLATFORM_MANIPULATION if p in blob]


def _check_no_private_family_analysis(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        relation = str(node.get("relation", ""))
        if relation in {"spouse", "child", "parent", "配偶", "子女", "父母"}:
            if not node.get("is_public_figure"):
                problems.append(f"分析了非公开家庭成员: {relation}")
    return problems


def _check_aggregate_by_default(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("audience_segment") or node.get("follower_profile"):
            if node.get("aggregated") is False or node.get("individual_ids"):
                problems.append("受众分析暴露了个体身份，未默认聚合")
    return problems


_DIVINE_VERDICT_ON_VIRALITY = (
    "爆火说明神喜悦", "神在祝福他的事工", "这是神的审判", "神让他红是因为",
)


def _check_no_divine_verdict_on_virality(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [
        f"把流量解释为神的认可或审判「{p}」"
        for p in _DIVINE_VERDICT_ON_VIRALITY
        if p in blob
    ]


def _check_no_counterfactual_excusing_harm(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("counterfactual") and node.get("harm_dismissed"):
            problems.append("用反事实推理为真实伤害开脱")
    blob = _text(out)
    for phrase in ("如果不是他别人也会", "换成谁都一样，所以不算伤害"):
        if phrase in blob:
            problems.append(f"反事实被用于开脱「{phrase}」")
    return problems


_OVER_CRIMINALISATION = ("看这类内容就是犯罪", "娱乐本身就是罪", "凡是刷视频的都在堕落")


def _check_no_entertainment_criminalisation(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    return [f"把一般娱乐使用罪化「{p}」" for p in _OVER_CRIMINALISATION if p in blob]


_INTERNAL_ONLY_KEYS = (
    "pride_hypotheses", "desire_map", "safety_decisions", "internal_notes", "raw_inference",
)


def _check_hide_internal_inferences(out: Payload, ctx: Payload) -> list[str]:
    view = out.get("redacted_user_view") or out.get("user_view")
    if not isinstance(view, dict):
        return []
    leaked = [key for key in _INTERNAL_ONLY_KEYS if key in view]
    return [f"用户版泄露了内部推断字段: {leaked}"] if leaked else []


_HIGH_RISK_DOMAINS = ("用药", "手术", "诉讼", "报税", "投资", "贷款")


def _check_high_risk_domain_routing(out: Payload, ctx: Payload) -> list[str]:
    blob = _text(out)
    hits = [d for d in _HIGH_RISK_DOMAINS if d in blob]
    if not hits:
        return []
    routed = any(
        node.get("human_review_required") or node.get("escalated") or node.get("referral")
        for node in _iter_dicts(out)
    )
    return [] if routed else [f"涉及高风险领域 {hits} 但未进入专项安全流程"]


def _check_no_clip_as_whole_person(out: Payload, ctx: Payload) -> list[str]:
    problems = []
    for node in _iter_dicts(out):
        if node.get("clip_based") and node.get("scope") == "whole_person":
            problems.append("以剪辑片段代表完整人格")
        if node.get("source_span_count") == 1 and node.get("character_claim"):
            problems.append("单一片段被用来断定人格")
    return problems


_SENSITIVE_ATTRS = ("race", "ethnicity", "religion_label", "sexual_orientation", "种族", "性取向")


def _check_sensitive_attributes_restricted(out: Payload, ctx: Payload) -> list[str]:
    provided = set(ctx.get("user_provided_attributes", []) or [])
    problems = []
    for node in _iter_dicts(out):
        for key in node:
            if any(attr in str(key).lower() for attr in _SENSITIVE_ATTRS):
                if key not in provided and not node.get("aggregated"):
                    problems.append(f"使用了未经用户提供且非聚合的敏感属性: {key}")
    return problems


_MONETIZATION_DIMENSIONS = {
    "disclosure": ("disclosure", "披露", "透明"),
    "honesty": ("honesty", "诚实", "真实性"),
    "fit": ("fit", "适配", "适用性"),
    "vulnerability": ("vulnerability", "脆弱", "利用"),
}


def _check_monetization_risk_dimensions(out: Payload, ctx: Payload) -> list[str]:
    """Business-model analysis must cover all four declared risk dimensions."""

    analysed = any(
        key in node
        for node in _iter_dicts(out)
        for key in ("business_model", "monetization", "monetization_analysis", "revenue_model")
    )
    if not analysed:
        return []
    blob = _text(out).lower()
    missing = [
        name
        for name, markers in _MONETIZATION_DIMENSIONS.items()
        if not any(marker.lower() in blob for marker in markers)
    ]
    return [f"商业模式分析缺少风险维度: {missing}"] if missing else []


def _check_distinguish_grace_levels(out: Payload, ctx: Payload) -> list[str]:
    for node in _iter_dicts(out):
        if "creation_good" in node and "fall_distortion" in node:
            if not node.get("creation_good"):
                return ["世界观映射只给了负面标签，未区分真理碎片与共同恩典"]
            return []
    return []


# --- rule table ------------------------------------------------------------

RULES: tuple[GuardrailRule, ...] = (
    GuardrailRule("no_clinical_diagnosis", (r"clinical diagnos", r"诊断", r"临床"),
                  _check_no_clinical_diagnosis, "不作临床诊断"),
    GuardrailRule("no_salvation_judgment", (r"salvation judgment", r"得救", r"定罪", r"咒诅"),
                  _check_no_salvation_judgment, "不判定得救状态"),
    GuardrailRule("no_spiritual_abuse", (r"spiritual abuse", r"羞辱", r"强迫", r"coerc"),
                  _check_no_spiritual_abuse, "不进行属灵强迫或羞辱"),
    GuardrailRule("no_mind_reading", (r"读心", r"mind.?read", r"inner state", r"内心"),
                  _check_no_mind_reading, "不宣称读取内心"),
    GuardrailRule("evidence_level_floor", (r"E0-E2", r"证据等级", r"evidence level"),
                  _check_evidence_level_floor, "低证据等级不得作为结论"),
    GuardrailRule("no_fabricated_evidence", (r"fabricat", r"伪造", r"编造"),
                  _check_no_fabricated_evidence, "不得伪造证据或签名"),
    GuardrailRule("no_ai_self_certification", (r"No AI", r"self-certif", r"AI-only", r"自证"),
                  _check_no_ai_self_certification, "AI 不得自证高危控制项"),
    GuardrailRule("no_blanket_privacy_claim", (r"blanket privacy", r"privacy compliance", r"隐私合规"),
                  _check_no_blanket_privacy_claim, "不作笼统隐私合规声明"),
    GuardrailRule("rollback_required", (r"rollback", r"回滚"),
                  _check_rollback_required, "无回滚不得部署"),
    GuardrailRule("no_silent_expiry", (r"silent.*expiry", r"expiry", r"到期"),
                  _check_no_silent_expiry, "证书不得静默过期"),
    GuardrailRule("no_score_override", (r"score-based override", r"override.*critical", r"分数.*覆盖"),
                  _check_no_score_override, "分数不得覆盖关键失败"),
    GuardrailRule("consent_required", (r"consent", r"同意", r"授权"),
                  _check_consent_required, "越权内容需先获同意"),
    GuardrailRule("minimize_pii", (r"minimum necessary", r"最小化", r"privacy", r"隐私", r"PII"),
                  _check_minimize_pii, "最小化保存个人信息"),
    GuardrailRule("public_material_only", (r"公开材料", r"public material", r"public figure", r"公众人物"),
                  _check_public_material_only, "公众人物只评公开材料"),
    GuardrailRule("preserve_structural", (r"structural", r"结构性", r"structural injustice"),
                  _check_preserve_structural, "保留结构性因素"),
    GuardrailRule("no_defamation", (r"defam", r"诽谤", r"libel"),
                  _check_no_defamation, "避免诽谤式措辞"),
    GuardrailRule("minor_protection", (r"未成年", r"minor", r"child"),
                  _check_minor_protection, "未成年人保护"),
    GuardrailRule("tenant_isolation", (r"tenant", r"租户", r"isolation"),
                  _check_tenant_isolation, "租户隔离"),
    GuardrailRule("disagreement_not_pride", (r"disagreement", r"不同意"),
                  _check_disagreement_not_pride, "不把异见等同于骄傲"),
    GuardrailRule("no_compulsive_confession", (r"compulsive confession", r"强迫性认罪", r"认罪"),
                  _check_no_compulsive_confession, "不放大强迫性认罪"),
    GuardrailRule("no_new_revelation", (r"revelation", r"启示", r"替神发言", r"prophe"),
                  _check_no_new_revelation, "不宣称新启示"),
    GuardrailRule("human_review_preserved", (r"dissent", r"human review", r"人工复核", r"异议"),
                  _check_human_review_preserved, "保留人工异议"),
    GuardrailRule("no_trauma_invalidation", (r"trauma invalidation", r"创伤", r"real harm", r"否定伤害"),
                  _check_no_trauma_invalidation, "不否定真实创伤"),
    GuardrailRule("no_forced_reconciliation", (r"forced reconciliation", r"强制和解", r"reconcil"),
                  _check_no_forced_reconciliation, "不强制和解"),
    GuardrailRule("no_scrupulosity_amplification", (r"scrupulosity", r"过度认罪", r"自我审查"),
                  _check_no_scrupulosity_amplification, "不放大强迫性自我审查"),
    GuardrailRule("no_disabling_recertification", (r"recertification", r"持续复检", r"复检"),
                  _check_no_disabling_recertification, "不得关闭持续复检"),
    GuardrailRule("no_hidden_multi_question", (r"multi-question", r"多个问题", r"one question", r"一个问题"),
                  _check_no_hidden_multi_question, "单轮只问一个问题"),
    GuardrailRule("no_moralism", (r"moralism", r"道德主义", r"行为清单"),
                  _check_no_moralism, "不退化为道德说教"),
    GuardrailRule("no_cheap_grace", (r"cheap grace", r"廉价恩典"),
                  _check_no_cheap_grace, "不落入廉价恩典"),
    GuardrailRule("no_prosperity_promises", (r"prosperity", r"成功神学", r"繁荣福音"),
                  _check_no_prosperity_promises, "不作成功神学承诺"),
    GuardrailRule("no_denominational_overreach", (r"denomination", r"宗派", r"传统归属"),
                  _check_no_denominational_overreach, "宗派立场不得冒充普遍"),
    GuardrailRule("no_salvation_scoring", (r"salvation scoring", r"得救分数", r"salvation score"),
                  _check_no_salvation_scoring, "不为得救打分"),
    GuardrailRule("no_single_maturity_score", (r"maturity score", r"成熟度", r"single .*score"),
                  _check_no_single_maturity_score, "不给单一属灵总分"),
    GuardrailRule("no_victim_blaming", (r"victim blaming", r"责备受害者", r"victim-blam"),
                  _check_no_victim_blaming, "不责备受害者"),
    GuardrailRule("no_public_person_private_twin", (r"private twin", r"private Formation Twin", r"公众人物.*画像"),
                  _check_no_public_person_private_twin, "不为公众人物建纵向画像"),
    GuardrailRule("no_replacing_professional_care", (r"replacing church", r"professional care", r"替代专业", r"取代"),
                  _check_no_replacing_professional_care, "不取代教会或专业照护"),
    GuardrailRule("no_deterministic_prediction", (r"deterministic prediction", r"确定性预测", r"predict"),
                  _check_no_deterministic_prediction, "不作确定性预测"),
    GuardrailRule("no_unlimited_pastoral_access", (r"unlimited pastoral access", r"无限.*访问", r"unlimited"),
                  _check_no_unlimited_pastoral_access, "牧养访问必须有范围与期限"),
    GuardrailRule("no_surveillance_accountability", (r"surveillance", r"监控"),
                  _check_no_surveillance_accountability, "不做监控式问责"),
    GuardrailRule("no_hidden_resharing", (r"re-sharing", r"resharing", r"再次共享", r"hidden.*shar"),
                  _check_no_hidden_resharing, "共享必须留痕"),
    GuardrailRule("no_internal_only_abuse", (r"internal-only", r"reportable abuse", r"内部处理"),
                  _check_no_internal_only_abuse, "可报告虐待不得只在内部处理"),
    GuardrailRule("no_professional_claims_without_review", (r"professional claims", r"qualified review", r"专业"),
                  _check_no_professional_claims_without_review, "专业结论需合资格复核"),
    GuardrailRule("no_proof_texting", (r"proof-text", r"proof text", r"断章取义"),
                  _check_no_proof_texting, "不断章取义引用经文"),
    GuardrailRule("no_strong_number_only", (r"Strong-number", r"Strong's", r"strong number"),
                  _check_no_strong_number_only, "词义不得只靠 Strong 编号"),
    GuardrailRule("no_copyright_leakage", (r"copyright", r"版权", r"leakage"),
                  _check_no_copyright_leakage, "不泄露受版权保护内容"),
    GuardrailRule("no_unsupported_certainty", (r"unsupported certainty", r"过度确定", r"certainty"),
                  _check_no_unsupported_certainty, "确定性措辞需 E3/E4 支持"),
    GuardrailRule("no_abusive_scripture_application", (r"abusive scripture", r"经文.*施压", r"scripture application"),
                  _check_no_abusive_scripture_application, "不以经文施压"),
    GuardrailRule("no_offline_external_verification", (r"不联网", r"外部事实", r"已核实"),
                  _check_no_offline_external_verification, "离线不得标记外部已核实"),
    GuardrailRule("no_blanket_demonisation", (r"魔鬼", r"demon"),
                  _check_no_blanket_demonisation, "不把观点简单标记为魔鬼"),
    GuardrailRule("no_dignity_violation", (r"人格尊严", r"dignity", r"贬低"),
                  _check_no_dignity_violation, "不贬低人格尊严"),
    GuardrailRule("no_harassment_tooling", (r"骚扰", r"开盒", r"人肉", r"网暴", r"举报轰炸", r"harass"),
                  _check_no_harassment_tooling, "不得成为骚扰工具"),
    GuardrailRule("no_extreme_sampling", (r"最极端", r"extreme.*sampl", r"采样"),
                  _check_no_extreme_sampling, "不以极端样本下结论"),
    GuardrailRule("no_malice_from_rhetoric", (r"修辞", r"rhetoric", r"恶意"),
                  _check_no_malice_from_rhetoric, "不从修辞直接推断恶意"),
    GuardrailRule("no_commercialisation_as_sin", (r"商业化", r"commercial"),
                  _check_no_commercialisation_as_sin, "商业化本身不等于罪"),
    GuardrailRule("no_platform_manipulation", (r"刷量", r"平台安全", r"操纵推荐", r"platform"),
                  _check_no_platform_manipulation, "不提供平台操纵方案"),
    GuardrailRule("no_private_family_analysis", (r"家庭成员", r"family member", r"非公开"),
                  _check_no_private_family_analysis, "不分析非公开家庭成员"),
    GuardrailRule("aggregate_by_default", (r"聚合", r"aggregate", r"粉丝身份"),
                  _check_aggregate_by_default, "受众数据默认聚合"),
    GuardrailRule("no_divine_verdict_on_virality", (r"神认可", r"神审判", r"爆火"),
                  _check_no_divine_verdict_on_virality, "流量不是神的判决"),
    GuardrailRule("no_counterfactual_excusing_harm", (r"反事实", r"counterfactual"),
                  _check_no_counterfactual_excusing_harm, "反事实不得开脱伤害"),
    GuardrailRule("no_entertainment_criminalisation", (r"娱乐", r"过度恐惧", r"罪化"),
                  _check_no_entertainment_criminalisation, "不把一般娱乐罪化"),
    GuardrailRule("hide_internal_inferences", (r"内部敏感推断", r"内部推断", r"internal inference"),
                  _check_hide_internal_inferences, "用户版隐藏内部推断"),
    GuardrailRule("high_risk_domain_routing", (r"高风险医疗", r"法律", r"财务", r"专项安全流程"),
                  _check_high_risk_domain_routing, "高风险领域走专项流程"),
    GuardrailRule("no_clip_as_whole_person", (r"剪辑片段", r"完整人格", r"clip"),
                  _check_no_clip_as_whole_person, "不以片段代表完整人格"),
    GuardrailRule("sensitive_attributes_restricted", (r"敏感人口属性", r"sensitive attribute", r"人口属性"),
                  _check_sensitive_attributes_restricted, "敏感属性受限使用"),
    GuardrailRule("distinguish_grace_levels", (r"真理碎片", r"共同恩典", r"偶像化", r"明确恶行"),
                  _check_distinguish_grace_levels, "区分真理碎片与共同恩典"),
    GuardrailRule("monetization_risk_dimensions", (r"披露、诚实", r"适配性", r"利用脆弱性", r"monetization"),
                  _check_monetization_risk_dimensions, "商业模式分析须覆盖四个风险维度"),
)

RULES_BY_ID = {rule.rule_id: rule for rule in RULES}


def enforce(
    guardrails: Iterable[str], output: Payload, context: Payload | None = None
) -> list[GuardrailFinding]:
    """Run every guardrail line of a contract against a skill output."""

    context = context or {}
    findings: list[GuardrailFinding] = []
    for guardrail in guardrails:
        matched = [rule for rule in RULES if rule.matches(guardrail)]
        if not matched:
            findings.append(
                GuardrailFinding("manual_review", guardrail, "manual_review",
                                 ["无自动规则覆盖，需人工复核"])
            )
            continue
        for rule in matched:
            problems = rule.check(output, context)
            findings.append(
                GuardrailFinding(
                    rule.rule_id,
                    guardrail,
                    "violation" if problems else "pass",
                    problems,
                )
            )
    return findings


def violations(findings: Iterable[GuardrailFinding]) -> list[GuardrailFinding]:
    return [f for f in findings if f.status == "violation"]


def coverage(findings: Iterable[GuardrailFinding]) -> dict[str, int]:
    counts = {"pass": 0, "violation": 0, "manual_review": 0}
    for finding in findings:
        counts[finding.status] = counts.get(finding.status, 0) + 1
    return counts
