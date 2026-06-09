"""
圣经地图集（Bible Atlas）API —— 服务前端 emotion-sphere-ui/src/features/bible-map。
表由迁移 0039 建立并 seed（PostGIS geometry + GIST）。
返回统一 {success, data}；DB 不可用/出错时返回 success:false，前端回退本地 seed。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Query, Request

from core.deps import acquire_conn, release_conn
from core.ratelimit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/bible-map", tags=["bible-map"])


def _rows(sql: str, params: tuple) -> list[dict[str, Any]]:
    conn = None
    try:
        conn = acquire_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            out = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.commit()
        return out
    finally:
        release_conn(conn)


def _gj(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return None
    return None


def _territory_dto(r: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": r["id"], "name": r["name"], "nameZh": r["name_zh"],
        "ownerType": r["owner_type"], "ownerId": r["owner_id"], "ownerName": r["owner_name"],
        "period": r["period"], "startYear": r["start_year"], "endYear": r["end_year"],
        "controlScore": r["control_score"], "status": r["status"], "color": r["color"],
        "geojson": _gj(r["geojson"]), "description": r["description"],
        "descriptionEn": r.get("description_en"),
    }


@router.get("/territories")
def territories(year: int = Query(-1200), layer: str = Query("all")) -> dict[str, Any]:
    try:
        rows = _rows(
            "SELECT * FROM bible_territories WHERE start_year <= %s AND (end_year IS NULL OR end_year >= %s)",
            (year, year),
        )
        data = [_territory_dto(r) for r in rows]
        if layer == "tribes":
            data = [t for t in data if t["ownerType"] == "tribe"]
        elif layer == "empires":
            data = [t for t in data if t["ownerType"] == "empire"]
        return {"success": True, "data": data}
    except Exception as e:
        logger.warning("bible-map territories: %s", e)
        return {"success": False, "error": str(e)}


@router.get("/territories/at")
def territory_at(lng: float = Query(...), lat: float = Query(...), year: int = Query(-1200)) -> dict[str, Any]:
    try:
        rows = _rows(
            "SELECT * FROM bible_territories WHERE geom IS NOT NULL "
            "AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s,%s),4326)) "
            "AND start_year <= %s AND (end_year IS NULL OR end_year >= %s)",
            (lng, lat, year, year),
        )
        return {"success": True, "data": [_territory_dto(r) for r in rows]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/events")
def events(year: int = Query(-1200)) -> dict[str, Any]:
    try:
        rows = _rows(
            "SELECT * FROM bible_events WHERE abs(start_year - %s) <= 150 "
            "OR (start_year <= %s AND COALESCE(end_year, start_year) >= %s) ORDER BY start_year",
            (year, year, year),
        )
        data = [{
            "id": r["id"], "title": r["title"], "titleZh": r["title_zh"], "category": r["category"],
            "book": r["book"], "chapter": r["chapter"], "startYear": r["start_year"], "endYear": r["end_year"],
            "locationName": r["location_name"], "latitude": r["latitude"], "longitude": r["longitude"],
            "geojson": _gj(r["geojson"]), "description": r["description"], "spiritualMeaning": r["spiritual_meaning"],
            "descriptionEn": r.get("description_en"), "spiritualMeaningEn": r.get("spiritual_meaning_en"),
        } for r in rows]
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/prophecies")
def prophecies(book: Optional[str] = Query(None), chapter: Optional[int] = Query(None)) -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM bible_prophecies", ())
        data = [{
            "id": r["id"], "book": r["book"], "chapterStart": r["chapter_start"], "chapterEnd": r["chapter_end"],
            "targetNation": r["target_nation"], "targetNationZh": r["target_nation_zh"], "prophecyType": r["prophecy_type"],
            "startYear": r["start_year"], "fulfillmentYear": r["fulfillment_year"], "sourceLocation": r["source_location"],
            "targetLatitude": r["target_latitude"], "targetLongitude": r["target_longitude"],
            "description": r["description"], "fulfillmentDescription": r["fulfillment_description"],
            "descriptionEn": r.get("description_en"), "fulfillmentDescriptionEn": r.get("fulfillment_description_en"),
        } for r in rows]
        if book:
            data = [p for p in data if p["book"].lower() == book.lower()]
        if chapter is not None:
            data = [p for p in data if p["chapterStart"] <= chapter <= (p["chapterEnd"] or p["chapterStart"])]
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/campaigns")
def campaigns(id: Optional[str] = Query(None)) -> dict[str, Any]:
    try:
        rows = _rows("SELECT * FROM bible_campaigns", ())
        data = [{
            "id": r["id"], "name": r["name"], "nameZh": r["name_zh"], "commander": r["commander"],
            "commanderZh": r["commander_zh"], "startYear": r["start_year"], "endYear": r["end_year"],
            "book": r["book"], "chapter": r["chapter"],
            "routeGeojson": _gj(r["route_geojson"]), "pointsGeojson": _gj(r["points_geojson"]),
            "description": r["description"], "descriptionEn": r.get("description_en"),
        } for r in rows]
        if id:
            data = [c for c in data if c["id"] == id]
        return {"success": True, "data": data}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _build_graph() -> dict[str, Any]:
    terr = _rows("SELECT id, name_zh, owner_type FROM bible_territories", ())
    props = _rows("SELECT id, book, chapter_start, target_nation, target_nation_zh FROM bible_prophecies", ())
    camps = _rows("SELECT id, name_zh, commander_zh FROM bible_campaigns", ())
    nodes: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(nid: str, label: str, kind: str) -> None:
        if nid in seen:
            return
        seen.add(nid)
        nodes.append({"id": nid, "label": label, "kind": kind})

    edges: list[dict[str, str]] = []
    for t in terr:
        add(t["id"], t["name_zh"], "tribe" if t["owner_type"] == "tribe" else "empire")
    for p in props:
        add(p["id"], f"{p['book']}{p['chapter_start']} 论{p['target_nation_zh']}", "prophecy")
        nid = "nation-" + p["target_nation"].lower()
        add(nid, p["target_nation_zh"], "nation")
        edges.append({"source": p["id"], "target": nid, "type": "AGAINST"})
    for c in camps:
        add(c["id"], c["name_zh"], "campaign")
        if c["commander_zh"]:
            cid = "commander-" + c["id"]
            add(cid, c["commander_zh"], "commander")
            edges.append({"source": c["id"], "target": cid, "type": "LED_BY"})
    add("nation-israel", "北国以色列", "nation")
    add("nation-judah", "南国犹大", "nation")
    static_edges = [
        ("empire-assyria", "nation-israel", "CONQUERED"),
        ("empire-babylon", "nation-judah", "CONQUERED"),
        ("empire-babylon", "nation-tyre", "CONQUERED"),
        ("empire-persia", "nation-babylon", "CONQUERED"),
        ("empire-babylon", "empire-assyria", "SUCCEEDED"),
        ("empire-persia", "empire-babylon", "SUCCEEDED"),
        ("empire-greece", "empire-persia", "SUCCEEDED"),
        ("empire-rome", "empire-greece", "SUCCEEDED"),
        ("tribe-judah", "tribe-benjamin", "NEIGHBORS"),
        ("tribe-judah", "tribe-simeon", "NEIGHBORS"),
        ("tribe-benjamin", "tribe-ephraim", "NEIGHBORS"),
        ("tribe-gad", "tribe-reuben", "NEIGHBORS"),
    ]
    ids = {n["id"] for n in nodes}
    for s, t, ty in static_edges:
        if s in ids and t in ids:
            edges.append({"source": s, "target": t, "type": ty})
    return {"nodes": nodes, "edges": edges}


@router.get("/graph")
def graph(node: Optional[str] = Query(None)) -> dict[str, Any]:
    try:
        g = _build_graph()
        if not node:
            return {"success": True, "data": g}
        nmap = {n["id"]: n for n in g["nodes"]}
        if node not in nmap:
            return {"success": False, "error": f"未找到节点 {node}"}
        neighbors = []
        for e in g["edges"]:
            if e["source"] == node and e["target"] in nmap:
                neighbors.append({"type": e["type"], "direction": "out", "node": nmap[e["target"]]})
            elif e["target"] == node and e["source"] in nmap:
                neighbors.append({"type": e["type"], "direction": "in", "node": nmap[e["source"]]})
        return {"success": True, "data": {"node": nmap[node], "neighbors": neighbors, "source": "local"}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _ai_template(name: str) -> str:
    return (
        f"关于「{name}」，从四个维度作教学性讲解：\n"
        "① 历史背景：在圣经历史脉络中的位置与年代。\n"
        "② 地理意义：地形与战略价值如何影响事件。\n"
        "③ 属灵意义：经文借此彰显的神的属性与救赎主题。\n"
        "④ 现代应用：对今日信徒的提醒。\n"
        "（属近似教学说明。）"
    )


@router.post("/ai")
@limiter.limit("20/minute")
async def ai(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        body = {}
    name = str(body.get("name") or "所选内容")[:200]  # 限长，防 prompt 滥用/成本放大
    kind = str(body.get("kind") or "")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return {"success": True, "data": {"commentary": _ai_template(name), "source": "template"}}
    try:
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        try:
            from lang_context import is_english as _is_en
            _en = _is_en()
        except Exception:
            _en = False
        if _en:
            prompt = (
                f"You are a Bible history & geography teaching assistant. For '{name}' "
                f"(type: {kind}), write about 200 words of warm, accurate commentary in "
                "natural English across four dimensions: historical background, geographic "
                "significance, spiritual meaning, and modern application. Note that it is an "
                "approximate teaching aid. Use standard English Bible names and references."
            )
        else:
            prompt = (
                f"你是圣经历史地理教学助手。针对「{name}」（类型：{kind}），用简体中文从历史背景、"
                "地理意义、属灵意义、现代应用四个维度写约200字、温暖准确的讲解，注明属近似教学说明。"
            )
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.7},
            )
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return {"success": True, "data": {"commentary": content, "source": "llm"}}
    except Exception as e:
        logger.warning("bible-map ai: %s", e)
    return {"success": True, "data": {"commentary": _ai_template(name), "source": "template"}}
