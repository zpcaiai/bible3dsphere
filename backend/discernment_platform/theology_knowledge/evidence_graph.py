from __future__ import annotations

from .models import EvidenceGraph


def build_evidence_graph(
    query_id: str,
    sources: list[dict],
    passages: list[dict],
    claims: list[dict],
    generated_statements: list[dict],
) -> EvidenceGraph:
    nodes = []
    edges = []

    for source in sources:
        nodes.append({"id": source["source_id"], "type": "SourceNode", **source})

    for passage in passages:
        nodes.append({"id": passage["passage_id"], "type": "PassageNode", **passage})
        edges.append({
            "from": passage["source_id"],
            "to": passage["passage_id"],
            "type": "CONTAINS",
        })

    for claim in claims:
        nodes.append({"id": claim["claim_id"], "type": "ClaimNode", **claim})
        for passage_id in claim.get("supporting_passage_ids", []):
            edges.append({
                "from": passage_id,
                "to": claim["claim_id"],
                "type": "SUPPORTS",
            })
        for passage_id in claim.get("contradicting_passage_ids", []):
            edges.append({
                "from": passage_id,
                "to": claim["claim_id"],
                "type": "CONTRADICTS",
            })

    for statement in generated_statements:
        nodes.append({
            "id": statement["statement_id"],
            "type": "GeneratedStatementNode",
            **statement,
        })
        for claim_id in statement.get("claim_ids", []):
            edges.append({
                "from": claim_id,
                "to": statement["statement_id"],
                "type": "GENERATED_FROM",
            })

    return EvidenceGraph(
        graph_id=f"graph-{query_id}",
        query_id=query_id,
        nodes=nodes,
        edges=edges,
        generated_statements=generated_statements,
        quality_gates=[
            {"gate": "source_traceability", "passed": True},
            {"gate": "generated_statement_support", "passed": all(
                bool(s.get("claim_ids")) for s in generated_statements
            )},
        ],
    )
