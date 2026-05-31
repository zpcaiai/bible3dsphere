"""
Biblical geography router — time-sliced GeoJSON over the PostGIS temporal model.

Backs the frontend 圣经地图 (出埃及/旷野漂流 et al.). Reads tables created by
migration 0007 and seeded by 0008. All responses are GeoJSON so the map layer
(LeafletAdapter today, MapboxAdapter later) can consume them directly.

Endpoints:
  GET /api/geo/scripture   ?book=NUM&chapter=33[&year=-1446]   场景A：读经联动
  GET /api/geo/entity      ?name=耶路撒冷&year=-450             场景B：时间轴切片
  GET /api/geo/routes/{route_name}                              路线 LineString
  GET /api/geo/exodus                                           出埃及42站 + 路线（便捷）
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Query

from core.deps import acquire_conn, release_conn

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/geo", tags=["geo"])


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


def _query(sql, params):
    conn = None
    try:
        conn = acquire_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.commit()
        return rows
    except Exception as e:  # PostGIS missing / not migrated yet → 503
        if conn:
            conn.rollback()
        logger.warning("geo query failed: %s", e)
        raise HTTPException(status_code=503, detail="圣经地理数据暂不可用（请确认 PostGIS 迁移已应用）")
    finally:
        release_conn(conn)


@router.get("/scripture")
def scripture_features(
    book: str = Query(..., description="书卷代码，如 NUM/GEN/ACT"),
    chapter: int = Query(...),
    year: int | None = Query(None, description="历史年份（公元前为负）。给定则取该时代的地名"),
):
    """场景A：读经联动 — 返回某章提及的地点，名称取指定年代的称呼。"""
    if year is None:
        sql = """
            SELECT DISTINCT ON (ge.entity_id)
                   ge.entity_id, en.name_zh, en.name_en,
                   sg.association_type, ST_AsGeoJSON(eg.geom_point) AS geom
            FROM scripture_geo_mappings sg
            JOIN geo_entities ge ON sg.entity_id = ge.entity_id
            LEFT JOIN entity_geometries eg ON ge.entity_id = eg.entity_id
            LEFT JOIN entity_names en ON ge.entity_id = en.entity_id
            WHERE sg.book_code = %s AND sg.chapter = %s
            ORDER BY ge.entity_id
        """
        rows = _query(sql, (book.upper(), chapter))
    else:
        sql = """
            SELECT ge.entity_id, en.name_zh, en.name_en,
                   sg.association_type, ST_AsGeoJSON(eg.geom_point) AS geom
            FROM scripture_geo_mappings sg
            JOIN geo_entities ge ON sg.entity_id = ge.entity_id
            JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> %s
            JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> %s
            WHERE sg.book_code = %s AND sg.chapter = %s
        """
        rows = _query(sql, (year, year, book.upper(), chapter))
    feats = [{
        "type": "Feature",
        "geometry": json.loads(r["geom"]) if r["geom"] else None,
        "properties": {"entity_id": r["entity_id"], "name_zh": r["name_zh"],
                       "name_en": r["name_en"], "association": r["association_type"]},
    } for r in rows]
    return _fc(feats)


@router.get("/entity")
def entity_at_year(
    name: str = Query(..., description="地名（任一时代的中文名）"),
    year: int = Query(..., description="历史年份（公元前为负）"),
):
    """场景B：时间轴切片 — 给定地名与年份，返回该时代的称呼与几何（点/多边形）。"""
    sql = """
        SELECT en.name_zh, en.name_en,
               ST_AsGeoJSON(eg.geom_point)   AS pt,
               ST_AsGeoJSON(eg.geom_polygon) AS poly
        FROM geo_entities ge
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> %s
        JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> %s
        WHERE ge.entity_id IN (SELECT entity_id FROM entity_names WHERE name_zh = %s)
    """
    rows = _query(sql, (year, year, name))
    feats = []
    for r in rows:
        geom = r["poly"] or r["pt"]
        feats.append({
            "type": "Feature",
            "geometry": json.loads(geom) if geom else None,
            "properties": {"name_zh": r["name_zh"], "name_en": r["name_en"], "year": year},
        })
    return _fc(feats)


@router.get("/routes/{route_name}")
def route(route_name: str):
    rows = _query(
        "SELECT route_name, ST_AsGeoJSON(geom_line) AS geom, lower(valid_time) AS y0, upper(valid_time) AS y1 "
        "FROM historical_routes WHERE route_name = %s",
        (route_name,),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="路线不存在")
    r = rows[0]
    return {"type": "Feature",
            "geometry": json.loads(r["geom"]) if r["geom"] else None,
            "properties": {"route_name": r["route_name"], "start_year": r["y0"], "end_year": r["y1"]}}


@router.get("/paul")
def paul():
    """保罗宣教城市（entity_type=city，保罗时代 valid_time 含公元50年），含 events/confidence。"""
    cities = _query(
        """
        SELECT ge.entity_id, en.name_zh, en.name_en, eg.confidence,
               ST_AsGeoJSON(eg.geom_point) AS geom,
               (SELECT json_agg(json_build_object('title', title, 'ref', scripture_ref, 'summary', summary, 'image', image, 'audio', audio) ORDER BY seq)
                  FROM geo_events ev WHERE ev.entity_id = ge.entity_id) AS events
        FROM geo_entities ge
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> 50
        JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> 50
        WHERE ge.entity_type = 'city'
        ORDER BY ge.entity_id
        """,
        (),
    )
    feats = [{
        "type": "Feature",
        "geometry": json.loads(c["geom"]) if c["geom"] else None,
        "properties": {"name_zh": c["name_zh"], "name_en": c["name_en"],
                       "confidence": c.get("confidence"), "events": c.get("events") or []},
    } for c in cities]
    return _fc(feats)


@router.get("/timeline")
def timeline(
    slug: str = Query(..., description="实体稳定键，如 jerusalem"),
    year: int = Query(..., description="历史年份（公元前为负）"),
):
    """时空切片：返回某 slug 地点在指定年份的疆域(polygon优先)与当时名称。"""
    rows = _query(
        """
        SELECT en.name_zh, en.name_en, eg.confidence,
               ST_AsGeoJSON(eg.geom_polygon) AS poly,
               ST_AsGeoJSON(eg.geom_point)   AS pt
        FROM geo_entities ge
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> %s
        JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> %s
        WHERE ge.slug = %s
        LIMIT 1
        """,
        (year, year, slug),
    )
    if not rows:
        raise HTTPException(status_code=404, detail="该年份无对应时空切片")
    r = rows[0]
    geom = r["poly"] or r["pt"]
    return {
        "type": "Feature",
        "geometry": json.loads(geom) if geom else None,
        "properties": {"name_zh": r["name_zh"], "name_en": r["name_en"],
                       "confidence": r.get("confidence"), "year": year},
    }


@router.get("/regions")
def regions(year: int = Query(..., description="历史年份（公元前为负）")):
    """某年有效的政治疆域多边形（entity_type=region），用于疆域演变时空切片。"""
    rows = _query(
        """
        SELECT ge.slug, en.name_zh, en.name_en, ST_AsGeoJSON(eg.geom_polygon) AS poly
        FROM geo_entities ge
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> %s
        JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> %s
        WHERE ge.entity_type = 'region' AND eg.geom_polygon IS NOT NULL
        """,
        (year, year),
    )
    feats = [{
        "type": "Feature",
        "geometry": json.loads(r["poly"]) if r["poly"] else None,
        "properties": {"slug": r["slug"], "name_zh": r["name_zh"], "name_en": r["name_en"]},
    } for r in rows]
    return _fc(feats)


@router.get("/relations")
def relations(
    slug: str = Query(..., description="实体稳定键"),
    year: int | None = Query(None, description="可选：仅返回该年有效的关系"),
):
    """拓扑图谱：返回某实体的关系（隶属/包含/相邻/首都），双向。"""
    yf = "AND (r.valid_time IS NULL OR r.valid_time @> %s)" if year is not None else ""
    base_out = f"""
        SELECT r.relation_type,
               dst.slug AS other_slug,
               (SELECT name_zh FROM entity_names WHERE entity_id = dst.entity_id ORDER BY name_id LIMIT 1) AS other_name,
               'out' AS dir
        FROM geo_relations r
        JOIN geo_entities src ON r.src_entity_id = src.entity_id
        JOIN geo_entities dst ON r.dst_entity_id = dst.entity_id
        WHERE src.slug = %s {yf}
    """
    base_in = f"""
        SELECT r.relation_type,
               src.slug AS other_slug,
               (SELECT name_zh FROM entity_names WHERE entity_id = src.entity_id ORDER BY name_id LIMIT 1) AS other_name,
               'in' AS dir
        FROM geo_relations r
        JOIN geo_entities src ON r.src_entity_id = src.entity_id
        JOIN geo_entities dst ON r.dst_entity_id = dst.entity_id
        WHERE dst.slug = %s {yf}
    """
    if year is not None:
        params = (year, slug, year, slug)
    else:
        params = (slug, slug)
    rows = _query(base_out + " UNION ALL " + base_in, params)
    return {"slug": slug, "relations": rows}


@router.get("/landmarks")
def landmarks(year: int = Query(..., description="历史年份（公元前为负）")):
    """某年存在的地标点（entity_type=landmark），用于疆域视图叠加。"""
    rows = _query(
        """
        SELECT ge.slug, en.name_zh, en.name_en, ST_AsGeoJSON(eg.geom_point) AS geom
        FROM geo_entities ge
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id AND eg.valid_time @> %s
        JOIN entity_names en ON ge.entity_id = en.entity_id AND en.valid_time @> %s
        WHERE ge.entity_type = 'landmark'
        """,
        (year, year),
    )
    feats = [{
        "type": "Feature",
        "geometry": json.loads(r["geom"]) if r["geom"] else None,
        "properties": {"slug": r["slug"], "name_zh": r["name_zh"], "name_en": r["name_en"]},
    } for r in rows]
    return _fc(feats)


@router.get("/exodus")
def exodus():
    """便捷端点：出埃及42个安营点（带经文映射）+ 路线，一次返回。"""
    stations = _query(
        """
        SELECT ge.entity_id, en.name_zh, en.name_en, en.name_hebrew,
               sg.chapter, sg.verse_start, sg.verse_end,
               eg.confidence,
               ST_AsGeoJSON(eg.geom_point) AS geom,
               (SELECT json_agg(json_build_object('title', title, 'ref', scripture_ref, 'summary', summary, 'image', image, 'audio', audio) ORDER BY seq)
                  FROM geo_events ev WHERE ev.entity_id = ge.entity_id) AS events
        FROM scripture_geo_mappings sg
        JOIN geo_entities ge ON sg.entity_id = ge.entity_id
        JOIN entity_geometries eg ON ge.entity_id = eg.entity_id
        JOIN entity_names en ON ge.entity_id = en.entity_id
        WHERE sg.book_code = 'NUM' AND sg.chapter = 33 AND sg.association_type = 'camp'
        ORDER BY ge.entity_id
        """,
        (),
    )
    feats = [{
        "type": "Feature",
        "geometry": json.loads(s["geom"]) if s["geom"] else None,
        "properties": {"order": i + 1, "name_zh": s["name_zh"], "name_en": s["name_en"],
                       "name_he": s["name_hebrew"], "confidence": s.get("confidence"),
                       "events": s.get("events") or [],
                       "scriptureRef": f"民33:{s['verse_start']}" + (
                           f"-{s['verse_end']}" if s["verse_end"] != s["verse_start"] else "")},
    } for i, s in enumerate(stations)]
    route_rows = _query("SELECT ST_AsGeoJSON(geom_line) AS geom FROM historical_routes WHERE route_name='Exodus_Traditional'", ())
    route_geom = json.loads(route_rows[0]["geom"]) if route_rows and route_rows[0]["geom"] else None
    return {"stations": _fc(feats), "route": route_geom}
