"""Optional metadata-only temporal evidence graph projection."""
from __future__ import annotations

from typing import Any

from .formation_graph import graph_enabled


def _driver():
    try:
        from mvfe.db.neo4j import get_neo4j_driver
        return get_neo4j_driver()
    except Exception:
        return None


def sync_temporal_pattern(
    *, tenant_id: str, profile_id: str, pattern: dict[str, Any], evidence: list[dict[str, Any]],
    life_season_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Project identifiers/status/provenance only; never sensitive content."""
    if not graph_enabled():
        return {"status": "DISABLED", "nodes": 0, "relationships": 0}
    driver = _driver()
    if driver is None:
        return {"status": "UNAVAILABLE", "nodes": 0, "relationships": 0}
    eligible = [item for item in evidence if item.get("evidence_role") not in {"INVALIDATED", "SUPERSEDED"}]
    try:
        with driver.session() as session:
            session.run(
                "MERGE (p:FormationTwinOwned:FormationPattern "
                "{tenant_id:$tenant_id,profile_id:$profile_id,pattern_id:$pattern_id}) "
                "SET p.pattern_type=$pattern_type,p.lifecycle_status=$lifecycle_status,"
                "p.user_review_status=$user_review_status,p.version=$version,"
                "p.valid_from=$valid_from,p.valid_until=$valid_until",
                tenant_id=tenant_id, profile_id=profile_id, pattern_id=str(pattern["id"]),
                pattern_type=pattern["pattern_type"], lifecycle_status=pattern["lifecycle_status"],
                user_review_status=pattern["user_review_status"], version=int(pattern.get("version", 1)),
                valid_from=str(pattern.get("first_observed_at") or ""), valid_until=str(pattern.get("review_due_at") or ""),
            )
            for item in eligible:
                relation = "COUNTERED_BY" if item["evidence_role"] in {"COUNTEREVIDENCE", "CONTEXT_LIMIT"} else "SUPPORTED_BY"
                session.run(
                    "MATCH (p:FormationPattern {tenant_id:$tenant_id,profile_id:$profile_id,pattern_id:$pattern_id}) "
                    "MERGE (e:FormationTwinOwned:PatternEvidence "
                    "{tenant_id:$tenant_id,profile_id:$profile_id,evidence_id:$evidence_id}) "
                    "SET e.evidence_role=$evidence_role,e.source_record_type=$source_record_type,"
                    "e.source_record_id=$source_record_id,e.observed_at=$observed_at,e.status=$status "
                    f"MERGE (e)-[r:{relation} {{tenant_id:$tenant_id,profile_id:$profile_id}}]->(p) "
                    "SET r.role=$evidence_role,r.observed_at=$observed_at,r.valid_from=$observed_at,"
                    "r.valid_until='',r.status=$status",
                    tenant_id=tenant_id, profile_id=profile_id, pattern_id=str(pattern["id"]),
                    evidence_id=str(item["id"]), evidence_role=item["evidence_role"],
                    source_record_type=item["source_record_type"], source_record_id=str(item["source_record_id"]),
                    observed_at=str(item.get("occurred_at") or ""), status=item.get("user_review_status", "PENDING"),
                )
            for season_id in life_season_ids or []:
                session.run(
                    "MATCH (p:FormationPattern {tenant_id:$tenant_id,profile_id:$profile_id,pattern_id:$pattern_id}) "
                    "MERGE (s:FormationTwinOwned:LifeSeason "
                    "{tenant_id:$tenant_id,profile_id:$profile_id,life_season_id:$season_id}) "
                    "MERGE (p)-[r:ACTIVE_DURING {tenant_id:$tenant_id,profile_id:$profile_id}]->(s) "
                    "SET r.status=$status,r.valid_from='',r.valid_until=''",
                    tenant_id=tenant_id, profile_id=profile_id, pattern_id=str(pattern["id"]),
                    season_id=str(season_id), status=pattern["lifecycle_status"],
                )
        return {"status": "SYNCED", "nodes": 1 + len(eligible) + len(life_season_ids or []),
                "relationships": len(eligible) + len(life_season_ids or [])}
    finally:
        driver.close()


def invalidate_temporal_evidence(*, tenant_id: str, profile_id: str, evidence_id: str) -> dict[str, Any]:
    driver = _driver()
    if driver is None:
        return {"status": "UNAVAILABLE", "updated": 0}
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (e:PatternEvidence {tenant_id:$tenant_id,profile_id:$profile_id,evidence_id:$evidence_id}) "
                "SET e.status='INVALIDATED' WITH e MATCH (e)-[r]->(:FormationPattern) "
                "SET r.status='INVALIDATED' RETURN count(e) AS updated",
                tenant_id=tenant_id, profile_id=profile_id, evidence_id=evidence_id,
            ).single()
        return {"status": "UPDATED", "updated": int(result["updated"] if result else 0)}
    finally:
        driver.close()


def graph_consistency_status(*, postgres_pattern_ids: set[str], graph_pattern_ids: set[str]) -> dict[str, Any]:
    missing = sorted(postgres_pattern_ids - graph_pattern_ids)
    orphaned = sorted(graph_pattern_ids - postgres_pattern_ids)
    return {"consistent": not missing and not orphaned, "missing_in_graph": missing, "orphaned_in_graph": orphaned}


def erase_temporal_graph(*, tenant_id: str, profile_id: str) -> dict[str, Any]:
    driver = _driver()
    if driver is None:
        return {"status": "UNAVAILABLE", "deleted": 0}
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n:FormationTwinOwned {tenant_id:$tenant_id,profile_id:$profile_id}) "
                "RETURN count(n) AS deleted",
                tenant_id=tenant_id, profile_id=profile_id,
            ).single()
            session.run(
                "MATCH (n:FormationTwinOwned {tenant_id:$tenant_id,profile_id:$profile_id}) DETACH DELETE n",
                tenant_id=tenant_id, profile_id=profile_id,
            ).consume()
        return {"status": "ERASED", "deleted": int(result["deleted"] if result else 0)}
    finally:
        driver.close()
