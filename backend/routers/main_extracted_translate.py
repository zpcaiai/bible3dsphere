"""按需翻译 /api/translate-batch（含 _translate_cached 缓存翻译）— 从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助（_get_db、_release_db、call_chat、DATABASE_URL）通过
init_main_extracted_translate() 在 include_router 之前注入。
limiter 与 main.py 一样直接取自 core.ratelimit（同一实例，装饰期即需要）。
"""
from typing import List

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from core.ratelimit import limiter

router = APIRouter()

# ── main.py 注入的依赖（导入期为占位值，仅在请求期被使用）──
_get_db = None
_release_db = None
call_chat = None
DATABASE_URL = ''


def init_main_extracted_translate(*, get_db, release_db, call_chat_fn, database_url) -> None:
    global _get_db, _release_db, call_chat, DATABASE_URL
    _get_db = get_db
    _release_db = release_db
    call_chat = call_chat_fn
    DATABASE_URL = database_url


def _translate_cached(text: str, target: str) -> str:
    """翻译单条文本，命中/写入 translations_cache。失败返回 ''。"""
    import hashlib
    text = str(text or '').strip()
    if target not in ('en', 'zh'):
        target = 'en'
    if not text:
        return ''
    if len(text) > 4000:
        text = text[:4000]
    h = hashlib.sha1(f'{text}|{target}'.encode('utf-8')).hexdigest()
    if DATABASE_URL:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute('SELECT translated FROM translations_cache WHERE hash=%s', (h,))
                row = cur.fetchone()
                if row:
                    return row[0]
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)
    if target == 'en':
        sys_prompt = ('You are a translator for a Chinese Christian app. Translate the user text to '
                      'natural, reverent English using standard English Bible proper nouns. '
                      'Output ONLY the translation.')
    else:
        sys_prompt = ('你是中文基督教应用的翻译。把用户文本翻成自然、敬虔的简体中文，'
                      '圣经专名用通用中文译名。只输出译文。')
    try:
        out = call_chat(sys_prompt, text).strip().strip('"').strip()
    except Exception:
        out = ''
    if not out:
        return ''
    if DATABASE_URL:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO translations_cache(hash,target,translated) VALUES(%s,%s,%s) '
                    'ON CONFLICT (hash) DO NOTHING', (h, target, out))
                conn.commit()
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)
    return out




class TranslateBatchRequest(BaseModel):
    # Bounded list length to prevent cost/memory amplification via oversized batches.
    texts: List[str] = Field(default_factory=list, max_length=100)
    target: str = ''
    target_lang: str = ''


@router.post('/api/translate-batch')
@limiter.limit('60/minute')
def translate_batch(payload: TranslateBatchRequest, request: Request, response: Response) -> dict:
    """批量按需翻译（EN 模式自动翻译列表）。
    { texts:[...], target|target_lang } → { ok, translations:[...] }
    （与输入等长，失败项回退原文）。

    性能优化：把原来"逐条串行(每条一次 DB 往返 + 一次 LLM 往返)"改为
      ① 一次性批量查缓存（单次 SQL，命中即返回）
      ② 仅对未命中文本去重后并发机翻（线程池，I/O 并行）
      ③ 一次性批量写回缓存（单条 INSERT）
    整屏翻译延迟从"逐条累加(~2s+)"降到约"单次 LLM 往返(~0.7s)"。"""
    import hashlib
    from concurrent.futures import ThreadPoolExecutor

    p = payload.model_dump() if hasattr(payload, 'model_dump') else (payload or {})
    texts = p.get('texts')
    if not isinstance(texts, list):
        texts = []
    target = str(p.get('target') or p.get('target_lang') or 'en').lower()
    if target not in ('en', 'zh'):
        target = 'en'
    texts = [str(t or '')[:2000] for t in texts][:100]  # 限长，防成本/内存放大
    response.headers['Cache-Control'] = 'private, max-age=86400'

    stripped = [t.strip() for t in texts]

    def _h(src: str) -> str:
        return hashlib.sha1(f'{src}|{target}'.encode('utf-8')).hexdigest()

    hashes = [(_h(s) if s else None) for s in stripped]
    result_map: dict = {}  # hash -> translated

    # ① 一次性批量查缓存
    uniq_hashes = list({h for h in hashes if h})
    if DATABASE_URL and uniq_hashes:
        conn = None
        try:
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT hash, translated FROM translations_cache WHERE hash IN %s',
                    (tuple(uniq_hashes),))
                for hh, tr in cur.fetchall():
                    result_map[hh] = tr
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)

    if target == 'en':
        sys_prompt = ('You are a translator for a Chinese Christian app. Translate the user text to '
                      'natural, reverent English using standard English Bible proper nouns. '
                      'Output ONLY the translation.')
    else:
        sys_prompt = ('你是中文基督教应用的翻译。把用户文本翻成自然、敬虔的简体中文，'
                      '圣经专名用通用中文译名。只输出译文。')

    # ② 未命中文本去重（dict 天然去重，相同文本只翻一次）后并发机翻
    misses: dict = {}
    for s, h in zip(stripped, hashes):
        if h and h not in result_map and h not in misses:
            misses[h] = s

    def _one(item):
        hh, src = item
        try:
            out_txt = call_chat(sys_prompt, src).strip().strip('"').strip()
        except Exception:
            out_txt = ''
        return hh, out_txt

    if misses:
        workers = min(8, len(misses))
        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                for hh, out_txt in ex.map(_one, list(misses.items())):
                    if out_txt:
                        result_map[hh] = out_txt
        except Exception:
            pass

    # ③ 一次性批量写回缓存
    new_rows = [(h, target, result_map[h]) for h in misses if result_map.get(h)]
    if DATABASE_URL and new_rows:
        conn = None
        try:
            from psycopg2.extras import execute_values
            conn = _get_db()
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    'INSERT INTO translations_cache(hash,target,translated) VALUES %s '
                    'ON CONFLICT (hash) DO NOTHING',
                    new_rows)
                conn.commit()
        except Exception:
            pass
        finally:
            if conn is not None:
                _release_db(conn)

    # ④ 按原顺序产出，空串/失败回退原文
    out = []
    for orig, s, h in zip(texts, stripped, hashes):
        out.append(orig if not s else (result_map.get(h) or orig))
    return {'ok': True, 'translations': out, 'target_lang': target}

