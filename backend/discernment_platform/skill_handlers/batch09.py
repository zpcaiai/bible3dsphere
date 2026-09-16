"""Batch 09 - 圣经神学释经与证据知识库：bindings to theology_knowledge."""

from __future__ import annotations

import re

from ..skill_runtime import SkillInvocationError, handler
from ._engines import pack, registry
from ._support import Payload, dumped, require

_REFERENCE_RE = re.compile(
    r"([1-3]?\s?[一-鿿A-Za-z]+)\s*(\d+)\s*[:：]\s*(\d+)(?:\s*[-–]\s*(\d+))?"
)


def _sources(payload: Payload) -> list:
    from ..theology_knowledge.models import SourceDocument

    return [
        s if isinstance(s, SourceDocument) else SourceDocument(**s)
        for s in payload.get("sources", []) or []
    ]


@handler("bible-reference-parser")
def bible_reference_parser(contract, payload: Payload, context: Payload) -> Payload:
    (text,) = require(payload, "text")
    references = [
        {
            "book": m.group(1).strip(),
            "chapter": int(m.group(2)),
            "verse_start": int(m.group(3)),
            "verse_end": int(m.group(4) or m.group(3)),
            "raw": m.group(0),
        }
        for m in _REFERENCE_RE.finditer(str(text))
    ]
    if not references:
        raise SkillInvocationError("INSUFFICIENT_EVIDENCE", "no bible reference found")
    return {"references": references, "reference_count": len(references)}


@handler("theology-query-normalizer")
def theology_query_normalizer(contract, payload: Payload, context: Payload) -> Payload:
    (query,) = require(payload, "query")
    normalized = re.sub(r"\s+", " ", str(query)).strip()
    return {
        "normalized_query": normalized,
        "length": len(normalized),
        "doctrine_scope": payload.get("doctrine_scope", "unspecified"),
    }


@handler("citation-provenance-verifier")
def citation_provenance_verifier(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import verify_citation
    from ..theology_knowledge.models import CitationRecord, SourceDocument

    citation_raw, source_raw = require(payload, "citation", "source")
    citation = (
        citation_raw if isinstance(citation_raw, CitationRecord) else CitationRecord(**citation_raw)
    )
    source = (
        source_raw if isinstance(source_raw, SourceDocument) else SourceDocument(**source_raw)
    )
    return {"citation_verification": dumped(verify_citation(citation, source))}


@handler("rights-and-license-policy-enforcer")
def rights_policy_enforcer(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import RightsPolicy
    from ..theology_knowledge.models import RightsStatus

    (status_raw,) = require(payload, "rights_status")
    try:
        status = RightsStatus(status_raw)
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    policy = RightsPolicy()
    consent = bool(payload.get("user_consent", False))
    return {
        "rights_status": status.value,
        "can_embed": policy.can_embed(status, consent),
        "can_generate_from": policy.can_generate_from(status),
        "can_quote": policy.can_quote(status),
    }


@handler("scripture-misuse-detector")
def scripture_misuse_detector(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import detect_misuse

    (text,) = require(payload, "text")
    return {"misuse": dumped(detect_misuse(str(text)))}


@handler("theology-evidence-graph-builder")
def theology_evidence_graph_builder(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import build_evidence_graph

    (query_id,) = require(payload, "query_id")
    graph = build_evidence_graph(
        query_id=str(query_id),
        sources=list(payload.get("sources", [])),
        passages=list(payload.get("passages", [])),
        claims=list(payload.get("claims", [])),
        generated_statements=list(payload.get("generated_statements", [])),
    )
    return {"evidence_graph": dumped(graph)}


@handler("doctrine-tier-consensus-governor")
def doctrine_tier_governor(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import DoctrineGovernor

    from ..theology_knowledge.models import DoctrineTier

    (tier_raw,) = require(payload, "tier")
    try:
        tier = DoctrineTier(tier_raw)
    except ValueError as exc:
        raise SkillInvocationError("MODEL_OUTPUT_INVALID", str(exc)) from exc
    result = DoctrineGovernor().evaluate(
        tier=tier,
        tradition_scope=list(payload.get("tradition_scope", [])),
        consensus_level=str(payload.get("consensus_level", "contested")),
        used_as_salvation_test=bool(payload.get("used_as_salvation_test", False)),
    )
    return {"doctrine_decision": dumped(result), "tier": tier.value}


@handler("auditable-rag-retriever-reranker")
def auditable_rag_retriever(contract, payload: Payload, context: Payload) -> Payload:
    from ..theology_knowledge import TheologyKnowledgeOrchestrator

    from ..theology_knowledge.models import RagQuery

    sources = _sources(payload)
    if not sources:
        raise SkillInvocationError("INSUFFICIENT_EVIDENCE", "no sources supplied")
    raw_query = payload.get("query")
    if raw_query is None:
        raise SkillInvocationError("MISSING_REQUIRED_INPUT", "query is required")
    query = raw_query if isinstance(raw_query, RagQuery) else RagQuery(**raw_query)
    filtered = TheologyKnowledgeOrchestrator().filter_sources(query, sources)
    return {"retrieved": dumped(filtered), "auditable": True, "query_id": query.query_id}


@handler("historical-theology-retriever")
def historical_theology_retriever(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("knowledge", "historical_theology")
    return {"knowledge_pack": data, "scope": data["scope"], "risks": data["risks"]}


@handler("denominational-position-matrix-builder")
def denominational_matrix(contract, payload: Payload, context: Payload) -> Payload:
    data = pack("knowledge", "denominational_traditions")
    reg = registry()
    return {
        "knowledge_pack": data,
        "doctrine_tiers": {p["id"]: p["tier"] for p in reg.ordered_doctrine_packs()},
        "adjudication_policy": "present positions, do not adjudicate tier2/tier3",
    }
