"""Hand-authored golden fixtures for the first-wave rollout batches (03/04/09).

These carry real domain content, not just the right shape, so a provider swap
that changes *meaning* rather than structure still shows up as a diff.

Two scenarios run through them:

* batches 03/04 - the 成功主义网红 case, matching the Batch 01 fixture corpus
* batch 09     - a 罗马书 8:1 exegetical query
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.discernment_platform.model_adapter import ScriptedAdapter  # noqa: E402
from backend.discernment_platform.skill_runtime import SkillRuntime, output_envelope  # noqa: E402
from backend.discernment_platform.skills import get_skill_registry  # noqa: E402

GOLDEN_ROOT = Path(__file__).resolve().parents[1] / "backend/discernment_platform/data/golden"

INFLUENCER_MATERIAL = (
    "某网红反复宣称：穷是因为不够努力，只要复制他的课程和生活方式，"
    "任何人都能实现财富自由；失败者只是没有执行力。"
)

SCRUPULOSITY_MATERIAL = (
    "我每天反复检查自己是不是骄傲，任何一点自信都让我觉得可能得罪神。"
    "我常常认罪几个小时，还是担心神不会赦免我。"
)

THEOLOGY_QUESTION = "罗马书 8:1「如今那些在基督耶稣里的就不定罪了」中的「定罪」指什么？"


def viral_input(case: str = INFLUENCER_MATERIAL, **extra) -> dict:
    payload = {
        "case_id": "golden-viral-001",
        "subject_type": "person",
        "material": case,
        "platform_scope": ["短视频", "付费社群"],
        "time_window": "2026-01 至 2026-06",
        "consent_scope": {"allow_spiritual_analysis": True, "allow_gospel_bridge": True},
        "sensitivity": "normal",
    }
    payload.update(extra)
    return payload


def theology_input() -> dict:
    return {
        "case_id": "golden-theology-001",
        "query": THEOLOGY_QUESTION,
        "scripture_refs": ["罗马书 8:1"],
        "allowed_rights": ["public_domain"],
        "tradition_scope": ["reformed", "lutheran", "roman_catholic"],
        "sensitivity": "normal",
    }


# --- batch 03 ---------------------------------------------------------------

BATCH03: dict[str, tuple[dict, dict]] = {
    "identity-persona-separator": (
        viral_input(),
        {
            "personaprofile": {
                "verifiable_identity": {
                    "claims": ["公开工商登记显示其经营一家课程公司"],
                    "evidence_level": "E3",
                    "source_type": "public_registry",
                },
                "self_claimed_identity": {
                    "claims": ["白手起家", "已实现财富自由"],
                    "evidence_level": "E1",
                    "note": "均为自我宣称，未见独立佐证",
                },
                "performed_persona": {
                    "role": "严父式导师",
                    "signature_moves": ["先训斥再给方法", "以自身作息作为标准"],
                    "evidence_level": "E3",
                },
                "audience_symbol": "被塑造为「唯一敢说真话的人」",
                "commercial_brand": "课程 + 私域社群，人设与商品高度绑定",
                "divergence_points": [
                    {
                        "point": "自称白手起家，但公开材料显示早期有家庭资金支持",
                        "evidence_level": "E2",
                        "alternative_explanations": [
                            "「白手起家」可能是其对自身经历的宽泛表述",
                            "早期资金规模可能确实很小",
                        ],
                    }
                ],
                "stability": {
                    "assessment": "人设在两年内高度一致",
                    "evidence_level": "E3",
                    "note": "一致性说明人设稳定，不等于人格与人设一致",
                },
                "unknowns": [
                    "镜头外的实际生活方式",
                    "其对学员失败案例的私下态度",
                ],
                "limitations": [
                    "仅基于公开材料，不对当事人内心作判断",
                    "人设分析不是人格评价，更不是得救状态判断",
                ],
            }
        },
    ),
    "narrative-rhetoric-analyzer": (
        viral_input(),
        {
            "output_1": {
                "theme_matrix": {
                    "hero": "自律且执行力强的个体",
                    "enemy": "找借口的人、体制的抱怨者",
                    "crisis": "再不改变就会被时代淘汰",
                    "savior": "他的方法论与课程",
                    "identity_promise": "照做就能成为「配得上好生活的人」",
                },
                "narrative_templates": [
                    "困境—顿悟—方法—翻身",
                    "对照组：照做的人 vs 不照做的人",
                ],
                "rhetorical_strategies": [
                    {
                        "strategy": "二元对立",
                        "example_span": "失败者只是没有执行力",
                        "effect": "把复杂成因压缩为单一意志变量",
                    },
                    {
                        "strategy": "全称断言",
                        "example_span": "任何人都能实现财富自由",
                        "effect": "抬高承诺强度，同时不可证伪",
                    },
                ],
                "emotion_spectrum": ["紧迫", "羞耻", "被激励", "对失败者的轻蔑"],
                "authenticity_habits": {
                    "cites_sources": False,
                    "shows_counterexamples": False,
                    "discloses_conflicts": "部分披露",
                    "evidence_level": "E3",
                },
                "evidence_spans": [
                    "穷是因为不够努力",
                    "只要复制他的课程和生活方式",
                    "失败者只是没有执行力",
                ],
                "limitations": [
                    "修辞强度不等于恶意；本分析不推断当事人动机",
                ],
            }
        },
    ),
    "business-model-monetization-analyzer": (
        viral_input(),
        {
            "output_1": {
                "business_model": "低价引流课 → 高价社群 → 一对一咨询",
                "revenue_channels": [
                    {"channel": "199 元入门课", "role": "获客", "evidence_level": "E3"},
                    {"channel": "9800 元年度社群", "role": "主要利润来源", "evidence_level": "E2"},
                ],
                "conversion_path": "免费短视频 → 私域加微信 → 直播逼单 → 社群续费",
                "stakeholders": ["主理人", "分销讲师", "平台", "学员"],
                "incentive_conflicts": [
                    {
                        "conflict": "分销佣金与学员适配性之间存在张力",
                        "evidence_level": "E2",
                        "alternative_explanations": ["分销比例可能低到不足以扭曲推荐"],
                    }
                ],
                "disclosure": "课程页面标注了「收益因人而异」，但直播话术未同步强调",
                "honesty": "宣称的学员成功率未提供可核验来源",
                "fit": "对已有稳定现金流者适配，对负债人群适配性存疑",
                "vulnerability": "存在针对经济焦虑人群的定向投放，需重点关注",
                "evidence_level": "E2",
                "limitations": [
                    "商业化本身不等于罪；本分析只评估披露、诚实、适配与脆弱性利用风险",
                    "未接入外部数据，价格与转化路径均来自公开页面",
                ],
            }
        },
    ),
    "manipulation-trust-risk-detector": (
        viral_input(),
        {
            "output_1": {
                "risk_signals": [
                    {
                        "id": "risk-01",
                        "type": "虚假稀缺",
                        "observation": "「仅剩 3 个名额」在连续四场直播中重复出现",
                        "evidence_level": "E3",
                        "severity": "moderate",
                        "reasonable_explanations": [
                            "可能确实每场都新开少量名额",
                            "可能是平台模板话术",
                        ],
                    },
                    {
                        "id": "risk-02",
                        "type": "脆弱性利用",
                        "observation": "投放素材集中在「负债」「被裁员」关键词人群",
                        "evidence_level": "E2",
                        "severity": "high",
                        "reasonable_explanations": ["可能只是平台算法自动优化的结果"],
                    },
                ],
                "protective_recommendations": [
                    "向学员明确展示失败案例与退款条款",
                    "对负债人群设置冷静期",
                ],
                "human_review_required": True,
                "evidence_level": "E2",
                "limitations": [
                    "风险信号不等于欺诈认定，也不构成法律结论",
                    "仅基于公开材料，未对当事人作动机判断",
                ],
            }
        },
    ),
}


# --- batch 04 ---------------------------------------------------------------

def pride_shape(
    observations: list[dict],
    alternatives: list[str],
    counter: list[str],
    limitations: list[str],
    next_action: str,
    evidence_level: str = "E2",
) -> dict:
    return {
        "observations_or_hypotheses": observations,
        "evidence_level": evidence_level,
        "alternative_explanations": alternatives,
        "counter_evidence": counter,
        "limitations": limitations,
        "next_action": next_action,
    }


BATCH04: dict[str, tuple[dict, dict]] = {
    "hypothesis-composer": (
        viral_input(),
        pride_shape(
            observations=[
                {
                    "id": "h-01",
                    "observation": "同时出现「以成就称义」与「轻看软弱者」两组信号",
                    "interpretation_hypothesis": "值得察验的是，两者可能是 reinforcing 关系：越以业绩自证，越需要贬低失败者来维持叙事",
                    "relationship_type": "reinforcing",
                    "evidence_level": "E2",
                    "alternative_explanations": [
                        "两者可能各自独立，只是同一营销风格的产物",
                        "轻看软弱可能是激励话术的粗糙表达",
                    ],
                },
                {
                    "id": "h-02",
                    "observation": "公开场合强调谦卑，同时反复展示身价",
                    "interpretation_hypothesis": "可能是 masking 关系：谦卑表达掩盖以地位自证的需要",
                    "relationship_type": "masking",
                    "evidence_level": "E1",
                    "alternative_explanations": ["谦卑表达可能是真实的，只是与商业表达并存"],
                },
            ],
            alternatives=[
                "整体可能只是行业通用的营销人格，不反映其私下自我认知",
            ],
            counter=[
                "在失败或被公开质疑时的实际反应",
                "对不付费者是否同样尊重",
            ],
            limitations=[
                "E1-E2 证据不得作为结论输出",
                "系统不读心，所有关系判断均为可推翻的假设",
            ],
            next_action="先向用户提出一个自省问题，而不是给出对他人的定性",
        ),
    ),
    "self-justification-engine": (
        viral_input(),
        pride_shape(
            observations=[
                {
                    "id": "sj-01",
                    "path": "以能力称义",
                    "observation": "反复以「执行力」区分值得与不值得的人",
                    "interpretation_hypothesis": "值得察验的是，可能存在以能力证明自身价值的路径",
                    "evidence_level": "E3",
                    "alternative_explanations": [
                        "可能是对勤奋这一受造之善的正当肯定",
                        "可能是面向特定学员群体的针对性表达",
                    ],
                }
            ],
            alternatives=["也可能是行业话术，而非其自我认知的真实结构"],
            counter=["失去收入或影响力时，他如何描述自己"],
            limitations=[
                "称义路径是牧养性假设，不是对灵魂状态的判决",
                "结构性因素（行业竞争、平台激励）同样在起作用，不应全部个人化",
            ],
            next_action="邀请用户先察验自己身上是否有同一条路径",
            evidence_level="E3",
        ),
    ),
    "scrupulosity-and-trauma-guardian": (
        viral_input(
            case=SCRUPULOSITY_MATERIAL,
            case_id="golden-scrupulosity-001",
            subject_type="self_reflection",
            sensitivity="mental_health",
        ),
        pride_shape(
            observations=[
                {
                    "id": "sg-01",
                    "observation": "每日反复自我检查、长时间认罪、仍不得确据",
                    "risk_type": "religious_scrupulosity",
                    "evidence_level": "E3",
                    "alternative_explanations": [
                        "可能处于一段特别敏感的时期，未必是长期模式",
                    ],
                }
            ],
            alternatives=["也可能与身心状态相关，而非单纯属灵问题"],
            counter=["在无压力时期是否同样反复自查"],
            limitations=[
                "本系统不作临床诊断",
                "不得继续加深自我控告；律法压力必须降低",
            ],
            next_action=(
                "停止深挖罪的流程，转为确据与安慰：基督已一次成全；"
                "同时建议联系合格的心理或医疗专业人员，并找一位稳妥的牧者同行，"
                "不以本系统取代专业照护。"
            ),
            evidence_level="E3",
        ),
    ),
    "integrated-pride-report-composer": (
        viral_input(),
        pride_shape(
            observations=[
                {
                    "id": "rep-01",
                    "affirmation": "对主动性与责任的看重是真实的受造之善",
                    "observation": "材料同时呈现勤奋伦理与对失败者的轻看",
                    "interpretation_hypothesis": "值得察验的是，可能存在以成就承担终极价值的模式",
                    "evidence_level": "E2",
                    "alternative_explanations": [
                        "可能是营销叙事，不代表其真实自我认知",
                        "可能是对特定懈怠现象的过度反应",
                    ],
                }
            ],
            alternatives=["整体也可能只反映行业话术，而非个人属灵状况"],
            counter=["跨场景、跨时间是否出现同一模式"],
            limitations=[
                "报告区分观察、解释与假设；解释与假设均可被推翻",
                "系统不能读心，不判定任何人的得救状态",
                "E2 证据不足以支撑结论",
            ],
            next_action="向用户提出一个自省首问，并给出一个具体、非表演性的回应建议",
        ),
    ),
}


# --- batch 09 ---------------------------------------------------------------

def theology_shape(
    evidence: list[dict],
    context_analysis: dict,
    claims: list[dict],
    contradictions: list[dict],
    limitations: list[str],
) -> dict:
    return {
        "retrieved_and_filtered_evidence": evidence,
        "source_and_edition_metadata": {
            "sources": [
                {
                    "source_id": "src-cuv",
                    "title": "圣经和合本",
                    "edition": "1919",
                    "rights_status": "public_domain",
                    "language": "zh",
                },
                {
                    "source_id": "src-na28",
                    "title": "Nestle-Aland 希腊文新约",
                    "edition": "NA28",
                    "rights_status": "quotation_only",
                    "language": "grc",
                },
            ]
        },
        "context_and_original_language_analysis": context_analysis,
        "doctrinal_tier_and_tradition_scope": {
            "tier": "D1",
            "tradition_label": "此层为普世共识，非特定宗派立场",
            "tradition_scope": ["reformed", "lutheran", "roman_catholic"],
            "consensus_level": "ecumenical",
        },
        "citations": [
            {
                "citation_id": "cite-01",
                "source_id": "src-cuv",
                "locator": "罗马书 8:1",
                "quote_text": "如今，那些在基督耶稣里的就不定罪了。",
                "rights_status": "public_domain",
                "used_as_proof": True,
                "literary_context": "第 8 章承接第 7 章律法下的挣扎，转入圣灵中的生命",
                "canonical_context": "置于保罗因信称义论证的整体脉络中",
                "historical_context": "写给罗马教会中犹太与外邦信徒并存的群体",
            }
        ],
        "contradictions_and_qualifications": contradictions,
        "generated_claims": claims,
        "evidence_graph_trace": {
            "nodes": ["src-cuv", "cite-01", "claim-01"],
            "edges": [["cite-01", "claim-01", "supports"]],
            "policy_version": "0.9.0",
        },
        "limitations_and_review_status": {
            "limitations": limitations,
            "review_status": "human_review_required",
            "reviewer_role": "qualified_theological_reviewer",
        },
    }


BATCH09: dict[str, tuple[dict, dict]] = {
    "scripture-context-resolver": (
        theology_input(),
        theology_shape(
            evidence=[
                {
                    "id": "ev-01",
                    "passage": "罗马书 8:1-4",
                    "book": "罗马书",
                    "genre": "书信体论证",
                    "speaker": "保罗",
                    "audience": "罗马教会",
                    "structural_position": "5-8 章论证段的转折点",
                    "evidence_level": "E4",
                }
            ],
            context_analysis={
                "immediate_context": "紧接 7:24-25 的呼喊，8:1 给出结论性宣告",
                "book_context": "全书论证因信称义与在基督里的新生命",
                "genre_note": "论证性书信，不宜按箴言式格言单独抽取",
            },
            claims=[
                {
                    "claim_id": "claim-01",
                    "statement": "此处「定罪」指法庭意义上的定罪判决，而非主观的自责感受",
                    "tier": "D1",
                    "tradition_label": "普世共识",
                    "support_citations": ["cite-01"],
                    "evidence_level": "E4",
                }
            ],
            contradictions=[
                {
                    "issue": "部分通俗解经把「不定罪」等同于「不再有罪咎感」",
                    "qualification": "经文语域是法庭性的地位宣告，感受层面的变化是果效而非定义",
                }
            ],
            limitations=[
                "本结果基于所列版本，未穷尽异文与译本差异",
                "教义结论需合资格神学复核后方可对外发布",
            ],
        ),
    ),
    "greek-morphology-syntax-analyzer": (
        theology_input(),
        theology_shape(
            evidence=[
                {
                    "id": "ev-01",
                    "lemma": "κατάκριμα",
                    "gloss": "定罪、刑罚性判决",
                    "case": "nominative",
                    "number": "singular",
                    "gender": "neuter",
                    "clause_role": "主句主语补足",
                    "textual_variants": "NA28 与 TR 在 8:1 结尾小句存在差异",
                    "corpus_usage": ["罗 5:16", "罗 5:18"],
                    "evidence_level": "E4",
                }
            ],
            context_analysis={
                "syntax": "οὐδὲν ... κατάκριμα 构成强调性否定，前置 νῦν 标记时间转折",
                "discourse": "νῦν 把论证从 7 章的挣扎推进到 8 章的宣告",
                "morphology_note": "κατάκριμα 为结果性名词，指判决本身而非定罪的过程",
            },
            claims=[
                {
                    "claim_id": "claim-01",
                    "statement": "κατάκριμα 在保罗用法中一致指向判决结果，支持法庭性读法",
                    "tier": "D1",
                    "tradition_label": "普世共识",
                    "support_citations": ["cite-01"],
                    "evidence_level": "E4",
                    "corpus_usage": ["罗 5:16", "罗 5:18"],
                }
            ],
            contradictions=[
                {
                    "issue": "TR 在 8:1 结尾增补「不随从肉体，只随从圣灵」",
                    "qualification": "该增补见于较晚抄本，不影响 κατάκριμα 的语义判断",
                }
            ],
            limitations=[
                "词义结论同时依据语料用法，不单靠词典编号",
                "异文评估未穷尽全部抄本证据",
            ],
        ),
    ),
    "systematic-doctrine-claim-builder": (
        theology_input(),
        theology_shape(
            evidence=[
                {
                    "id": "ev-01",
                    "passages": ["罗马书 8:1", "罗马书 5:1", "加拉太书 2:16"],
                    "theme": "称义的地位性与不可动摇性",
                    "evidence_level": "E4",
                }
            ],
            context_analysis={
                "canonical_shape": "从罗 3-5 的称义论证推进到罗 8 的确据",
                "note": "命题必须由多处经文与正典结构共同支撑，不得单点取证",
            },
            claims=[
                {
                    "claim_id": "claim-01",
                    "statement": "在基督里的人不再面对定罪判决，这是地位性的，不随表现增减",
                    "tier": "D1",
                    "tradition_label": "普世共识，非特定宗派立场",
                    "support_citations": ["cite-01"],
                    "counter_arguments": [
                        "有观点认为此宣告以持续顺服为条件；但 8:1 的语法未设条件从句",
                    ],
                    "evidence_level": "E4",
                },
                {
                    "claim_id": "claim-02",
                    "statement": "称义与成圣须区分：前者一次成就，后者渐进",
                    "tier": "D2",
                    "tradition_label": "改革宗与信义宗表述，罗马天主教用语不同",
                    "support_citations": ["cite-01"],
                    "evidence_level": "E3",
                },
            ],
            contradictions=[
                {
                    "issue": "D2 命题在不同传统中术语不一致",
                    "qualification": "已标注传统归属，不作跨传统的普遍陈述",
                }
            ],
            limitations=[
                "D2 层命题呈现各方立场，不作裁定",
                "教义命题需人工神学复核",
            ],
        ),
    ),
    "theology-answer-composer-and-red-team": (
        theology_input(),
        theology_shape(
            evidence=[
                {
                    "id": "ev-01",
                    "passage": "罗马书 8:1",
                    "role": "primary",
                    "evidence_level": "E4",
                }
            ],
            context_analysis={
                "answer_outline": [
                    "先界定「定罪」的法庭语义",
                    "再说明其地位性含义",
                    "最后区分与罪咎感的关系",
                ],
                "misuse_warning": "此节不可被用于要求他人无条件顺服，或压制合理的良心不安",
            },
            claims=[
                {
                    "claim_id": "claim-01",
                    "statement": "「定罪」指法庭性的判决；在基督里的人不再面对这一判决",
                    "tier": "D1",
                    "tradition_label": "普世共识",
                    "support_citations": ["cite-01"],
                    "evidence_level": "E4",
                }
            ],
            contradictions=[
                {
                    "issue": "红队检查：本节是否可能被用于淡化悔改？",
                    "qualification": "答案已同时说明罪的真实与悔改的必要，未落入廉价恩典",
                },
                {
                    "issue": "红队检查：本节是否可能被用于属灵施压？",
                    "qualification": "已加入误用警告，禁止以此要求无条件顺服",
                },
            ],
            limitations=[
                "答案区分共识层与传统差异层",
                "对外发布前需合资格神学复核",
            ],
        ),
    ),
}


CURATED = {**BATCH03, **BATCH04, **BATCH09}


def main() -> int:
    registry = get_skill_registry()
    failures = []
    for skill_id, (payload, golden) in CURATED.items():
        contract = registry.get(skill_id)
        expected = set(output_envelope(contract))
        if set(golden) != expected:
            failures.append((skill_id, f"key mismatch: {sorted(set(golden) ^ expected)}"))
            continue
        runtime = SkillRuntime(adapter=ScriptedAdapter({skill_id: golden}))
        result = runtime.invoke(skill_id, payload)
        if result.status != "ok":
            failures.append((skill_id, f"{result.status}: {result.message[:200]}"))
            continue
        target = GOLDEN_ROOT / contract.batch_key
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{skill_id}.json").write_text(
            json.dumps(
                {
                    "skill_id": skill_id,
                    "skill_name": contract.name,
                    "skill_version": contract.version,
                    "batch": contract.batch,
                    "tier": "curated",
                    "notes": "人工撰写的黄金样例：同时锁定输出形状与内容质量。",
                    "input": payload,
                    "expected_output_keys": sorted(golden),
                    "golden_output": golden,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    print(f"curated written: {len(CURATED) - len(failures)} / {len(CURATED)}")
    for skill_id, reason in failures:
        print(f"  FAILED {skill_id}: {reason}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
