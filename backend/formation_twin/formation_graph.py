"""Optional, metadata-only PostgreSQL projection for reviewed formation chains."""
from __future__ import annotations

import hashlib
import os
import json
from typing import Any

def _get_pool():
    try:
        try:
            from backend.graph_layer import _db_pool
        except Exception:
            from graph_layer import _db_pool  # type: ignore
        return _db_pool
    except Exception:
        return None

def graph_enabled() -> bool:
    # PostgreSQL is now the canonical graph store. Keep an explicit emergency
    # opt-out, but do not silently disable persistence in normal deployments.
    return os.getenv("FORMATION_TWIN_GRAPH_ENABLED", "true").lower() == "true"

def graph_status() -> dict[str, Any]:
    if not graph_enabled():
        return {"enabled": False, "configured": False, "status": "DISABLED"}
    pool = _get_pool()
    if pool is None:
        return {"enabled": True, "configured": False, "status": "UNAVAILABLE"}
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM mvfe_graph_nodes")
            nodes = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM mvfe_graph_edges")
            edges = cur.fetchone()[0]
        return {"enabled": True, "configured": True, "status": "AVAILABLE", "nodes": nodes, "edges": edges}
    except Exception:
        return {"enabled": True, "configured": True, "status": "ERROR"}
    finally:
        pool.putconn(conn)

def sync_reviewed_chain(*, tenant_id: str, profile_id: str, chain_id: str,
                        nodes: list[dict], edges: list[dict]) -> dict[str, Any]:
    """Sync IDs and hashes only. Full content is intentionally never projected."""
    if not graph_enabled():
        return {"status": "DISABLED", "nodes": 0, "edges": 0}
    pool = _get_pool()
    if pool is None:
        return {"status": "UNAVAILABLE", "nodes": 0, "edges": 0}
    safe_nodes = [item for item in nodes if item.get("user_review_status") in {"NOT_REQUIRED", "CONFIRMED", "PARTIALLY_CONFIRMED"}]
    safe_ids = {str(item["id"]) for item in safe_nodes}
    safe_edges = [item for item in edges if str(item["source_node_id"]) in safe_ids and str(item["target_node_id"]) in safe_ids]

    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            for item in safe_nodes:
                digest = hashlib.sha256(str(item.get("content") or "").encode()).hexdigest()
                props = json.dumps({
                    "tenant_id": tenant_id, "profile_id": profile_id, "chain_id": chain_id,
                    "node_type": item["node_type"], "source_kind": item["source_kind"],
                    "statement_type": item["statement_type"], "review_status": item["user_review_status"],
                    "content_hash": digest
                })
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties)
                    VALUES (%s, 'FormationNode', %s, %s)
                    ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                    SET properties = EXCLUDED.properties, updated_at = NOW()
                    """,
                    (tenant_id, str(item["id"]), props)
                )
            for item in safe_edges:
                # get source id
                cur.execute("SELECT id FROM mvfe_graph_nodes WHERE user_id=%s AND node_type='FormationNode' AND node_name=%s", (tenant_id, str(item["source_node_id"])))
                s_row = cur.fetchone()
                # get target id
                cur.execute("SELECT id FROM mvfe_graph_nodes WHERE user_id=%s AND node_type='FormationNode' AND node_name=%s", (tenant_id, str(item["target_node_id"])))
                t_row = cur.fetchone()
                if s_row and t_row:
                    s_id = s_row[0]
                    t_id = t_row[0]
                    props = json.dumps({
                        "profile_id": profile_id,
                        "edge_id": str(item["id"]),
                        "relation_type": item["relation_type"],
                        "statement_type": item["statement_type"]
                    })
                    cur.execute(
                        """
                        INSERT INTO mvfe_graph_edges (user_id, source_id, target_id, edge_type, properties)
                        VALUES (%s, %s::uuid, %s::uuid, 'FORMATION_LINK', %s)
                        ON CONFLICT (user_id, source_id, target_id, edge_type)
                        DO UPDATE SET properties = EXCLUDED.properties, updated_at = NOW()
                        """,
                        (tenant_id, s_id, t_id, props)
                    )
        conn.commit()
        return {"status": "SYNCED", "nodes": len(safe_nodes), "edges": len(safe_edges)}
    except Exception:
        conn.rollback()
        return {"status": "FAILED", "nodes": 0, "edges": 0}
    finally:
        pool.putconn(conn)

def erase_profile_graph(*, tenant_id: str, profile_id: str) -> dict[str, Any]:
    """Remove only the exact tenant/profile projection; never use a broad delete."""
    pool = _get_pool()
    if pool is None:
        return {"status": "UNAVAILABLE", "deleted": 0}
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id FROM mvfe_graph_nodes
                WHERE user_id = %s
                AND properties->>'profile_id' = %s
                """,
                (tenant_id, profile_id)
            )
            rows = cur.fetchall()
            deleted = len(rows)
            if rows:
                ids = tuple([r[0] for r in rows])
                cur.execute("DELETE FROM mvfe_graph_edges WHERE source_id IN %s OR target_id IN %s", (ids, ids))
                cur.execute("DELETE FROM mvfe_graph_nodes WHERE id IN %s", (ids,))
        conn.commit()
        return {"status": "ERASED", "deleted": deleted}
    except Exception:
        conn.rollback()
        return {"status": "FAILED", "deleted": 0}
    finally:
        pool.putconn(conn)
