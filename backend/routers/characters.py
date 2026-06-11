"""Biblical characters and relationship graph API."""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Query, Request, Response

from core.deps import acquire_conn, release_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/characters", tags=["characters"])


def _rows(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = None
    try:
        conn = acquire_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        conn.commit()
        return rows
    finally:
        release_conn(conn)


def _cacheable(request: Request, response: Response, payload: dict[str, Any]) -> Any:
    if not payload.get("success"):
        return payload
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    etag = '"' + hashlib.md5(body.encode("utf-8")).hexdigest() + '"'
    headers = {"Cache-Control": "public, max-age=1800", "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return payload


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _character_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "nameEn": row["name_en"],
        "era": row["era"],
        "role": row["role"],
        "kingdom": row.get("kingdom"),
        "characterType": row["character_type"],
        "lesson": row["lesson"],
        "summary": row["summary"],
        "witness": row["witness"],
        "scriptureRef": row["scripture_ref"],
        "prayer": row["prayer"],
        "tags": _as_list(row.get("tags")),
        "followPoints": _as_list(row.get("follow_points")),
        "cautionPoints": _as_list(row.get("caution_points")),
        "applications": _as_list(row.get("applications")),
        "scriptures": _as_list(row.get("scriptures")),
        "themes": _as_list(row.get("themes")),
        "sortOrder": row.get("sort_order", 0),
    }


def _node_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "label": row["name"],
        "name": row["name"],
        "nameEn": row["name_en"],
        "era": row["era"],
        "role": row["role"],
        "kingdom": row.get("kingdom"),
        "characterType": row["character_type"],
        "lesson": row["lesson"],
        "scriptureRef": row["scripture_ref"],
        "degree": int(row.get("degree") or 0),
        "outDegree": int(row.get("out_degree") or 0),
        "inDegree": int(row.get("in_degree") or 0),
    }


def _edge_dto(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source": row["source_id"],
        "target": row["target_id"],
        "sourceName": row["source_name"],
        "targetName": row["target_name"],
        "type": row["relationship_type"],
        "category": row["relationship_category"],
        "label": row["label_zh"],
        "labelEn": row.get("label_en"),
        "scriptureRef": row.get("scripture_ref"),
        "description": row.get("description"),
        "weight": float(row.get("weight") or 1),
        "confidence": float(row.get("confidence") or 1),
        "directed": bool(row.get("is_directed")),
    }


@router.get("")
def list_characters(
    request: Request,
    response: Response,
    q: Optional[str] = Query(None, max_length=80),
    era: Optional[str] = Query(None, max_length=50),
    role: Optional[str] = Query(None, max_length=50),
    type: Optional[str] = Query(None, max_length=20),
    kingdom: Optional[str] = Query(None, max_length=50),
    tag: Optional[str] = Query(None, max_length=50),
    theme: Optional[str] = Query(None, max_length=50),
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Any:
    clauses = ["true"]
    params: list[Any] = []
    if q:
        clauses.append("(name ILIKE %s OR name_en ILIKE %s OR lesson ILIKE %s OR summary ILIKE %s)")
        needle = f"%{q.strip()}%"
        params.extend([needle, needle, needle, needle])
    if era:
        clauses.append("era = %s")
        params.append(era)
    if role:
        clauses.append("role = %s")
        params.append(role)
    if type:
        clauses.append("character_type = %s")
        params.append(type)
    if kingdom:
        clauses.append("kingdom = %s")
        params.append(kingdom)
    if tag:
        clauses.append(
            "EXISTS (SELECT 1 FROM character_tags ct WHERE ct.character_id = v_character_full.id AND ct.tag = %s)"
        )
        params.append(tag)
    if theme:
        clauses.append(
            "EXISTS ("
            "SELECT 1 FROM character_theme_mappings ctm "
            "JOIN character_themes t ON t.id = ctm.theme_id "
            "WHERE ctm.character_id = v_character_full.id AND (t.id = %s OR t.name = %s)"
            ")"
        )
        params.extend([theme, theme])

    params.extend([limit, offset])
    try:
        rows = _rows(
            f"""
            SELECT *
            FROM v_character_full
            WHERE {' AND '.join(clauses)}
            ORDER BY sort_order, id
            LIMIT %s OFFSET %s
            """,
            tuple(params),
        )
        return _cacheable(
            request,
            response,
            {"success": True, "data": [_character_dto(row) for row in rows], "count": len(rows)},
        )
    except Exception as exc:
        logger.warning("characters list failed: %s", exc)
        return {"success": False, "error": str(exc), "data": []}


@router.get("/stats")
def character_stats(request: Request, response: Response) -> Any:
    try:
        era_rows = _rows("SELECT * FROM v_characters_by_era", ())
        role_rows = _rows("SELECT * FROM v_characters_by_role", ())
        type_rows = _rows(
            """
            SELECT character_type, COUNT(*) AS total_count
            FROM biblical_characters
            WHERE is_active = true
            GROUP BY character_type
            ORDER BY total_count DESC
            """,
            (),
        )
        relation_rows = _rows(
            """
            SELECT relationship_category, relationship_type, label_zh, COUNT(*) AS total_count
            FROM biblical_character_relationships
            WHERE is_active = true
            GROUP BY relationship_category, relationship_type, label_zh
            ORDER BY relationship_category, total_count DESC, relationship_type
            """,
            (),
        )
        payload = {
            "success": True,
            "data": {
                "byEra": era_rows,
                "byRole": role_rows,
                "byType": type_rows,
                "relationships": relation_rows,
            },
        }
        return _cacheable(request, response, payload)
    except Exception as exc:
        logger.warning("characters stats failed: %s", exc)
        return {"success": False, "error": str(exc), "data": {}}


@router.get("/graph")
def character_graph(
    request: Request,
    response: Response,
    focus: Optional[str] = Query(None, max_length=100),
    depth: int = Query(1, ge=1, le=3),
    era: Optional[str] = Query(None, max_length=50),
    role: Optional[str] = Query(None, max_length=50),
    relation_type: Optional[str] = Query(None, max_length=50),
    category: Optional[str] = Query(None, max_length=30),
    limit: int = Query(160, ge=1, le=500),
) -> Any:
    try:
        if focus:
            focus_like = focus if not focus.isdigit() else ""
            node_rows = _rows(
                """
                WITH RECURSIVE graph_nodes(id, depth) AS (
                    SELECT id, 0
                    FROM biblical_characters
                    WHERE is_active = true
                      AND (id::text = %s OR name = %s OR name_en ILIKE %s)
                    UNION
                    SELECT
                        CASE
                            WHEN r.source_character_id = graph_nodes.id THEN r.target_character_id
                            ELSE r.source_character_id
                        END,
                        graph_nodes.depth + 1
                    FROM graph_nodes
                    JOIN biblical_character_relationships r
                      ON r.is_active = true
                     AND (r.source_character_id = graph_nodes.id OR r.target_character_id = graph_nodes.id)
                    WHERE graph_nodes.depth < %s
                )
                SELECT n.*
                FROM v_biblical_character_graph_nodes n
                JOIN (
                    SELECT id, MIN(depth) AS depth
                    FROM graph_nodes
                    GROUP BY id
                ) gn ON gn.id = n.id
                ORDER BY gn.depth, n.degree DESC, n.id
                LIMIT %s
                """,
                (focus, focus, focus_like, depth, limit),
            )
        else:
            clauses = ["true"]
            params: list[Any] = []
            if era:
                clauses.append("era = %s")
                params.append(era)
            if role:
                clauses.append("role = %s")
                params.append(role)
            params.append(limit)
            node_rows = _rows(
                f"""
                SELECT *
                FROM v_biblical_character_graph_nodes
                WHERE {' AND '.join(clauses)}
                ORDER BY degree DESC, sort_order, id
                LIMIT %s
                """,
                tuple(params),
            )

        node_ids = [row["id"] for row in node_rows]
        if not node_ids:
            return _cacheable(request, response, {"success": True, "data": {"nodes": [], "edges": []}})

        edge_clauses = ["source_id = ANY(%s)", "target_id = ANY(%s)"]
        edge_params: list[Any] = [node_ids, node_ids]
        if relation_type:
            edge_clauses.append("relationship_type = %s")
            edge_params.append(relation_type)
        if category:
            edge_clauses.append("relationship_category = %s")
            edge_params.append(category)
        edge_params.append(limit * 3)
        edge_rows = _rows(
            f"""
            SELECT *
            FROM v_biblical_character_graph_edges
            WHERE {' AND '.join(edge_clauses)}
            ORDER BY weight DESC, sort_order, id
            LIMIT %s
            """,
            tuple(edge_params),
        )
        payload = {
            "success": True,
            "data": {
                "nodes": [_node_dto(row) for row in node_rows],
                "edges": [_edge_dto(row) for row in edge_rows],
            },
        }
        return _cacheable(request, response, payload)
    except Exception as exc:
        logger.warning("characters graph failed: %s", exc)
        return {"success": False, "error": str(exc), "data": {"nodes": [], "edges": []}}


@router.get("/{identifier}/relationships")
def character_relationships(
    identifier: str,
    request: Request,
    response: Response,
    category: Optional[str] = Query(None, max_length=30),
    relation_type: Optional[str] = Query(None, max_length=50),
) -> Any:
    clauses = ["(source_id = c.id OR target_id = c.id)"]
    params: list[Any] = [identifier, identifier, identifier]
    if category:
        clauses.append("relationship_category = %s")
        params.append(category)
    if relation_type:
        clauses.append("relationship_type = %s")
        params.append(relation_type)
    try:
        rows = _rows(
            f"""
            WITH c AS (
                SELECT id
                FROM biblical_characters
                WHERE is_active = true
                  AND (id::text = %s OR name = %s OR name_en ILIKE %s)
                LIMIT 1
            )
            SELECT e.*
            FROM v_biblical_character_graph_edges e, c
            WHERE {' AND '.join(clauses)}
            ORDER BY weight DESC, sort_order, id
            """,
            tuple(params),
        )
        return _cacheable(
            request,
            response,
            {"success": True, "data": [_edge_dto(row) for row in rows], "count": len(rows)},
        )
    except Exception as exc:
        logger.warning("character relationships failed: %s", exc)
        return {"success": False, "error": str(exc), "data": []}


@router.get("/{identifier}")
def character_detail(identifier: str, request: Request, response: Response) -> Any:
    try:
        rows = _rows(
            """
            SELECT *
            FROM v_character_full
            WHERE id::text = %s OR name = %s OR name_en ILIKE %s
            LIMIT 1
            """,
            (identifier, identifier, identifier),
        )
        if not rows:
            return _cacheable(request, response, {"success": True, "data": None})
        relations = _rows(
            """
            SELECT e.*
            FROM v_biblical_character_graph_edges e
            WHERE e.source_id = %s OR e.target_id = %s
            ORDER BY e.weight DESC, e.sort_order, e.id
            """,
            (rows[0]["id"], rows[0]["id"]),
        )
        data = _character_dto(rows[0])
        data["relationships"] = [_edge_dto(row) for row in relations]
        return _cacheable(request, response, {"success": True, "data": data})
    except Exception as exc:
        logger.warning("character detail failed: %s", exc)
        return {"success": False, "error": str(exc), "data": None}
