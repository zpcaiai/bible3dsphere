"""Optional metadata-only temporal evidence PostgreSQL graph projection."""
from __future__ import annotations

import json
from typing import Any

from .formation_graph import graph_enabled

def _get_pool():
    try:
        try:
            from backend.graph_layer import _db_pool
        except Exception:
            from graph_layer import _db_pool  # type: ignore
        return _db_pool
    except Exception:
        return None

def sync_temporal_pattern(
    *, tenant_id: str, profile_id: str, pattern: dict[str, Any], evidence: list[dict[str, Any]],
    life_season_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Project identifiers/status/provenance only; never sensitive content."""
    if not graph_enabled():
        return {"status": "DISABLED", "nodes": 0, "relationships": 0}
    pool = _get_pool()
    if pool is None:
        return {"status": "UNAVAILABLE", "nodes": 0, "relationships": 0}
    eligible = [item for item in evidence if item.get("evidence_role") not in {"INVALIDATED", "SUPERSEDED"}]
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            props = json.dumps({
                "profile_id": profile_id,
                "pattern_type": pattern["pattern_type"],
                "lifecycle_status": pattern["lifecycle_status"],
                "user_review_status": pattern["user_review_status"],
                "version": int(pattern.get("version", 1)),
                "valid_from": str(pattern.get("first_observed_at") or ""),
                "valid_until": str(pattern.get("review_due_at") or "")
            })
            cur.execute(
                """
                INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties)
                VALUES (%s, 'FormationPattern', %s, %s)
                ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                SET properties = EXCLUDED.properties, updated_at = NOW()
                RETURNING id
                """,
                (tenant_id, str(pattern["id"]), props)
            )
            p_id = cur.fetchone()[0]

            for item in eligible:
                relation = "COUNTERED_BY" if item["evidence_role"] in {"COUNTEREVIDENCE", "CONTEXT_LIMIT"} else "SUPPORTED_BY"
                e_props = json.dumps({
                    "profile_id": profile_id,
                    "evidence_role": item["evidence_role"],
                    "source_record_type": item["source_record_type"],
                    "source_record_id": str(item["source_record_id"]),
                    "observed_at": str(item.get("occurred_at") or ""),
                    "status": item.get("user_review_status", "PENDING")
                })
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties)
                    VALUES (%s, 'PatternEvidence', %s, %s)
                    ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                    SET properties = EXCLUDED.properties, updated_at = NOW()
                    RETURNING id
                    """,
                    (tenant_id, str(item["id"]), e_props)
                )
                e_id = cur.fetchone()[0]

                r_props = json.dumps({
                    "role": item["evidence_role"],
                    "observed_at": str(item.get("occurred_at") or ""),
                    "valid_from": str(item.get("occurred_at") or ""),
                    "valid_until": "",
                    "status": item.get("user_review_status", "PENDING")
                })
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges (user_id, source_id, target_id, edge_type, properties)
                    VALUES (%s, %s::uuid, %s::uuid, %s, %s)
                    ON CONFLICT (user_id, source_id, target_id, edge_type)
                    DO UPDATE SET properties = EXCLUDED.properties, updated_at = NOW()
                    """,
                    (tenant_id, e_id, p_id, relation, r_props)
                )
            for season_id in life_season_ids or []:
                s_props = json.dumps({
                    "profile_id": profile_id
                })
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_nodes (user_id, node_type, node_name, properties)
                    VALUES (%s, 'LifeSeason', %s, %s)
                    ON CONFLICT (user_id, node_type, node_name) DO UPDATE
                    SET properties = EXCLUDED.properties, updated_at = NOW()
                    RETURNING id
                    """,
                    (tenant_id, str(season_id), s_props)
                )
                s_id = cur.fetchone()[0]
                r2_props = json.dumps({
                    "status": pattern["lifecycle_status"],
                    "valid_from": "", "valid_until": ""
                })
                cur.execute(
                    """
                    INSERT INTO mvfe_graph_edges (user_id, source_id, target_id, edge_type, properties)
                    VALUES (%s, %s::uuid, %s::uuid, 'ACTIVE_DURING', %s)
                    ON CONFLICT (user_id, source_id, target_id, edge_type)
                    DO UPDATE SET properties = EXCLUDED.properties, updated_at = NOW()
                    """,
                    (tenant_id, p_id, s_id, r2_props)
                )
        conn.commit()
        return {"status": "SYNCED", "nodes": 1 + len(eligible) + len(life_season_ids or []),
                "relationships": len(eligible) + len(life_season_ids or [])}
    except Exception:
        conn.rollback()
        return {"status": "FAILED", "nodes": 0, "relationships": 0}
    finally:
        pool.putconn(conn)

def invalidate_temporal_evidence(*, tenant_id: str, profile_id: str, evidence_id: str) -> dict[str, Any]:
    pool = _get_pool()
    if pool is None:
        return {"status": "UNAVAILABLE", "updated": 0}
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE mvfe_graph_nodes
                SET properties = jsonb_set(properties, '{status}', '"INVALIDATED"'::jsonb), updated_at = NOW()
                WHERE user_id = %s AND node_type = 'PatternEvidence' AND node_name = %s
                  AND properties->>'profile_id' = %s
                RETURNING id
                """,
                (tenant_id, evidence_id, profile_id)
            )
            row = cur.fetchone()
            updated = 0
            if row:
                updated += 1
                e_id = row[0]
                cur.execute(
                    """
                    UPDATE mvfe_graph_edges
                    SET properties = jsonb_set(properties, '{status}', '"INVALIDATED"'::jsonb), updated_at = NOW()
                    WHERE source_id = %s AND user_id = %s
                      AND properties->>'profile_id' = %s
                    """,
                    (e_id, tenant_id, profile_id)
                )
                updated += cur.rowcount
        conn.commit()
        return {"status": "UPDATED", "updated": updated}
    except Exception:
        conn.rollback()
        return {"status": "FAILED", "updated": 0}
    finally:
        pool.putconn(conn)

def graph_consistency_status(
    *,
    postgres_pattern_ids: set[str],
    tenant_id: str | None = None,
    profile_id: str | None = None,
    graph_pattern_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Compare canonical pattern IDs with the current PostgreSQL projection."""
    if graph_pattern_ids is None:
        graph_pattern_ids = set()
        pool = _get_pool()
        if pool is not None and tenant_id and profile_id:
            conn = pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT node_name FROM mvfe_graph_nodes
                        WHERE user_id=%s AND node_type='FormationPattern'
                          AND properties->>'profile_id'=%s
                        """,
                        (tenant_id, profile_id),
                    )
                    graph_pattern_ids = {str(row[0]) for row in cur.fetchall()}
            finally:
                pool.putconn(conn)
    missing = sorted(postgres_pattern_ids - graph_pattern_ids)
    orphaned = sorted(graph_pattern_ids - postgres_pattern_ids)
    return {"consistent": not missing and not orphaned, "missing_in_graph": missing, "orphaned_in_graph": orphaned}

def erase_temporal_graph(*, tenant_id: str, profile_id: str) -> dict[str, Any]:
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
                AND node_type IN ('FormationPattern', 'PatternEvidence', 'LifeSeason')
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
