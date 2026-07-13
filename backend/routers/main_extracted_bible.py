"""经文查阅 /api/scripture、查经 /api/bible/study、圣经视频 /api/bible/video —
从 main.py 逐字搬移（路径不变，无 prefix）。

对 main.py 内部辅助（ROOT_DIR、GOOGLE_TTS_API_KEY、_handle_exc）通过
init_main_extracted_bible() 在 include_router 之前注入，本模块与 main 无 import 期耦合。
"""
import json
from typing import List

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

router = APIRouter()

# ── main.py 注入的依赖（导入期为占位值，仅在请求期被使用）──
ROOT_DIR = None            # Path：数据文件根目录
GOOGLE_TTS_API_KEY = ''    # 视频 TTS 配音可选 key
_handle_exc = None         # 统一异常打印


def init_main_extracted_bible(*, root_dir, google_tts_api_key, handle_exc) -> None:
    global ROOT_DIR, GOOGLE_TTS_API_KEY, _handle_exc
    ROOT_DIR = root_dir
    GOOGLE_TTS_API_KEY = google_tts_api_key
    _handle_exc = handle_exc


# ─────────────────────────────────────────────────────────────────────────────
# 经文查阅 API  /api/scripture
# 解析中文经文引用（如"诗篇第一百一十五篇"、"哥林多后书五章1至10节"）
# 返回对应和合本经文正文
# ─────────────────────────────────────────────────────────────────────────────
import re as _re
import csv as _csv
from functools import lru_cache as _lru_cache
from pathlib import Path as _Path

# ── 书卷名映射（中文 → 和合本标准名，处理常见别名）────────────────────────────
_BOOK_ZH_CANON = {
    '创世记': '创世记', '创': '创世记',
    '出埃及记': '出埃及记', '出': '出埃及记',
    '利未记': '利未记', '利': '利未记',
    '民数记': '民数记', '民': '民数记',
    '申命记': '申命记', '申': '申命记',
    '约书亚记': '约书亚记', '书': '约书亚记',
    '士师记': '士师记', '士': '士师记',
    '路得记': '路得记', '得': '路得记',
    '撒母耳记上': '撒母耳记上', '撒上': '撒母耳记上',
    '撒母耳记下': '撒母耳记下', '撒下': '撒母耳记下',
    '列王纪上': '列王纪上', '王上': '列王纪上',
    '列王纪下': '列王纪下', '王下': '列王纪下',
    '历代志上': '历代志上', '代上': '历代志上',
    '历代志下': '历代志下', '代下': '历代志下',
    '以斯拉记': '以斯拉记', '拉': '以斯拉记',
    '尼希米记': '尼希米记', '尼': '尼希米记',
    '以斯帖记': '以斯帖记', '斯': '以斯帖记',
    '约伯记': '约伯记', '伯': '约伯记',
    '诗篇': '诗篇', '诗': '诗篇',
    '箴言': '箴言', '箴': '箴言',
    '传道书': '传道书', '传': '传道书',
    '雅歌': '雅歌', '歌': '雅歌',
    '以赛亚书': '以赛亚书', '赛': '以赛亚书',
    '耶利米书': '耶利米书', '耶': '耶利米书',
    '耶利米哀歌': '耶利米哀歌', '哀': '耶利米哀歌',
    '以西结书': '以西结书', '结': '以西结书',
    '但以理书': '但以理书', '但': '但以理书',
    '何西阿书': '何西阿书', '何': '何西阿书',
    '约珥书': '约珥书', '珥': '约珥书',
    '阿摩司书': '阿摩司书', '摩': '阿摩司书',
    '俄巴底亚书': '俄巴底亚书', '俄': '俄巴底亚书',
    '约拿书': '约拿书', '拿': '约拿书',
    '弥迦书': '弥迦书', '弥': '弥迦书',
    '那鸿书': '那鸿书', '鸿': '那鸿书',
    '哈巴谷书': '哈巴谷书', '哈': '哈巴谷书',
    '西番雅书': '西番雅书', '番': '西番雅书',
    '哈该书': '哈该书', '该': '哈该书',
    '撒迦利亚书': '撒迦利亚书', '亚': '撒迦利亚书',
    '玛拉基书': '玛拉基书', '玛': '玛拉基书',
    '马太福音': '马太福音', '太': '马太福音',
    '马可福音': '马可福音', '可': '马可福音',
    '路加福音': '路加福音', '路': '路加福音',
    '约翰福音': '约翰福音', '约': '约翰福音',
    '使徒行传': '使徒行传', '徒': '使徒行传',
    '罗马书': '罗马书', '罗': '罗马书',
    '哥林多前书': '哥林多前书', '林前': '哥林多前书',
    '哥林多后书': '哥林多后书', '林后': '哥林多后书',
    '加拉太书': '加拉太书', '加': '加拉太书',
    '以弗所书': '以弗所书', '弗': '以弗所书',
    '腓立比书': '腓立比书', '腓': '腓立比书',
    '歌罗西书': '歌罗西书', '西': '歌罗西书',
    '帖撒罗尼迦前书': '帖撒罗尼迦前书', '帖前': '帖撒罗尼迦前书',
    '帖撒罗尼迦后书': '帖撒罗尼迦后书', '帖后': '帖撒罗尼迦后书',
    '提摩太前书': '提摩太前书', '提前': '提摩太前书',
    '提摩太后书': '提摩太后书', '提后': '提摩太后书',
    '提多书': '提多书', '多': '提多书',
    '腓利门书': '腓利门书', '门': '腓利门书',
    '希伯来书': '希伯来书', '来': '希伯来书',
    '雅各书': '雅各书', '雅': '雅各书',
    '彼得前书': '彼得前书', '彼前': '彼得前书',
    '彼得后书': '彼得后书', '彼后': '彼得后书',
    '约翰一书': '约翰一书', '约壹': '约翰一书',
    '约翰二书': '约翰二书', '约贰': '约翰二书',
    '约翰三书': '约翰三书', '约叁': '约翰三书',
    '犹大书': '犹大书', '犹': '犹大书',
    '启示录': '启示录', '启': '启示录',
}

# ── 中文数字 → 阿拉伯数字 ───────────────────────────────────────────────────
_CN_DIGIT = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
             '六': 6, '七': 7, '八': 8, '九': 9}
_CN_UNIT  = {'十': 10, '百': 100, '千': 1000}

def _cn2int(s: str) -> int | None:
    """Convert a Chinese number string like '一百一十五' → 115."""
    s = s.strip()
    if not s:
        return None
    if s.lstrip('-').isdigit():
        return int(s)
    # Handle plain Arabic digits mixed in
    result = 0
    tmp = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c in _CN_DIGIT:
            tmp = _CN_DIGIT[c]
            i += 1
        elif c in _CN_UNIT:
            unit = _CN_UNIT[c]
            if tmp == 0 and unit == 10:
                tmp = 1  # 十五 → 15
            result += tmp * unit
            tmp = 0
            i += 1
        elif c.isdigit():
            # Arabic digit
            num_s = ''
            while i < len(s) and s[i].isdigit():
                num_s += s[i]
                i += 1
            tmp = int(num_s)
        else:
            i += 1
    result += tmp
    return result if result > 0 else None


def _parse_scripture_ref(ref: str) -> tuple[str | None, int | None, int | None, int | None]:
    """
    Parse a Chinese scripture reference into (book, chapter, verse_start, verse_end).
    Examples:
      '诗篇第一百一十五篇'        → ('诗篇', 115, None, None)
      '哥林多后书五章 1至10节'    → ('哥林多后书', 5, 1, 10)
      '路加福音十二章13至21节'    → ('路加福音', 12, 13, 21)
      '以赛亚书40:12-31'          → ('以赛亚书', 40, 12, 31)
    """
    ref = ref.strip()

    # ── book name: try longest match first ──────────────────────────────────
    book = None
    rest = ref
    # Sort by length descending so "哥林多后书" matches before "哥林多"
    for name in sorted(_BOOK_ZH_CANON.keys(), key=len, reverse=True):
        canon = _BOOK_ZH_CANON[name]
        if ref.startswith(name):
            book = canon
            rest = ref[len(name):]
            break

    if book is None:
        return None, None, None, None

    # ── Strip leading 第/卷 ──────────────────────────────────────────────────
    rest = _re.sub(r'^[第卷]\s*', '', rest)

    # ── Arabic colon notation: 40:12-31 ────────────────────────────────────
    m = _re.match(r'^(\d+)[：:章]\s*(\d+)\s*[-–至到]\s*(\d+)', rest)
    if m:
        return book, int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = _re.match(r'^(\d+)[：:章]\s*(\d+)', rest)
    if m:
        return book, int(m.group(1)), int(m.group(2)), int(m.group(2))

    # ── Chapter in Chinese nums ─────────────────────────────────────────────
    m = _re.match(r'^([零一二三四五六七八九十百千\d]+)[篇章卷]', rest)
    chapter = None
    if m:
        chapter = _cn2int(m.group(1))
        rest = rest[m.end():]
    elif _re.match(r'^(\d+)', rest):
        m2 = _re.match(r'^(\d+)', rest)
        chapter = int(m2.group(1))
        rest = rest[m2.end():]

    if chapter is None:
        return book, None, None, None

    # ── Clean up spaces ──────────────────────────────────────────────────────
    rest = rest.strip()
    if not rest or rest in ('篇', '章', '卷', ''):
        return book, chapter, None, None

    # ── Verse range: Arabic ──────────────────────────────────────────────────
    m = _re.match(r'(\d+)\s*[-–至到]\s*(\d+)', rest)
    if m:
        return book, chapter, int(m.group(1)), int(m.group(2))

    # ── Chinese verse range ──────────────────────────────────────────────────
    m = _re.match(r'([零一二三四五六七八九十百千\d]+)[至到节]?\s*[-–至到]\s*([零一二三四五六七八九十百千\d]+)', rest)
    if m:
        return book, chapter, _cn2int(m.group(1)), _cn2int(m.group(2))

    # ── Single verse ────────────────────────────────────────────────────────
    m = _re.match(r'(\d+)', rest)
    if m:
        v = int(m.group(1))
        return book, chapter, v, v

    return book, chapter, None, None


@_lru_cache(maxsize=1)
def _load_cuv_index() -> dict:
    """Load cuv_bible.csv into {(book, chapter, verse) → text} once."""
    idx: dict[tuple, str] = {}
    path = ROOT_DIR / 'bible' / 'cuv_bible.csv'
    if not path.exists():
        return idx
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                key = (row['book'].strip(), int(row['chapter']), int(row['verse']))
                idx[key] = row['text'].strip().replace(' ', '')  # strip CUV spaces
            except (ValueError, KeyError):
                pass
    return idx


@_lru_cache(maxsize=1)
def _load_booknum_to_zh() -> dict:
    """book number(int) -> canonical Chinese book name, from cuv_bible.csv."""
    m: dict = {}
    path = ROOT_DIR / 'bible' / 'cuv_bible.csv'
    if not path.exists():
        return m
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                m[int(row['book number'])] = row['book'].strip()
            except (ValueError, KeyError):
                pass
    return m


@_lru_cache(maxsize=1)
def _load_esv_index() -> dict:
    """Load esv_bible.csv into {(book_zh, chapter, verse) -> english text}.
    Keyed by the canonical Chinese book name (via shared 'book number') so it
    drops into get_scripture's existing lookup loop unchanged."""
    idx: dict = {}
    path = ROOT_DIR / 'bible' / 'esv_bible.csv'
    if not path.exists():
        return idx
    num2zh = _load_booknum_to_zh()
    with open(path, 'r', encoding='utf-8') as f:
        for row in _csv.DictReader(f):
            try:
                book_zh = num2zh.get(int(row['book number']))
                if not book_zh:
                    continue
                key = (book_zh, int(row['chapter']), int(row['verse']))
                idx[key] = row['text'].strip()
            except (ValueError, KeyError):
                pass
    return idx


@_lru_cache(maxsize=1)
def _load_zh_to_en_book() -> dict:
    """canonical Chinese book name -> English book name (from esv_bible.csv)."""
    num2zh = _load_booknum_to_zh()
    num2en: dict = {}
    path = ROOT_DIR / 'bible' / 'esv_bible.csv'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            for row in _csv.DictReader(f):
                try:
                    num2en[int(row['book number'])] = row['book'].strip()
                except (ValueError, KeyError):
                    pass
    return {zh: num2en[n] for n, zh in num2zh.items() if n in num2en}


def _zh_to_en_book(zh: str):
    return _load_zh_to_en_book().get(zh)


@router.get('/api/scripture')
def get_scripture(ref: str, request: Request, max_verses: int = 200):
    """
    Parse a Chinese scripture reference and return the verse text.
    Query param: ref=<reference string>  e.g. ref=诗篇第一百一十五篇
    """
    ref = ref.strip()
    if not ref:
        raise HTTPException(status_code=400, detail='ref is required')

    book, chapter, v_start, v_end = _parse_scripture_ref(ref)

    if book is None:
        return {'ok': False, 'ref': ref, 'error': '无法识别书卷名', 'verses': []}

    _en = (request.headers.get('X-Lang') or 'zh').lower().startswith('en')
    idx = _load_esv_index() if _en else _load_cuv_index()

    # Determine verse range
    verses_out = []
    if chapter is None:
        # Shouldn't happen, but return nothing
        return {'ok': False, 'ref': ref, 'error': '无法识别章节', 'verses': []}

    if v_start is None:
        # Whole chapter
        v = 1
        while v <= max_verses:
            key = (book, chapter, v)
            if key in idx:
                verses_out.append({'verse': v, 'text': idx[key]})
                v += 1
            else:
                break
    else:
        end = v_end if v_end else v_start
        end = min(end, v_start + max_verses - 1)
        for v in range(v_start, end + 1):
            key = (book, chapter, v)
            if key in idx:
                verses_out.append({'verse': v, 'text': idx[key]})

    return {
        'ok': True,
        'version': 'esv' if _en else 'cuv',
        'ref': ref,
        'book': book,
        'chapter': chapter,
        'verse_start': v_start,
        'verse_end': v_end,
        'verses': verses_out,
    }

# ── Bible Study (查经) ──────────────────────────────────────────────────────

class BibleStudyVerseItem(BaseModel):
    verse: int
    text: str = Field(max_length=300)

class BibleStudyRequest(BaseModel):
    book: str = Field(min_length=1, max_length=30)
    chapter: int = Field(ge=1, le=200)
    verses: list[BibleStudyVerseItem] = Field(max_length=200)

# In-memory cache for generated Bible studies (book, chapter) → study dict
_bible_study_cache: dict[tuple, dict] = {}

@router.post('/api/bible/study')
def generate_bible_study(payload: BibleStudyRequest, request: Request) -> dict:
    """Generate a rich 10-section Bible study for a chapter using LLM; results are cached in-memory."""
    _en = (request.headers.get('X-Lang') or 'zh').lower().startswith('en')
    _lang = 'en' if _en else 'zh'
    cache_key = (payload.book, payload.chapter, _lang)
    if cache_key in _bible_study_cache:
        print(f'[bible-study] cache hit {payload.book} {payload.chapter}', flush=True)
        return {'ok': True, 'study': _bible_study_cache[cache_key], 'cached': True}

    verses_text = '\n'.join(f'{v.verse}\u3000{v.text}' for v in payload.verses)
    ref = f'{payload.book}第{payload.chapter}章'
    print(f'[bible-study] generating ref={ref} verses={len(payload.verses)}', flush=True)

    system_prompt = (
        '你是一位精通圣经原文（希伯来文/希腊文）、系统神学、教会历史和牧者关怀的圣经教师，' 
        '同时擅长中国文化处境化解经。请根据提供的经文，生成一份极为详尽、可供小组查经和个人灵修使用的中文查经材料。\n'
        '严格以合法JSON对象格式返回，不要加Markdown代码块标记。\n'
        '返回格式（所有字段均为中文字符串，除verse_by_verse为数组）:\n'
        '{\n'
        '  "overview": "章节概览：本章主题、结构轮廓、在整卷书/整本圣经中的位置与承上启下作用（200-300字）",\n'
        '  "context": "历史文化背景：作者、写作时代、地理环境、当时的政治宗教文化背景、写作目的；兼顾中国读者的文化联结（250-350字）",\n'
        '  "structure": "段落结构分析：将本章分为3-5个自然段，每段给出小标题和1-2句核心内容，体现章节的叙事/论证逻辑（150-250字）",\n'
        '  "verse_by_verse": [\n'
        '    // 对每一节经文单独详解，格式如下，共N项（N=经文总节数）:\n'
        '    {\n'
        '      "verse": 1,\n'
        '      "comment": "对本节经文的详细解经（120-200字）：解释字词、语法与修辞，说明作者意图，回应可能的疑问",\n'
        '      "word": "本节最重要的一个关键词（希伯来文或希腊文音译+原义）及其神学意涵（50-100字）",\n'
        '      "apply": "本节对当代信徒最直接的一句应用提示（30-60字，以"你/我们"开头）"\n'
        '    }\n'
        '  ],\n'
        '  "key_words": "本章3-5个最重要的神学词语：每词附原文音译、字义、在圣经中的神学发展脉络及本章用法（250-350字）",\n'
        '  "cross_refs": "串珠平行经文：列出5-7处重要相关经文（含新旧约），每处附一句说明其与本章的关联（250-350字）",\n'
        '  "theology": "核心神学主题：提炼本章2-3个核心神学命题，每个命题展开论述其圣经神学与系统神学意义（250-350字）",\n'
        '  "echoes": "历史印证：举2-4个具体史实——早期教父、宗教改革家、宣教士、中国教会历史人物——如何活出或应用本章真理（250-350字）",\n'
        '  "application": "时代应用：分四个维度——个人灵命、家庭婚姻、教会团契、社会职场——各写一段具体的榜样、教训或劝勉（300-400字）",\n'
        '  "practice": "操练建议：5条具体可操作的日常灵命操练，每条含做法、频率与预期生命改变（250-350字）",\n'
        '  "prayer": "祷告引导：一篇150-200字的祷告文，基于本章真理，使用第一人称复数（我们），涵盖认罪、感恩、祈求、委身四个层次"\n'
        '}'
    )

    if _en:
        book_en = _zh_to_en_book(payload.book) or payload.book
        ref = f'{book_en} {payload.chapter}'
        system_prompt = (
            'You are a Bible teacher fluent in the original languages (Hebrew/Greek), systematic theology, church history, and pastoral care. '
            'Based on the provided passage, produce a thorough English Bible-study resource suitable for small-group study and personal devotion.\n'
            'Return ONLY a valid JSON object, with no Markdown code fences.\n'
            'Format (all fields are English strings except verse_by_verse which is an array):\n'
            '{\n'
            '  "overview": "Chapter overview: theme, structural outline, and its place and role within the book and the whole Bible (200-300 words)",\n'
            '  "context": "Historical and cultural background: author, era, geography, political/religious/cultural setting, and purpose of writing (250-350 words)",\n'
            '  "structure": "Paragraph structure: divide the chapter into 3-5 natural sections, each with a heading and 1-2 sentences of core content (150-250 words)",\n'
            '  "verse_by_verse": [\n'
            '    {\n'
            '      "verse": 1,\n'
            '      "comment": "Detailed exegesis of this verse (120-200 words): words, grammar, rhetoric, the intent of the author, and likely questions",\n'
            '      "word": "The single most important key word of this verse (Hebrew or Greek transliteration plus meaning) and its theological significance (50-100 words)",\n'
            '      "apply": "One direct application of this verse for believers today (30-60 words, beginning with You or We)"\n'
            '    }\n'
            '  ],\n'
            '  "key_words": "3-5 most important theological terms of the chapter: each with original-language transliteration, meaning, biblical-theological development, and its use here (250-350 words)",\n'
            '  "cross_refs": "Cross references: 5-7 important related passages (Old and New Testament), each with one sentence on its connection to this chapter (250-350 words)",\n'
            '  "theology": "Core theological themes: 2-3 central propositions, each developed in its biblical and systematic-theological significance (250-350 words)",\n'
            '  "echoes": "Historical witness: 2-4 concrete examples (early church fathers, Reformers, missionaries, notable believers) who lived out or applied the truth of this chapter (250-350 words)",\n'
            '  "application": "Application for today across four dimensions - personal walk, family and marriage, church and fellowship, society and workplace - each a concrete paragraph of example, lesson, or exhortation (300-400 words)",\n'
            '  "practice": "5 concrete, actionable daily spiritual practices, each with method, frequency, and expected transformation (250-350 words)",\n'
            '  "prayer": "A 150-200 word prayer based on the truth of this chapter, in first-person plural (we), covering confession, thanksgiving, petition, and commitment"\n'
            '}'
        )
        user_message = f'Passage: {ref} ({len(payload.verses)} verses)\n\n{verses_text}'
    else:
        user_message = f'经文章节：{ref}（共{len(payload.verses)}节）\n\n{verses_text}'

    try:
        from query_emotion_verses import _call_llm_with_fallback, _strip_markdown_json
        raw = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=6000,
            temperature=0.68,
            tag='bible-study',
        )
        clean = _strip_markdown_json(raw)
        study = json.loads(clean)
    except json.JSONDecodeError:
        study = {'overview': raw, 'parse_error': True}
    except Exception as exc:
        _handle_exc(exc)
        raise HTTPException(status_code=503, detail=('Bible study generation failed; LLM temporarily unavailable' if _en else '查经生成失败，LLM暂不可用'))

    _bible_study_cache[cache_key] = study
    print(f'[bible-study] ok ref={ref} sections={list(study.keys())}', flush=True)
    return {'ok': True, 'study': study}


# ── Bible Video Generation ─────────────────────────────────────────────────────

class VideoVerseItem(BaseModel):
    verse: int
    text: str = Field(..., max_length=500)

class VideoRequest(BaseModel):
    book:    str = Field(..., min_length=1, max_length=30)
    chapter: int = Field(..., ge=0, le=150)
    verses:  List[VideoVerseItem]

@router.post('/api/bible/video')
async def generate_bible_video_endpoint(payload: VideoRequest, request: Request):
    """
    生成圣经章节短视频 (720×1280 MP4, 9:16竖屏)。
    最多 12 节；TTS 配音 + 渐变背景 + 字幕帧。
    大约需要 60-180 秒，请耐心等待。
    无需登录——经文视频属公开内容。
    """

    try:
        from video_gen import generate_bible_video
    except ImportError:
        try:
            from backend.video_gen import generate_bible_video
        except ImportError:
            raise HTTPException(status_code=500, detail='视频生成模块未安装')

    verses_data = [{'verse': v.verse, 'text': v.text} for v in payload.verses]
    try:
        mp4_bytes = await generate_bible_video(
            book=payload.book,
            chapter=payload.chapter,
            verses=verses_data,
            api_key=GOOGLE_TTS_API_KEY or None,
        )
    except Exception as e:
        print(f'[video] 生成失败: {e}', flush=True)
        raise HTTPException(status_code=500, detail=f'视频生成失败: {str(e)}')

    filename = f'{payload.book}{payload.chapter}章.mp4'
    return Response(
        content=mp4_bytes,
        media_type='video/mp4',
        headers={
            'Content-Disposition': f'attachment; filename*=UTF-8''{filename}',
            'Content-Length': str(len(mp4_bytes)),
        },
    )

