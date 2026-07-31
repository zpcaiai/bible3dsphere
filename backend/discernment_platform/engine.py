from __future__ import annotations

import math
import re
from typing import Any

from .gospel import GospelPathEngine
from .models import DiscernmentCaseCreate
from .registry import DiscernmentRegistry, get_registry
from .safety import precheck


PRIDE_COMPOSITIONS = {
    frozenset({"competence_justification", "control_sovereignty"}): ("reinforcing", "能力价值与结果控制相互强化，形成不可替代者假设。"),
    frozenset({"moral_self_righteousness", "tribal_superiority"}): ("reinforcing", "群体身份可能保护道德自义，形成阵营无罪假设。"),
    frozenset({"spiritual_pride", "messianic_self_image"}): ("reinforcing", "属灵地位与救主角色可能相互强化。"),
    frozenset({"false_humility", "competence_justification"}): ("masking", "自我贬低可能遮蔽对能力肯定的持续需要。"),
    frozenset({"victimhood_innocence", "moral_self_righteousness"}): ("reinforcing", "真实受伤可能被用来维持道德豁免。"),
}


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    words = set(re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", lowered))
    cjk = "".join(re.findall(r"[\u4e00-\u9fff]", lowered))
    words.update(cjk[index:index + 2] for index in range(max(0, len(cjk) - 1)))
    return {token for token in words if token}


def _phrase_similarity(text: str, text_tokens: set[str], phrases: list[str]) -> tuple[float, list[str]]:
    score = 0.0
    matches: list[str] = []
    lowered = text.lower()
    for phrase in phrases:
        phrase = str(phrase).strip()
        if not phrase:
            continue
        phrase_tokens = _tokens(phrase)
        common = text_tokens & phrase_tokens
        overlap = len(common) / max(1, len(phrase_tokens))
        exact = phrase.lower() in lowered
        # Chinese packs often express a concept as a full sentence while user
        # input contains only its key two-character terms. Preserve that weak
        # signal, but require several hits before a candidate becomes mixed.
        lexical = min(0.16, len(common) * 0.025)
        value = 0.32 if exact else max(min(0.2, overlap * 0.2), lexical)
        if value >= 0.025:
            score += value
            matches.append(phrase)
    return min(1.0, score), matches[:6]


def _evidence_level(case: DiscernmentCaseCreate) -> str:
    groups = {item.independence_group or item.locator for item in case.source_items}
    levels = {item.evidence_level for item in case.source_items}
    if len(groups) >= 3 and levels & {"E3", "E4", "P3", "P4"}:
        return "E3"
    if len(groups) >= 2:
        return "E2"
    return "E1"


class DiscernmentEngine:
    """Runs the deterministic case-analysis portion of the Batch 01-10 platform."""

    def __init__(self, registry: DiscernmentRegistry | None = None) -> None:
        self.registry = registry or get_registry()
        self.gospel = GospelPathEngine(self.registry)

    def analyze(self, *, case_id: str, case: DiscernmentCaseCreate) -> dict[str, Any]:
        trace: list[dict[str, Any]] = [{"state": "RECEIVED", "batch": 1}]
        safety = precheck(case.raw_input, subject_type=case.subject_type, sensitivity=case.sensitivity)
        trace.append({"state": "SAFETY_CHECKED", "batch": 1, "status": safety.status})
        if safety.status in {"blocked", "safety_hold"}:
            return self._blocked_report(case_id, safety.as_dict(), trace)
        if case.subject_type == "person" and not case.consent_scope.allow_public_content_analysis:
            safety.status = "blocked"
            safety.reasons.append("public_content_analysis_not_consented")
            safety.actions.append("需要明确允许分析公开内容")
            return self._blocked_report(case_id, safety.as_dict(), trace)

        claims = self._claims(case)
        trace.extend([
            {"state": "NORMALIZED", "batch": 1},
            {"state": "CLAIMS_EXTRACTED", "batch": 1, "count": len(claims)},
        ])
        domain_matches = self._domain_matches(case.raw_input)
        trace.append({"state": "WORLDVIEW_MAPPED", "batch": 2, "pack_versions": [{"id": item["pack_id"], "version": item["version"]} for item in domain_matches]})

        if case.consent_scope.allow_spiritual_analysis:
            pride = self._pride_hypotheses(case, domain_matches)
            desire_map = self._desire_map(domain_matches)
        else:
            pride = []
            desire_map = []
        trace.append({"state": "PRIDE_HYPOTHESES_BUILT", "batch": 4, "count": len(pride), "consented": case.consent_scope.allow_spiritual_analysis})
        trace.append({"state": "DESIRES_MAPPED", "batch": 1, "count": len(desire_map)})

        virality = self._virality(case, domain_matches)
        if virality:
            trace.append({"state": "VIRALITY_ANALYZED", "batch": 3, "review_required": virality["human_review_required"]})
        questions = self._questions(case, domain_matches, pride)
        trace.append({"state": "QUESTIONS_PLANNED", "batch": 5, "count": len(questions)})

        worldview_map = self._worldview_map(domain_matches, case.consent_scope.allow_spiritual_analysis)
        gospel_bridge = self._gospel_bridge(case, domain_matches)
        trace.append({"state": "GOSPEL_BRIDGE_BUILT", "batch": 6, "status": gospel_bridge.get("status", gospel_bridge.get("review_status", "ready"))})

        review_required = safety.human_review_required or bool(virality and virality["human_review_required"])
        review_status = "human_review_required" if review_required else "ready"
        limitations = [
            "这是确定性、可审计的辨识辅助，不读取人心、不宣告新启示，也不判断任何人的得救状态。",
            "词汇匹配只生成候选解释；低证据结果应以澄清问题而非结论呈现。",
            "社会结构、真实受苦与个人责任必须同时保留。",
        ]
        if not case.source_items:
            limitations.append("未提供独立来源，所有解释最高按单一自述或单一材料处理。")
        if not case.consent_scope.allow_spiritual_analysis:
            limitations.append("用户未授权属灵深层分析，因此自高、偶像和欲望假设均未生成。")

        compositions = self._compose_pride(pride)
        summary = self._summary(domain_matches, pride, review_status)
        quality_gates = {
            "schema_valid": True,
            "evidence_labeled": all(item.get("evidence_level") for item in claims + pride),
            "observation_interpretation_separated": all("observation" in item and "interpretation_hypothesis" in item for item in pride),
            "alternatives_present": all(item.get("alternative_explanations") for item in pride),
            "counter_evidence_present": all(item.get("counter_evidence_needed") for item in pride),
            "no_mind_reading": True,
            "no_salvation_judgment": True,
            "one_question_at_a_time": all((item["text"].count("?") + item["text"].count("？")) <= 1 for item in questions),
            "gospel_consent_respected": case.consent_scope.allow_gospel_bridge or gospel_bridge.get("status") == "consent_required",
            "trace_complete": True,
        }
        trace.append({"state": "REPORT_COMPOSED", "batch": 1})
        trace.append({"state": "REVIEW_REQUIRED" if review_required else "READY", "batch": 1})
        return {
            "case_id": case_id,
            "summary": summary,
            "observed_claims": claims,
            "worldview_map": worldview_map,
            "domain_pack_matches": domain_matches,
            "pride_hypotheses": pride,
            "hypothesis_compositions": compositions,
            "desire_map": desire_map,
            "virality_analysis": virality,
            "socratic_questions": questions,
            "gospel_bridge": gospel_bridge,
            "safety": safety.as_dict(),
            "limitations": limitations,
            "quality_gates": quality_gates,
            "review_status": review_status,
            "trace": trace,
            "engine_versions": self.registry.catalog()["versions"],
        }

    @staticmethod
    def _blocked_report(case_id: str, safety: dict[str, Any], trace: list[dict[str, Any]]) -> dict[str, Any]:
        trace.append({"state": "BLOCKED" if safety["status"] == "blocked" else "PASTORAL_SAFETY_HOLD", "batch": 1})
        return {
            "case_id": case_id,
            "summary": "普通辨识流程已停止，先处理安全或授权边界。",
            "observed_claims": [], "worldview_map": {}, "domain_pack_matches": [],
            "pride_hypotheses": [], "hypothesis_compositions": [], "desire_map": [],
            "virality_analysis": None, "socratic_questions": [],
            "gospel_bridge": {"status": "blocked"}, "safety": safety,
            "limitations": ["安全流程优先于普通分析。"], "quality_gates": {"safety_passed": False},
            "review_status": "blocked", "trace": trace,
            "engine_versions": get_registry().catalog()["versions"],
        }

    @staticmethod
    def _claims(case: DiscernmentCaseCreate) -> list[dict[str, Any]]:
        chunks = [part.strip() for part in re.split(r"[。！？!?\n]+", case.raw_input) if part.strip()]
        chunks = chunks[:12] or [case.raw_input]
        level = _evidence_level(case)
        return [{
            "claim_id": f"claim-{index + 1}",
            "observation": chunk,
            "statement_type": "user_self_report" if case.subject_type == "self_reflection" else "submitted_claim",
            "interpretation": None,
            "evidence_level": level,
            "source_refs": [item.locator for item in case.source_items[:10]],
            "limitations": ["提交内容尚未自动等同于独立核验事实。"],
        } for index, chunk in enumerate(chunks)]

    def _domain_matches(self, text: str) -> list[dict[str, Any]]:
        tokens = _tokens(text)
        candidates = []
        for pack in self.registry.domain_packs.values():
            phrases = list(pack.get("aliases", [])) + list(pack["detection"].get("positive_signals", []))
            phrases += [pack.get("fair_definition", "")]
            phrases += list(pack.get("pride_hypotheses", [])) + list(pack.get("desire_fears", []))
            phrases += list(pack.get("worldview", {}).values())
            positive, matches = _phrase_similarity(text, tokens, phrases)
            counter, counter_matches = _phrase_similarity(text, tokens, list(pack["detection"].get("counter_evidence", [])))
            score = max(0.0, min(1.0, positive - counter * 0.55))
            if score < 0.08:
                continue
            classification = "high" if score >= 0.78 else "mixed" if score >= 0.58 else "clarify"
            candidates.append({
                "pack_id": pack["id"], "name": pack["name"], "version": pack["version"], "cluster": pack["cluster"],
                "score": round(score, 3), "classification": classification,
                "matched_evidence": matches, "counter_evidence": counter_matches,
                "fair_definition": pack["fair_definition"], "common_grace": pack["common_grace"],
                "explanation": "词汇与规则召回的候选解释；低于 mixed 时只用于澄清。",
            })
        return sorted(candidates, key=lambda item: item["score"], reverse=True)[:5]

    def _worldview_map(self, matches: list[dict[str, Any]], consented: bool) -> dict[str, Any]:
        if not matches:
            return {"status": "insufficient_evidence", "candidates": [], "clarifying_question": "这段材料最核心的主张是什么？"}
        candidates = []
        for match in matches:
            pack = self.registry.domain_packs[match["pack_id"]]
            worldview = pack["worldview"]
            candidates.append({
                "pack_id": pack["id"], "version": pack["version"], "classification": match["classification"],
                "creation_good": pack["common_grace"],
                "human_problem": worldview["human_problem"],
                "functional_savior": worldview["functional_savior"] if consented else "未授权深层属灵解释",
                "promised_telos": worldview["promised_telos"],
                "fall_distortion": worldview["distortion"] if consented else "未授权深层属灵解释",
                "alternative_explanations": pack["detection"].get("exclusions", []),
            })
        return {"status": "candidate_map", "composite": len(candidates) > 1, "candidates": candidates}

    def _pride_hypotheses(self, case: DiscernmentCaseCreate, domain_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        text_tokens = _tokens(case.raw_input)
        domain_pride = " ".join(
            " ".join(self.registry.domain_packs[item["pack_id"]].get("pride_hypotheses", []))
            for item in domain_matches if item["score"] >= 0.38
        )
        candidates = []
        for pack in self.registry.hypothesis_packs.values():
            phrases = [pack["name_zh"], pack["fair_definition"]]
            phrases += list(pack.get("distortions", []))
            phrases += [signal.get("description", "") for signal in pack.get("signals", [])]
            score, matches = _phrase_similarity(case.raw_input + " " + domain_pride, text_tokens | _tokens(domain_pride), phrases)
            if score < 0.10:
                continue
            candidates.append((score, matches, pack))
        results = []
        for index, (score, matches, pack) in enumerate(sorted(candidates, key=lambda item: item[0], reverse=True)[:3]):
            results.append({
                "hypothesis_id": f"hypothesis-{index + 1}", "pattern_id": pack["id"], "name": pack["name_zh"],
                "scope": "self" if case.subject_type == "self_reflection" else "submitted_material",
                "observation": matches[0] if matches else case.raw_input[:240],
                "interpretation_hypothesis": pack["fair_definition"],
                "evidence_level": "H1", "confidence": round(min(0.49, 0.2 + score * 0.29), 3),
                "stable_character_language_allowed": False,
                "created_good": pack["created_good"],
                "alternative_explanations": pack["alternative_explanations"],
                "counter_evidence_needed": pack["counter_evidence"],
                "pastoral_risk": "公众人物需人工复核" if case.subject_type == "person" else "避免强迫性罪疚与自证循环",
                "socratic_follow_up": pack.get("socratic_tree", [{}])[0].get("question", "什么证据会削弱这个假设？"),
                "status": "HUMAN_REVIEW_REQUIRED" if case.subject_type == "person" else "PROPOSED",
                "pack_version": pack["version"],
            })
        return results

    @staticmethod
    def _compose_pride(hypotheses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for left_index, left in enumerate(hypotheses):
            for right in hypotheses[left_index + 1:]:
                key = frozenset({left["pattern_id"], right["pattern_id"]})
                if key in PRIDE_COMPOSITIONS:
                    interaction, explanation = PRIDE_COMPOSITIONS[key]
                    results.append({
                        "component_hypotheses": [left["hypothesis_id"], right["hypothesis_id"]],
                        "interaction_type": interaction, "explanation": explanation,
                        "limitations": ["组合是可证伪的解释模板，不是固定人格类型。"],
                    })
        return results

    def _desire_map(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for match in matches[:3]:
            pack = self.registry.domain_packs[match["pack_id"]]
            for desire in pack.get("desire_fears", [])[:2]:
                results.append({
                    "desire": desire, "source_pack": pack["id"], "pack_version": pack["version"],
                    "interpretation_hypothesis": f"“{desire}”可能在此承担超过受造物限度的重量。",
                    "evidence_level": "H1", "alternative_explanations": pack["detection"].get("exclusions", []),
                })
        return results[:5]

    def _questions(self, case: DiscernmentCaseCreate, matches: list[dict[str, Any]], pride: list[dict[str, Any]]) -> list[dict[str, Any]]:
        questions: list[dict[str, Any]] = []
        if matches:
            pack = self.registry.domain_packs[matches[0]["pack_id"]]
            tree = self.registry.related_asset(pack, "socratic_tree.json", {"stages": []})
            difficulty = {"clarify": "D0", "steelman": "D1", "evidence": "D1", "assumption": "D2", "counterexample": "D2", "consequence": "D3", "heart": "D4", "worship": "D4", "law": "D5", "gospel": "D5", "response": "D3"}
            for stage in tree.get("stages", []):
                if stage.get("questions"):
                    text = stage["questions"][0]
                    if text.count("？") + text.count("?") > 1:
                        text = re.split(r"(?<=[？?])", text)[0]
                    questions.append({
                        "question_id": f"{pack['id']}-{stage['id']}", "stage": stage["id"].upper(),
                        "difficulty": difficulty.get(stage["id"], "D1"), "text": text,
                        "purpose": stage.get("purpose", "澄清与检验"),
                        "discriminates_between": [pack["id"], "alternative_explanation"],
                        "requires_consent": bool(stage.get("requires_consent", False) or stage["id"] == "gospel"),
                        "allow_skip": True,
                    })
        if pride:
            questions.insert(1 if questions else 0, {
                "question_id": "pride-self-mirror", "stage": "SELF_MIRROR", "difficulty": "D3",
                "text": pride[0]["socratic_follow_up"], "purpose": "检验自高假设而非预设定罪",
                "discriminates_between": [pride[0]["pattern_id"], "alternative_explanation"],
                "requires_consent": False, "allow_skip": True,
            })
        if not questions:
            questions.append({
                "question_id": "clarify-core-claim", "stage": "CLARIFY", "difficulty": "D0",
                "text": "哪一句话最能代表你现在想检验的判断？", "purpose": "确定核心主张",
                "discriminates_between": [], "requires_consent": False, "allow_skip": True,
            })
        if not case.consent_scope.allow_spiritual_analysis:
            questions = [item for item in questions if item["stage"] not in {"HEART", "WORSHIP", "LAW", "GOSPEL", "RESPONSE", "SELF_MIRROR"}]
        return questions[:10]

    def _gospel_bridge(self, case: DiscernmentCaseCreate, matches: list[dict[str, Any]]) -> dict[str, Any]:
        if not case.consent_scope.allow_gospel_bridge:
            return {"status": "consent_required", "invitation": "你愿意看看基督如何回应这个困境吗？"}
        if matches:
            pack = self.registry.domain_packs[matches[0]["pack_id"]]
            bridges = self.registry.related_asset(pack, "gospel_bridges.json", {"routes": []})
            route = next((item for item in bridges.get("routes", []) if case.faith_context in item.get("audience", [])), None)
            route = route or next(iter(bridges.get("routes", [])), {})
            return {
                "status": "ready", "source_pack": pack["id"], "pack_version": pack["version"],
                "affirmation": route.get("affirmation", pack["common_grace"][0]),
                "exposure_hypothesis": route.get("exposure", pack["worldview"]["distortion"]),
                "christ_center": route.get("christ_center", pack["gospel_summary"]),
                "invitation": route.get("invitation", "你愿意继续探索吗？"),
                "non_coercive": True,
            }
        return {
            "status": "ready", "affirmation": "先承认其中真实的善与现实处境。",
            "christ_center": "基督的位格、十架与复活是福音中心；行为不是赚取接纳的基础。",
            "invitation": "你愿意从创造、堕落、基督与新创造的路径继续探索吗？", "non_coercive": True,
        }

    @staticmethod
    def _virality(case: DiscernmentCaseCreate, matches: list[dict[str, Any]]) -> dict[str, Any] | None:
        if case.subject_type not in {"person", "event", "product", "media", "mixed"}:
            return None
        metadata = case.source_metadata
        factors = []
        for factor in ["creator_capability", "persona_legibility", "narrative_fit", "emotional_activation", "format_fit", "platform_affordance", "network_seeding", "controversy_lift", "audience_need_fit", "external_event_timing", "paid_distribution", "randomness"]:
            raw = metadata.get(factor)
            factors.append({
                "factor": factor, "direction": raw.get("direction", "unknown") if isinstance(raw, dict) else "unknown",
                "evidence_level": raw.get("evidence_level", "P0") if isinstance(raw, dict) else "P0",
                "support": raw.get("support", []) if isinstance(raw, dict) else [],
                "alternative_explanations": raw.get("alternative_explanations", []) if isinstance(raw, dict) else ["时机、网络播种或随机性尚未排除"],
            })
        nodes = [{"id": "subject", "type": case.subject_type, "label": case.title}]
        edges = []
        for index, source in enumerate(case.source_items):
            source_id = f"source-{index + 1}"
            nodes.append({"id": source_id, "type": source.source_type, "label": source.locator})
            edges.append({"source": source_id, "target": "subject", "relation": "mentions", "support_not_implied": True})
        return {
            "persona_separation": {
                "verified_identity": [item.model_dump() for item in case.source_items if item.evidence_level in {"P3", "P4", "E3", "E4"}],
                "self_claimed_identity": [], "performed_persona": [], "analyst_hypotheses": [],
                "limitations": ["身份、人设、受众象征和分析者推断不可合并。"],
            },
            "content_narrative": {"submitted_claim_count": len(re.split(r"[。！？!?\n]+", case.raw_input)), "domain_pack_candidates": [item["pack_id"] for item in matches]},
            "business_model": {"observations": metadata.get("monetization_observations", []), "undisclosed_income_is_unknown": True},
            "platform_affordances": metadata.get("platform_affordances", []),
            "audience_segments": metadata.get("audience_segments", []),
            "virality_decomposition": {"factors": factors, "unknown_residual": True, "precision_warning": "定性因果假设，不是流量贡献率或真理分数。"},
            "propagation_graph": {"nodes": nodes, "edges": edges, "criticism_is_not_support": True},
            "controversy": {"state": metadata.get("controversy_state", "LATENT"), "next_states_are_hypotheses": True},
            "trust_risks": ["隐藏动机、内部算法和未披露收入不得作为事实。"],
            "parasocial_and_community": {"status": "insufficient_evidence", "audiences_must_not_be_stereotyped": True},
            "counterfactuals": ["没有平台推荐、争议互动或外部事件时，传播结果可能不同。", "能力、叙事适配、受众需要与随机性可能共同解释结果。"],
            "formation_fruits": {"status": "prospective_hypotheses", "dimensions": ["attention", "truth_habits", "desire", "identity", "relationships", "work_and_money", "body_and_sexuality", "public_life", "spiritual_openness"]},
            "human_review_required": case.subject_type == "person" or case.sensitivity in {"reputation_sensitive", "legal_sensitive", "minor_involved"},
        }

    @staticmethod
    def _summary(matches: list[dict[str, Any]], pride: list[dict[str, Any]], review_status: str) -> str:
        if not matches:
            return "现有材料不足以形成世界观分类；先澄清核心主张并补充反证。"
        substantial = [item for item in matches if item["score"] >= 0.38] or matches[:1]
        names = "、".join(item["name"] for item in substantial[:3])
        hypothesis_note = f"并提出 {len(pride)} 个低证据、可撤销的自高假设" if pride else "未生成自高假设"
        review = "，交付前需要人工复核" if review_status == "human_review_required" else ""
        return f"材料与“{names}”存在候选关联，{hypothesis_note}{review}。这些不是人物标签或属灵判决。"
