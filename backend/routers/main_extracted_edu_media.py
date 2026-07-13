"""Sunday School 视频 + Seekers Class（慕道班）课程端点 — 从 main.py 逐字搬移（路径不变）。

依赖 main.py 的 DB 助手与 _handle_exc，经 init_main_extracted_edu_media() 注入。
"""
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

# ── main.py 注入的依赖（导入期为 None，仅在请求期被调用）──
_get_db = None
_release_db = None
_handle_exc = None


def init_main_extracted_edu_media(*, get_db, release_db, handle_exc) -> None:
    global _get_db, _release_db, _handle_exc
    _get_db = get_db
    _release_db = release_db
    _handle_exc = handle_exc


# ── Sunday School Videos (主日学视频) ────────────────────────────────────────


_VIDEO_BASE_URL  = 'https://cdn.holiness.uk/biblical-films/'
_VIDEO_PREFIX    = 'biblical-films/'
_VIDEO_LISTING_CACHE: dict = {}
_VIDEO_CACHE_TTL = 120


def _list_videos_via_r2_api() -> list:
    account_id  = os.environ.get('R2_ACCOUNT_ID', '').strip()
    access_key  = os.environ.get('R2_ACCESS_KEY_ID', '').strip()
    secret_key  = os.environ.get('R2_SECRET_ACCESS_KEY', '').strip()
    bucket_name = os.environ.get('R2_BUCKET_NAME', '').strip()
    prefix      = os.environ.get('R2_VIDEO_PREFIX', _VIDEO_PREFIX).strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        raise ValueError('R2 env vars not configured')
    import boto3
    client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto',
    )
    VIDEO_EXTS = ('.mp4', '.mov', '.webm', '.m4v')
    paginator = client.get_paginator('list_objects_v2')
    videos = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            fname = obj['Key'].split('/')[-1]
            if not fname or not any(fname.lower().endswith(e) for e in VIDEO_EXTS):
                continue
            ts = obj['LastModified'].timestamp() if obj.get('LastModified') else 0.0
            videos.append({'filename': fname, 'modified_ts': ts, 'url': _VIDEO_BASE_URL + fname})
    return videos


def _parse_html_xml_listing(text: str) -> list:
    import re
    videos = []
    if '<ListBucketResult' in text or '<Key>' in text:
        keys  = re.findall(r'<Key>([^<]+\.(?:mp4|mov|webm|m4v))</Key>', text, re.IGNORECASE)
        dates = re.findall(r'<LastModified>([^<]+)</LastModified>', text)
        for i, key in enumerate(keys):
            fname = key.split('/')[-1]
            ts = 0.0
            if i < len(dates):
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(dates[i].replace('Z', '+00:00')).timestamp()
                except Exception:
                    pass
            videos.append({'filename': fname, 'modified_ts': ts, 'url': _VIDEO_BASE_URL + fname})
        if videos:
            return videos
    for href in re.findall(r'href=["\']([^"\'?#]+\.(?:mp4|mov|webm|m4v))', text, re.IGNORECASE):
        fname = href.split('/')[-1]
        videos.append({'filename': fname, 'modified_ts': 0.0, 'url': _VIDEO_BASE_URL + fname})
    return videos


@router.get('/api/sunday-school/videos')
async def list_sunday_school_videos(request: Request, debug: bool = False) -> dict:
    """List sunday school videos from database table sunday_school_videos.
    Add ?debug=1 to bypass cache."""
    import time
    now = time.time()

    if not debug and _VIDEO_LISTING_CACHE.get('ts', 0) + _VIDEO_CACHE_TTL > now:
        return {'ok': True, 'videos': _VIDEO_LISTING_CACHE['videos'], 'cached': True}

    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, alias, teacher, scripture, description,
                       video_url, thumbnail_url, duration_sec, sort_order, created_at
                FROM sunday_school_videos
                WHERE is_visible = TRUE
                ORDER BY sort_order ASC, created_at DESC
                """
            )
            rows = cur.fetchall()

        videos = [
            {
                'id':            r[0],
                'title':         r[1] or '',
                'alias':         r[2] or '',
                'display_title': r[2] or r[1] or '',  # 优先使用 alias
                'teacher':       r[3] or '',
                'scripture':     r[4] or '',
                'description':   r[5] or '',
                'video_url':     r[6] or '',
                'thumbnail_url': r[7] or '',
                'duration_sec':  r[8] or 0,
                'sort_order':    r[9] or 0,
                'created_at':    r[10].isoformat() if r[10] else None,
            }
            for r in rows
        ]

        print(f'[sunday-school] DB query ok — {len(videos)} videos', flush=True)
    finally:
        _release_db(conn)

    if not debug:
        _VIDEO_LISTING_CACHE['ts'] = now
        _VIDEO_LISTING_CACHE['videos'] = videos

    result: dict = {'ok': True, 'videos': videos, 'method': 'database', 'cached': False}
    return result


class SundaySchoolVideoPayload(BaseModel):
    title:         str  = Field(default='', max_length=255)
    alias:         str  = Field(default='', max_length=255)
    teacher:       str  = Field(default='', max_length=100)
    scripture:     str  = Field(default='')
    description:   str  = Field(default='')
    video_url:     str  = Field(..., min_length=1)
    thumbnail_url: str  = Field(default='')
    duration_sec:  int  = Field(default=0, ge=0)
    sort_order:    int  = Field(default=0)


@router.post('/api/sunday-school/videos')
def add_sunday_school_video(payload: SundaySchoolVideoPayload, request: Request) -> dict:
    """Admin-only: insert a new video record. Requires X-Admin-Token header."""
    admin_token = request.headers.get('X-Admin-Token', '')
    expected = os.environ.get('ADMIN_TOKEN', '')
    if not expected or admin_token != expected:
        raise HTTPException(status_code=403, detail='Admin token required')
    conn = _get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO sunday_school_videos
                    (title, alias, teacher, scripture, description, video_url, thumbnail_url, duration_sec, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                payload.title.strip(),
                payload.alias.strip(),
                payload.teacher.strip(),
                payload.scripture.strip(),
                payload.description.strip(),
                payload.video_url.strip(),
                payload.thumbnail_url.strip(),
                payload.duration_sec,
                payload.sort_order,
            ))
            new_id = cur.fetchone()[0]
            conn.commit()
        return {'ok': True, 'id': new_id}
    except Exception as exc:
        _handle_exc(exc)
        raise HTTPException(status_code=500, detail='Failed to insert video')
    finally:
        _release_db(conn)



# ── Seekers Class Courses (慕道班课程 — 文字/PPT/视频) ───────────────────────────

_SEEKERS_BASE_URL = 'https://cdn.holiness.uk/seekers-class/'
_SEEKERS_PREFIX   = 'seekers-class/'
# 慕道班固定课程顺序（按文件名关键字匹配；未匹配的排在最后按文件名排序）
_SEEKERS_ORDER = ['认识圣经', '认识创造', '认识罪', '认识耶稣', '认识洗礼']
_SEEKERS_CACHE: dict = {}
_SEEKERS_CACHE_TTL = 120

# extension -> media_type
_SEEKERS_MEDIA_MAP = {
    '.mp4': 'video', '.mov': 'video', '.webm': 'video', '.m4v': 'video',
    '.ppt': 'ppt', '.pptx': 'ppt', '.key': 'ppt',
    '.pdf': 'ppt',
    '.txt': 'text', '.md': 'text', '.doc': 'text', '.docx': 'text',
}


def _seekers_media_type(fname: str) -> str:
    low = fname.lower()
    for ext, mt in _SEEKERS_MEDIA_MAP.items():
        if low.endswith(ext):
            return mt
    return ''


def _list_seekers_via_r2_api() -> list:
    account_id  = os.environ.get('R2_ACCOUNT_ID', '').strip()
    access_key  = os.environ.get('R2_ACCESS_KEY_ID', '').strip()
    secret_key  = os.environ.get('R2_SECRET_ACCESS_KEY', '').strip()
    bucket_name = os.environ.get('R2_BUCKET_NAME', '').strip()
    prefix      = os.environ.get('R2_SEEKERS_PREFIX', _SEEKERS_PREFIX).strip()
    if not all([account_id, access_key, secret_key, bucket_name]):
        raise ValueError('R2 env vars not configured')
    import boto3
    client = boto3.client(
        's3',
        endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='auto',
    )
    paginator = client.get_paginator('list_objects_v2')
    files = []
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get('Contents', []):
            fname = obj['Key'].split('/')[-1]
            if not fname:
                continue
            mt = _seekers_media_type(fname)
            if not mt:
                continue
            ts = obj['LastModified'].timestamp() if obj.get('LastModified') else 0.0
            files.append({'filename': fname, 'media_type': mt, 'modified_ts': ts,
                          'url': _SEEKERS_BASE_URL + fname})
    return files


@router.get('/api/seekers-class/courses')
async def list_seekers_class_courses(request: Request, debug: bool = False) -> dict:
    """List 慕道班 course resources (text / ppt / video) from R2.
    Mirrors the Sunday-school listing: R2 API primary, HTTP listing fallback.
    Each item carries a media_type so the client renders the right card."""
    import time, httpx
    now = time.time()

    if not debug and _SEEKERS_CACHE.get('ts', 0) + _SEEKERS_CACHE_TTL > now:
        return {'ok': True, 'courses': _SEEKERS_CACHE['courses'], 'cached': True}

    raw: list = []
    method_used = 'none'
    debug_info: dict = {}

    try:
        raw = _list_seekers_via_r2_api()
        method_used = 'r2_api'
        print(f'[seekers-class] R2 API ok — {len(raw)} files', flush=True)
    except ValueError as e:
        debug_info['r2_skip'] = str(e)
    except Exception as e:
        debug_info['r2_error'] = str(e)
        print(f'[seekers-class] R2 error: {e}', flush=True)

    if not raw:
        try:
            async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
                resp = await client.get(_SEEKERS_BASE_URL)
            debug_info['http_status'] = resp.status_code
            debug_info['http_preview'] = resp.text[:500]
            if resp.status_code == 200:
                import re
                for key in re.findall(r'<Key>([^<]+)</Key>', resp.text):
                    fname = key.split('/')[-1]
                    mt = _seekers_media_type(fname)
                    if mt:
                        raw.append({'filename': fname, 'media_type': mt,
                                    'modified_ts': 0.0, 'url': _SEEKERS_BASE_URL + fname})
                if not raw:
                    for href in re.findall(r'href=["\']([^"\'?#]+)', resp.text):
                        fname = href.split('/')[-1]
                        mt = _seekers_media_type(fname)
                        if mt:
                            raw.append({'filename': fname, 'media_type': mt,
                                        'modified_ts': 0.0, 'url': _SEEKERS_BASE_URL + fname})
                method_used = 'http_listing'
                print(f'[seekers-class] HTTP listing — {len(raw)} files', flush=True)
        except Exception as e:
            debug_info['http_error'] = str(e)
            print(f'[seekers-class] HTTP error: {e}', flush=True)

    def _seekers_sort_key(v):
        for idx, kw in enumerate(_SEEKERS_ORDER):
            if kw in v['filename']:
                return (idx, v['filename'])
        return (len(_SEEKERS_ORDER), v['filename'])
    raw.sort(key=_seekers_sort_key)
    courses = [
        {
            'id':          i + 1,
            'title':       v['filename'].rsplit('.', 1)[0].replace('-', ' ').replace('_', ' '),
            'filename':    v['filename'],
            'media_type':  v['media_type'],
            'url':         v['url'],
            'modified_ts': v['modified_ts'],
        }
        for i, v in enumerate(raw)
    ]

    if not debug:
        _SEEKERS_CACHE['ts'] = now
        _SEEKERS_CACHE['courses'] = courses

    result: dict = {'ok': True, 'courses': courses, 'method': method_used, 'cached': False}
    if debug:
        result['debug'] = debug_info
    return result


@router.get('/api/v1/courses')
async def list_courses_compat(
    request: Request,
    page: int = 1,
    per_page: int = 20,
) -> dict:
    """Backward-compatible public course catalogue for older web clients."""
    page = max(1, page)
    per_page = min(100, max(1, per_page))
    result = await list_seekers_class_courses(request)
    courses = result.get('courses', [])
    start = (page - 1) * per_page
    items = courses[start:start + per_page]
    return {
        'ok': True,
        'items': items,
        'courses': items,
        'total': len(courses),
        'page': page,
        'per_page': per_page,
        'cached': result.get('cached', False),
    }
