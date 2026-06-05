"""
admin_catalog.py — 管理端：慕道班/主日学/甘露/诗歌/书籍/门徒/牧养/事件。

prefix: /api/admin
鉴权：每个端点首先调用 require_admin(request)。
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

try:
    from routers.admin_common import _state, require_admin, audit, paginate
except ImportError:
    from backend.routers.admin_common import _state, require_admin, audit, paginate

router = APIRouter(prefix="/api/admin", tags=["admin-catalog"])


# ─────────────────────────────────────────────────────────────────────────────
# 慕道班 seekers_class_courses CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/seekers-courses")
def admin_list_seekers_courses(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM seekers_class_courses")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, title, teacher, scripture, description,
                       text_url, ppt_url, video_url, duration_sec,
                       sort_order, is_visible, created_at
                FROM seekers_class_courses
                ORDER BY sort_order ASC, created_at ASC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "title": r[1], "teacher": r[2], "scripture": r[3],
                    "description": r[4], "text_url": r[5], "ppt_url": r[6],
                    "video_url": r[7], "duration_sec": r[8],
                    "sort_order": r[9], "is_visible": r[10], "created_at": iso(r[11]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


class SeekersCourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    teacher: str = Field(default="", max_length=100)
    scripture: str = Field(default="", max_length=500)
    description: str = Field(default="")
    text_url: str = Field(default="", max_length=1000)
    ppt_url: str = Field(default="", max_length=1000)
    video_url: str = Field(default="", max_length=1000)
    duration_sec: int = Field(default=0, ge=0)
    sort_order: int = Field(default=0, ge=0)
    is_visible: bool = True


@router.post("/seekers-courses")
def admin_create_seekers_course(request: Request, body: SeekersCourseCreate) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO seekers_class_courses
                    (title, teacher, scripture, description,
                     text_url, ppt_url, video_url,
                     duration_sec, sort_order, is_visible)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    body.title, body.teacher, body.scripture, body.description,
                    body.text_url, body.ppt_url, body.video_url,
                    body.duration_sec, body.sort_order, body.is_visible,
                ),
            )
            new_id = cur.fetchone()[0]
            audit(cur, admin["email"], "seekers_course.create", "seekers_course",
                  str(new_id), {"title": body.title})
            conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        _state["release_db"](conn)


class SeekersCourseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    teacher: Optional[str] = Field(default=None, max_length=100)
    scripture: Optional[str] = None
    description: Optional[str] = None
    text_url: Optional[str] = Field(default=None, max_length=1000)
    ppt_url: Optional[str] = Field(default=None, max_length=1000)
    video_url: Optional[str] = Field(default=None, max_length=1000)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_visible: Optional[bool] = None


@router.put("/seekers-courses/{course_id}")
def admin_update_seekers_course(
    request: Request, course_id: int, body: SeekersCourseUpdate
) -> dict:
    admin = require_admin(request)
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="无更新字段")
    # 白名单列
    allowed = {"title","teacher","scripture","description","text_url",
               "ppt_url","video_url","duration_sec","sort_order","is_visible"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE seekers_class_courses SET {set_clause} WHERE id = %s",
                values + [course_id],
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="课程不存在")
            audit(cur, admin["email"], "seekers_course.update", "seekers_course",
                  str(course_id), fields)
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.delete("/seekers-courses/{course_id}")
def admin_delete_seekers_course(request: Request, course_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title FROM seekers_class_courses WHERE id = %s", (course_id,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="课程不存在")
            cur.execute(
                "DELETE FROM seekers_class_courses WHERE id = %s", (course_id,)
            )
            audit(cur, admin["email"], "seekers_course.delete", "seekers_course",
                  str(course_id), {"title": row[0]})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.get("/seekers-courses/r2-files")
def admin_seekers_r2_files(request: Request) -> dict:
    require_admin(request)
    import os
    account_id  = os.environ.get("R2_ACCOUNT_ID", "").strip()
    access_key  = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    secret_key  = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    bucket_name = os.environ.get("R2_BUCKET_NAME", "").strip()
    prefix      = os.environ.get("R2_SEEKERS_PREFIX", "seekers-class/").strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        return {"ok": True, "items": [], "note": "R2 未配置"}
    try:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        paginator = client.get_paginator("list_objects_v2")
        items = []
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                fname = key[len(prefix):]
                if not fname:
                    continue
                items.append({"key": key, "filename": fname, "size": obj.get("Size", 0)})
        return {"ok": True, "items": items, "readonly": True}
    except Exception as exc:
        return {"ok": True, "items": [], "note": f"R2 枚举失败: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# 主日学 sunday_school_videos CRUD
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/sunday-school-videos")
def admin_list_sunday_school_videos(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM sunday_school_videos")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, title, teacher, scripture, description,
                       video_url, thumbnail_url, duration_sec,
                       sort_order, is_visible, created_at
                FROM sunday_school_videos
                ORDER BY sort_order ASC, created_at ASC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "title": r[1], "teacher": r[2], "scripture": r[3],
                    "description": r[4], "video_url": r[5], "thumbnail_url": r[6],
                    "duration_sec": r[7], "sort_order": r[8],
                    "is_visible": r[9], "created_at": iso(r[10]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


class SSVideoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    teacher: str = Field(default="", max_length=100)
    scripture: str = Field(default="")
    description: str = Field(default="")
    video_url: str = Field(min_length=1, max_length=1000)
    thumbnail_url: str = Field(default="", max_length=1000)
    duration_sec: int = Field(default=0, ge=0)
    sort_order: int = Field(default=0, ge=0)
    is_visible: bool = True


@router.post("/sunday-school-videos")
def admin_create_sunday_school_video(request: Request, body: SSVideoCreate) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sunday_school_videos
                    (title, teacher, scripture, description,
                     video_url, thumbnail_url, duration_sec, sort_order, is_visible)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
                """,
                (
                    body.title, body.teacher, body.scripture, body.description,
                    body.video_url, body.thumbnail_url,
                    body.duration_sec, body.sort_order, body.is_visible,
                ),
            )
            new_id = cur.fetchone()[0]
            audit(cur, admin["email"], "ss_video.create", "sunday_school_video",
                  str(new_id), {"title": body.title})
            conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        _state["release_db"](conn)


class SSVideoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    teacher: Optional[str] = Field(default=None, max_length=100)
    scripture: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = Field(default=None, max_length=1000)
    thumbnail_url: Optional[str] = Field(default=None, max_length=1000)
    duration_sec: Optional[int] = Field(default=None, ge=0)
    sort_order: Optional[int] = Field(default=None, ge=0)
    is_visible: Optional[bool] = None


@router.put("/sunday-school-videos/{vid}")
def admin_update_sunday_school_video(
    request: Request, vid: int, body: SSVideoUpdate
) -> dict:
    admin = require_admin(request)
    fields = body.model_dump(exclude_none=True)
    if not fields:
        raise HTTPException(status_code=400, detail="无更新字段")
    allowed = {"title","teacher","scripture","description","video_url",
               "thumbnail_url","duration_sec","sort_order","is_visible"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values())
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE sunday_school_videos SET {set_clause} WHERE id = %s",
                values + [vid],
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="视频不存在")
            audit(cur, admin["email"], "ss_video.update", "sunday_school_video",
                  str(vid), fields)
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


@router.delete("/sunday-school-videos/{vid}")
def admin_delete_sunday_school_video(request: Request, vid: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT title FROM sunday_school_videos WHERE id = %s", (vid,)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="视频不存在")
            cur.execute("DELETE FROM sunday_school_videos WHERE id = %s", (vid,))
            audit(cur, admin["email"], "ss_video.delete", "sunday_school_video",
                  str(vid), {"title": row[0]})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 清晨甘露
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/dew")
def admin_list_dew(
    request: Request,
    from_date: str = Query(default="", alias="from"),
    to_date: str = Query(default="", alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []
            if from_date:
                filters.append("dew_date >= %s::date")
                params.append(from_date)
            if to_date:
                filters.append("dew_date <= %s::date")
                params.append(to_date)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM daily_dew {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT dew_date, tier, created_at
                FROM daily_dew {where}
                ORDER BY dew_date DESC, tier ASC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {"dew_date": str(r[0]), "tier": r[1], "created_at": iso(r[2])}
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/dew/{date}/{tier}")
def admin_get_dew(request: Request, date: str, tier: int) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content_json FROM daily_dew WHERE dew_date = %s AND tier = %s",
                (date, tier),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="甘露记录不存在")
            content = row[0] if isinstance(row[0], dict) else {}
        return {"ok": True, "dew_date": date, "tier": tier, "content": content}
    finally:
        _state["release_db"](conn)


@router.delete("/dew/{date}/{tier}")
def admin_delete_dew(request: Request, date: str, tier: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM daily_dew WHERE dew_date = %s AND tier = %s",
                (date, tier),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="甘露记录不存在")
            audit(cur, admin["email"], "dew.delete", "daily_dew",
                  f"{date}:{tier}", {})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 诗歌 R2 只读枚举
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/hymns/r2-files")
def admin_hymns_r2_files(request: Request) -> dict:
    require_admin(request)
    import os
    account_id  = os.environ.get("R2_ACCOUNT_ID", "").strip()
    access_key  = os.environ.get("R2_ACCESS_KEY_ID", "").strip()
    secret_key  = os.environ.get("R2_SECRET_ACCESS_KEY", "").strip()
    bucket_name = os.environ.get("R2_BUCKET_NAME", "").strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        return {"ok": True, "items": [], "readonly": True, "note": "R2 未配置"}
    try:
        import boto3
        client = boto3.client(
            "s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
        )
        paginator = client.get_paginator("list_objects_v2")
        items = []
        for page in paginator.paginate(Bucket=bucket_name, Prefix="hymns/"):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                fname = key[len("hymns/"):]
                if not fname:
                    continue
                items.append({"key": key, "filename": fname, "size": obj.get("Size", 0)})
        return {"ok": True, "items": items, "readonly": True,
                "note": "只读：诗歌文件直接管理 R2 bucket，此处仅列出"}
    except Exception as exc:
        return {"ok": True, "items": [], "readonly": True, "note": f"R2 枚举失败: {exc}"}


# ─────────────────────────────────────────────────────────────────────────────
# 书籍 book_marks 统计（只读）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/books/marks-stats")
def admin_books_marks_stats(request: Request) -> dict:
    require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT book_id,
                       COUNT(*) FILTER (WHERE status = 'want')  AS want_cnt,
                       COUNT(*) FILTER (WHERE status = 'read')  AS read_cnt,
                       ROUND(AVG(rating)::numeric, 1)           AS avg_rating,
                       COUNT(rating)                            AS rating_count
                FROM book_marks
                GROUP BY book_id
                ORDER BY read_cnt DESC
                """
            )
            stats = [
                {
                    "book_id": r[0], "want_cnt": r[1], "read_cnt": r[2],
                    "avg_rating": float(r[3]) if r[3] is not None else None,
                    "rating_count": r[4],
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "stats": stats, "readonly": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 门徒塑造（只读 + end 关系）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/disciple/profiles")
def admin_disciple_profiles(
    request: Request,
    email: str = Query(default=""),
    stage: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []
            if email:
                filters.append("email ILIKE %s")
                params.append(f"%{email}%")
            if stage:
                filters.append("spiritual_state = %s")
                params.append(stage)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM disciple_profiles {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT email, spiritual_state, christlikeness_index,
                       assessment_count, updated_at
                FROM disciple_profiles {where}
                ORDER BY updated_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "email": r[0], "spiritual_state": r[1],
                    "christlikeness_index": float(r[2]) if r[2] else 0.0,
                    "assessment_count": r[3], "updated_at": iso(r[4]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/disciple/assessments")
def admin_disciple_assessments(
    request: Request,
    email: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM disciple_assessments WHERE email = %s", (email,)
            )
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, email, reflection_text, spiritual_state,
                       faith_score, hope_score, love_score, created_at
                FROM disciple_assessments
                WHERE email = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (email, limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1],
                    "reflection_text": (r[2] or "")[:100],
                    "spiritual_state": r[3],
                    "faith_score": float(r[4]) if r[4] else None,
                    "hope_score": float(r[5]) if r[5] else None,
                    "love_score": float(r[6]) if r[6] else None,
                    "created_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/disciple/relationships")
def admin_disciple_relationships(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM disciple_relationships")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, mentor_email, disciple_email, disciple_name,
                       relationship_type, status, started_at, ended_at
                FROM disciple_relationships
                ORDER BY started_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "mentor_email": r[1], "disciple_email": r[2],
                    "disciple_name": r[3], "relationship_type": r[4],
                    "status": r[5], "started_at": iso(r[6]), "ended_at": iso(r[7]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.post("/disciple/relationships/{rel_id}/end")
def admin_end_disciple_relationship(request: Request, rel_id: int) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT mentor_email, disciple_name, status "
                "FROM disciple_relationships WHERE id = %s",
                (rel_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="关系不存在")
            if row[2] == "ENDED":
                raise HTTPException(status_code=400, detail="关系已结束")
            cur.execute(
                "UPDATE disciple_relationships SET status='ENDED', ended_at=CURRENT_DATE "
                "WHERE id = %s",
                (rel_id,),
            )
            audit(cur, admin["email"], "disciple.end_relationship", "disciple_relationship",
                  str(rel_id), {"mentor_email": row[0], "disciple_name": row[1]})
            conn.commit()
        return {"ok": True}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# 牧养只读
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/examen")
def admin_list_examen(
    request: Request,
    email: str = Query(default=""),
    from_date: str = Query(default="", alias="from"),
    to_date: str = Query(default="", alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            filters = []
            params: list = []
            if email:
                filters.append("email = %s")
                params.append(email)
            if from_date:
                filters.append("entry_date >= %s::date")
                params.append(from_date)
            if to_date:
                filters.append("entry_date <= %s::date")
                params.append(to_date)
            where = ("WHERE " + " AND ".join(filters)) if filters else ""
            cur.execute(f"SELECT COUNT(*) FROM examen_entries {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, entry_date, consolation_level, created_at
                FROM examen_entries {where}
                ORDER BY entry_date DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "entry_date": str(r[2]),
                    "consolation_level": r[3], "created_at": iso(r[4]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/examen/{entry_id}")
def admin_get_examen(request: Request, entry_id: str) -> dict:
    admin = require_admin(request)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, entry_date, consolation, desolation,
                       gratitude, confession, tomorrow_step, consolation_level, created_at
                FROM examen_entries WHERE id = %s
                """,
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="省察记录不存在")
            iso = _state["to_shanghai_iso"]
            entry = {
                "id": row[0], "email": row[1], "entry_date": str(row[2]),
                "consolation": row[3], "desolation": row[4],
                "gratitude": row[5], "confession": row[6],
                "tomorrow_step": row[7], "consolation_level": row[8],
                "created_at": iso(row[9]),
            }
            audit(cur, admin["email"], "pastoral.view", "examen_entry",
                  entry_id, {"email": row[1]})
            conn.commit()
        return {"ok": True, "entry": entry}
    finally:
        _state["release_db"](conn)


@router.get("/checkups")
def admin_list_checkups(
    request: Request,
    email: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            where = "WHERE email = %s" if email else ""
            params = [email] if email else []
            cur.execute(f"SELECT COUNT(*) FROM spiritual_checkups {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, index_score, level, summary, created_at
                FROM spiritual_checkups {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "index_score": r[2],
                    "level": r[3], "summary": (r[4] or "")[:100],
                    "created_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/gospel-diagnoses")
def admin_list_gospel_diagnoses(
    request: Request,
    email: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            where = "WHERE email = %s" if email else ""
            params = [email] if email else []
            cur.execute(f"SELECT COUNT(*) FROM gospel_diagnoses {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"""
                SELECT id, email, emotion, idol_type, created_at
                FROM gospel_diagnoses {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params + [limit, offset],
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "emotion": r[2],
                    "idol_type": r[3], "created_at": iso(r[4]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


# ─────────────────────────────────────────────────────────────────────────────
# Agent 运行记录 & 域事件（只读）
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/agent-runs")
def admin_list_agent_runs(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM agent_runs")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, email, agent_name, event_type, status, created_at
                FROM agent_runs
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "email": r[1], "agent_name": r[2],
                    "event_type": r[3], "status": r[4], "created_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)


@router.get("/domain-events")
def admin_list_domain_events(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_admin(request)
    limit, offset = paginate(page, page_size)
    conn = _state["get_db"]()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM domain_events")
            total = cur.fetchone()[0]
            cur.execute(
                """
                SELECT id, aggregate_type, aggregate_id, event_type,
                       processed, created_at
                FROM domain_events
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            )
            iso = _state["to_shanghai_iso"]
            items = [
                {
                    "id": r[0], "aggregate_type": r[1], "aggregate_id": r[2],
                    "event_type": r[3], "processed": r[4], "created_at": iso(r[5]),
                }
                for r in cur.fetchall()
            ]
        return {"ok": True, "items": items, "total": total, "page": page, "page_size": limit}
    finally:
        _state["release_db"](conn)
