"""Optional, metadata-only Neo4j projection for reviewed formation chains."""
from __future__ import annotations

import hashlib
import os
from typing import Any


def graph_enabled() -> bool:
    return os.getenv("FORMATION_TWIN_GRAPH_ENABLED", "false").lower() == "true"


def graph_status() -> dict[str, Any]:
    if not graph_enabled():
        return {"enabled": False, "configured": False, "status": "DISABLED"}
    try:
        from mvfe.db.neo4j import get_neo4j_driver
        driver = get_neo4j_driver()
    except Exception:
        driver = None
    if driver is None:
        return {"enabled": True, "configured": False, "status": "UNAVAILABLE"}
    driver.close()
    return {"enabled": True, "configured": True, "status": "AVAILABLE"}


def sync_reviewed_chain(*, tenant_id: str, profile_id: str, chain_id: str,
                        nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
    """Sync IDs and hashes only. Full content is intentionally never projected."""
    if not graph_enabled():
        return {"status": "DISABLED", "nodes": 0, "edges": 0}
    try:
        from mvfe.db.neo4j import get_neo4j_driver
        driver = get_neo4j_driver()
    except Exception:
        driver = None
    if driver is None:
        return {"status": "UNAVAILABLE", "nodes": 0, "edges": 0}
    safe_nodes = [item for item in nodes if item.get("user_review_status") in {"NOT_REQUIRED", "CONFIRMED", "PARTIALLY_CONFIRMED"}]
    safe_ids = {str(item["id"]) for item in safe_nodes}
    safe_edges = [item for item in edges if str(item["source_node_id"]) in safe_ids and str(item["target_node_id"]) in safe_ids]
    try:
        with driver.session() as session:
            for item in safe_nodes:
                digest = hashlib.sha256(str(item.get("content") or "").encode()).hexdigest()
                session.run(
                    "MERGE (n:FormationNode {tenant_id:$tenant_id,profile_id:$profile_id,node_id:$node_id}) "
                    "SET n.chain_id=$chain_id,n.node_type=$node_type,n.source_kind=$source_kind,"
                    "n.statement_type=$statement_type,n.review_status=$review_status,n.content_hash=$content_hash",
                    tenant_id=tenant_id, profile_id=profile_id, node_id=str(item["id"]), chain_id=chain_id,
                    node_type=item["node_type"], source_kind=item["source_kind"],
                    statement_type=item["statement_type"], review_status=item["user_review_status"], content_hash=digest,
                )
            for item in safe_edges:
                session.run(
                    "MATCH (a:FormationNode {tenant_id:$tenant_id,profile_id:$profile_id,node_id:$source}),"
                    "(b:FormationNode {tenant_id:$tenant_id,profile_id:$profile_id,node_id:$target}) "
                    "MERGE (a)-[r:FORMATION_LINK {tenant_id:$tenant_id,profile_id:$profile_id,edge_id:$edge_id}]->(b) "
                    "SET r.relation_type=$relation_type,r.statement_type=$statement_type",
                    tenant_id=tenant_id, profile_id=profile_id, source=str(item["source_node_id"]),
                    target=str(item["target_node_id"]), edge_id=str(item["id"]),
                    relation_type=item["relation_type"], statement_type=item["statement_type"],
                )
        return {"status": "SYNCED", "nodes": len(safe_nodes), "edges": len(safe_edges)}
    finally:
        driver.close()


def erase_profile_graph(*, tenant_id: str, profile_id: str) -> dict[str, Any]:
    """Remove only the exact tenant/profile projection; never use a broad delete."""
    # Erasure intentionally ignores the feature flag: a user must be able to
    # remove an older projection after an administrator disables new syncs.
    try:
        from mvfe.db.neo4j import get_neo4j_driver
        driver = get_neo4j_driver()
    except Exception:
        driver = None
    if driver is None:
        return {"status": "UNAVAILABLE", "deleted": 0}
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (n {tenant_id:$tenant_id,profile_id:$profile_id}) "
                "WHERE n:FormationNode OR n:FormationTwinOwned RETURN count(n) AS deleted",
                tenant_id=tenant_id, profile_id=profile_id,
            ).single()
            session.run(
                "MATCH (n {tenant_id:$tenant_id,profile_id:$profile_id}) "
                "WHERE n:FormationNode OR n:FormationTwinOwned DETACH DELETE n",
                tenant_id=tenant_id, profile_id=profile_id,
            ).consume()
        return {"status": "ERASED", "deleted": int(result["deleted"] if result else 0)}
    finally:
        driver.close()
