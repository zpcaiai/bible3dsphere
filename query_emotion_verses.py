#!/usr/bin/env python3
import argparse
import csv
import json
import os
import time
from typing import Any
from pathlib import Path
from functools import lru_cache

import numpy as np
import requests

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
GEMINI_API_CHAT_KEY = os.getenv("GEMINI_API_CHAT_KEY", "")
SILICONFLOW_EMBEDDING_URL = "https://api.siliconflow.cn/v1/embeddings"
SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"
EMBED_DIM = 1024  # BAAI/bge-m3 维度；与预存 .npy 向量一致
# 第二 embeddings 供应商（SiliconFlow 不可用时降级）。必须是 OpenAI 兼容 /embeddings，
# 且应使用 bge-m3(1024维)以与预存向量同空间。注意：DeepSeek 官方无 embeddings 接口，
# 不能作为 embeddings 降级；请指向同样提供 bge-m3 的服务（如 DeepInfra / Together / Novita / 自建）。
EMBED_FALLBACK_URL = os.getenv("EMBED_FALLBACK_URL", "")
EMBED_FALLBACK_KEY = os.getenv("EMBED_FALLBACK_KEY", "")
EMBED_FALLBACK_MODEL = os.getenv("EMBED_FALLBACK_MODEL", "BAAI/bge-m3")
# Gemini embeddings（OpenAI 兼容端点，复用 GEMINI_API_CHAT_KEY）。
GEMINI_EMBED_URL = "https://generativelanguage.googleapis.com/v1beta/openai/embeddings"
GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL", "gemini-embedding-001")
# 注：text-embedding-004 在 OpenAI 兼容端点 404，已从降级链移除
_GEMINI_EMBED_CHAIN = list(dict.fromkeys([GEMINI_EMBED_MODEL]))
_GEMINI_EMBED_ACTIVE = None  # 运行时记住可用的模型，避免反复试错
# embeddings 主供应商：默认有 Gemini key 就用 gemini，否则 siliconflow。可用 EMBED_PROVIDER 覆盖。
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "gemini" if GEMINI_API_CHAT_KEY else "siliconflow").lower()
_EMBED_DIM_ACTUAL = None  # 运行时探测到的实际维度（防止失败兜底维度不一致）

REQUEST_TIMEOUT = 60
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0

# ── AI 降级状态追踪（配额/余额）──────────────────────────────────────────────
_AI_STATUS = {"quota": 0.0, "balance": 0.0}

def _record_ai_issue(kind: str) -> None:
    if kind in _AI_STATUS:
        _AI_STATUS[kind] = time.time()

def get_ai_status(window_sec: int = 600) -> dict:
    now = time.time()
    quota = bool(_AI_STATUS["quota"]) and (now - _AI_STATUS["quota"]) < window_sec
    balance = bool(_AI_STATUS["balance"]) and (now - _AI_STATUS["balance"]) < window_sec
    return {"degraded": bool(quota or balance),
            "quota_exhausted": bool(quota),
            "balance_insufficient": bool(balance)}

GEMINI_COOLDOWN_SEC = 180  # Gemini 撞 429 后这段时间内直接跳过，先用 SiliconFlow

def _gemini_in_cooldown() -> bool:
    t = _AI_STATUS.get("quota", 0.0)
    return bool(t) and (time.time() - t) < GEMINI_COOLDOWN_SEC

_HERE = Path(__file__).resolve().parent
FEATURES_FILE = str(_HERE / "emotion_features_map.json")
MATCHES_FILE = str(_HERE / "emotion_exemplar_verse_matches.json")
_EMBED_CACHE_SIG = "bge-m3" if EMBED_PROVIDER == "siliconflow" else GEMINI_EMBED_MODEL
EMBEDDING_CACHE_FILE = str(_HERE / (
    "emotion_feature_embedding_cache.json" if EMBED_PROVIDER == "siliconflow"
    else f"emotion_feature_embedding_cache.{_EMBED_CACHE_SIG}.json"
))
DEFAULT_TOP_FEATURES = 5
DEFAULT_TOP_VERSES_PER_LANGUAGE = 5
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "1"))  # 默认1，规避部分Gemini代理不支持数组输入
DEFAULT_OUTPUT_DIR = str(_HERE / "query_outputs")
DEFAULT_ENABLE_RERANK = False
DEFAULT_RERANK_CANDIDATES = 20
DEFAULT_RERANK_WEIGHT = 0.3
RERANK_MODEL_NAME = os.getenv("RERANK_MODEL_NAME", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
SILICONFLOW_CHAT_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICONFLOW_CHAT_MODEL = "deepseek-ai/DeepSeek-V3"
GEMINI_CHAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
GEMINI_CHAT_MODEL = "gemini-3.1-flash-lite"
LLM_RERANK_MODEL = os.getenv("LLM_RERANK_MODEL", "Qwen/Qwen2.5-32B-Instruct")

RERANKER = None
RERANKER_LOAD_ERROR = None

# ── In-memory cache: loaded once at startup, never reloaded ──────────────────
_CACHE_FEATURES: list[dict] | None = None
_CACHE_FEATURE_EMBEDDINGS: "np.ndarray | None" = None
_CACHE_MATCHES_BY_FEATURE: dict | None = None


# ── English → Chinese book name translation (safety-net for legacy data) ─────
_EN_TO_ZH_BOOK: dict[str, str] = {
    "Genesis": "创世记", "Exodus": "出埃及记", "Leviticus": "利未记",
    "Numbers": "民数记", "Deuteronomy": "申命记", "Joshua": "约书亚记",
    "Judges": "士师记", "Ruth": "路得记", "1 Samuel": "撒母耳记上",
    "2 Samuel": "撒母耳记下", "1 Kings": "列王纪上", "2 Kings": "列王纪下",
    "1 Chronicles": "历代志上", "2 Chronicles": "历代志下", "Ezra": "以斯拉记",
    "Nehemiah": "尼希米记", "Esther": "以斯帖记", "Job": "约伯记",
    "Psalms": "诗篇", "Proverbs": "箴言", "Ecclesiastes": "传道书",
    "Song of Solomon": "雅歌", "Song of Songs": "雅歌",
    "Isaiah": "以赛亚书", "Jeremiah": "耶利米书", "Lamentations": "耶利米哀歌",
    "Ezekiel": "以西结书", "Daniel": "但以理书", "Hosea": "何西阿书",
    "Joel": "约珥书", "Amos": "阿摩司书", "Obadiah": "俄巴底亚书",
    "Jonah": "约拿书", "Micah": "弥迦书", "Nahum": "那鸿书",
    "Habakkuk": "哈巴谷书", "Zephaniah": "西番雅书", "Haggai": "哈该书",
    "Zechariah": "撒迦利亚书", "Malachi": "玛拉基书",
    "Matthew": "马太福音", "Mark": "马可福音", "Luke": "路加福音",
    "John": "约翰福音", "Acts": "使徒行传", "Romans": "罗马书",
    "1 Corinthians": "哥林多前书", "2 Corinthians": "哥林多后书",
    "Galatians": "加拉太书", "Ephesians": "以弗所书", "Philippians": "腓立比书",
    "Colossians": "歌罗西书", "1 Thessalonians": "帖撒罗尼迦前书",
    "2 Thessalonians": "帖撒罗尼迦后书", "1 Timothy": "提摩太前书",
    "2 Timothy": "提摩太后书", "Titus": "提多书", "Philemon": "腓利门书",
    "Hebrews": "希伯来书", "James": "雅各书", "1 Peter": "彼得前书",
    "2 Peter": "彼得后书", "1 John": "约翰一书", "2 John": "约翰二书",
    "3 John": "约翰三书", "Jude": "犹大书", "Revelation": "启示录",
}

_ZH_TO_EN_BOOK: dict[str, str] = {zh: en for en, zh in _EN_TO_ZH_BOOK.items()}
_BOOK_CODE_TO_EN: dict[str, str] = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers", "DEU": "Deuteronomy",
    "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth", "1SA": "1 Samuel", "2SA": "2 Samuel",
    "1KI": "1 Kings", "2KI": "2 Kings", "1CH": "1 Chronicles", "2CH": "2 Chronicles",
    "EZR": "Ezra", "NEH": "Nehemiah", "EST": "Esther", "JOB": "Job", "PSA": "Psalms",
    "PRO": "Proverbs", "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah",
    "JER": "Jeremiah", "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel",
    "HOS": "Hosea", "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
    "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah",
    "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi", "MAT": "Matthew",
    "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts", "ROM": "Romans",
    "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians", "EPH": "Ephesians",
    "PHP": "Philippians", "COL": "Colossians", "1TH": "1 Thessalonians",
    "2TH": "2 Thessalonians", "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus",
    "PHM": "Philemon", "HEB": "Hebrews", "JAS": "James", "1PE": "1 Peter",
    "2PE": "2 Peter", "1JN": "1 John", "2JN": "2 John", "3JN": "3 John",
    "JUD": "Jude", "REV": "Revelation",
}


def _english_book_name(name: str) -> str:
    """Return a standard English book name from English, Chinese, or USFM-style codes."""
    raw = str(name or "").strip()
    return _BOOK_CODE_TO_EN.get(raw.upper(), _ZH_TO_EN_BOOK.get(raw, raw))


def _zh_book_name(name: str) -> str:
    """Return the Chinese book name; passthrough if already Chinese or unknown."""
    return _EN_TO_ZH_BOOK.get(_english_book_name(name), name)


def _display_book_name(language: str, name: str) -> str:
    if language == "esv":
        return _english_book_name(name)
    return _zh_book_name(name)


def _ensure_loaded(
    features_file: str = FEATURES_FILE,
    matches_file: str = MATCHES_FILE,
    cache_file: str = EMBEDDING_CACHE_FILE,
) -> tuple:
    """Load data once into module-level memory; subsequent calls are instant."""
    global _CACHE_FEATURES, _CACHE_FEATURE_EMBEDDINGS, _CACHE_MATCHES_BY_FEATURE
    if _CACHE_FEATURES is None:
        print('[cache] cold start: loading features and embeddings...', flush=True)
        t0 = time.perf_counter()
        features = load_json(features_file)
        matches = load_json(matches_file)
        features, feature_embeddings = load_or_build_feature_embeddings(features, cache_file)
        _CACHE_FEATURES = features
        _CACHE_FEATURE_EMBEDDINGS = feature_embeddings
        _CACHE_MATCHES_BY_FEATURE = map_matches_by_feature(matches)
        print(f'[cache] loaded {len(features)} features in {time.perf_counter()-t0:.2f}s', flush=True)
    else:
        print(f'[cache] hit: {len(_CACHE_FEATURES)} features already in memory', flush=True)
    return _CACHE_FEATURES, _CACHE_FEATURE_EMBEDDINGS, _CACHE_MATCHES_BY_FEATURE


def prewarm_cache() -> None:
    """Call at server startup to avoid cold-start latency on first request."""
    _ensure_loaded()

PSYCHOLOGICAL_SYSTEM_PROMPT = """你是一位深植于基督教灵修传统的属灵导师，同时具备牧关聆听的温柔。
你的话语应当像一封来自父神心怀的信——有圣经的根基，有圣灵的温度，有盼望的光芒。

请按以下四个维度回应，语言贴近灵修日记与属灵书信的风格，避免临床术语，使用圣经意象、神学词汇（恩典、救赎、蒙爱、圣约、同在、更新、盼望、交托、默想）：

1. **core_emotions**：2-4 个词，用属灵语言命名此刻的心灵处境（如"哀恸"而非"悲伤"，"灵里枯干"而非"疲惫"，"渴慕神同在"而非"孤独"）。

2. **psychological_assessment**：2-3 句，以牧者的眼光温柔地看见这个人——承认他/她的挣扎是真实的，同时将其置于神的救赎叙事中（不要诊断，要见证）。

3. **coping_suggestions**：1-2 条属灵操练的邀请——例如：安静默祷、诵读某类诗篇、倾心吐意痛苦、放下控制权交托给神、在团契中寻求代祷。每条以"你可以……"开头，语气是邀请而非指令。

4. **spiritual_guidance**：1 段深刻的灵性话语（4-6 句），用圣经神学（如神的信实、基督的同受苦难、圣灵的保惠、末世的盼望）来诠释此处境，引用或化用 1 处圣经意象，语气如同一封写给受苦之人的信，有诗意，有重量，有温度。

5. **core_need**：一句话，以"你的灵魂此刻最深的渴望是……"开头，道出这个人在神面前最核心的属灵需要。

回应使用中文，总长度不超过 400 字。
【CRITICAL】你只允许输出合法的 JSON 对象。不要 markdown 代码块、不要任何解释文字、不要任何前后缀。输出的第一个字符必须是 {，最后一个字符必须是 }。
请严格按以下 JSON 格式输出：
{
  "core_emotions": ["词1", "词2"],
  "psychological_assessment": "...",
  "coping_suggestions": ["你可以……", "你可以……"],
  "spiritual_guidance": "...",
  "core_need": "你的灵魂此刻最深的渴望是……"
}"""


PSYCHOLOGICAL_SYSTEM_PROMPT_EN = """You are a spiritual mentor rooted in historic Christian devotional tradition, with the gentleness of pastoral listening.
Your words should feel like a letter shaped by the Father's compassion: grounded in Scripture, warm with the Spirit's comfort, and bright with hope.

Respond in these five dimensions. Use the style of a devotional journal and pastoral letter. Avoid clinical labels. Use biblical and theological language such as grace, redemption, belovedness, covenant, presence, renewal, hope, surrender, and meditation.

1. **core_emotions**: 2-4 short English phrases naming the soul's present condition in spiritual language, for example "grief before God", "thirst for God's presence", or "weary hope".

2. **psychological_assessment**: 2-3 sentences that gently see the person through pastoral eyes. Acknowledge that the struggle is real, while placing it inside God's redemptive story. Do not diagnose; bear witness.

3. **coping_suggestions**: 1-2 invitations to spiritual practice. Each item must begin with "You can..." and sound invitational, not commanding.

4. **spiritual_guidance**: one substantial pastoral paragraph, 4-6 sentences, interpreting the situation through biblical theology. Use or echo one biblical image. The tone should feel like a letter to someone who is suffering: poetic, weighty, and warm.

5. **core_need**: one sentence beginning exactly with "Your soul's deepest longing right now is..." and naming the person's core spiritual need before God.

Respond entirely in natural English. Do not include any Chinese characters. Total length under 400 English words.
【CRITICAL】Output only a valid JSON object. No markdown code fence, no explanation, no prefix or suffix. The first character must be { and the last character must be }.
Use exactly this JSON shape:
{
  "core_emotions": ["phrase 1", "phrase 2"],
  "psychological_assessment": "...",
  "coping_suggestions": ["You can...", "You can..."],
  "spiritual_guidance": "...",
  "core_need": "Your soul's deepest longing right now is..."
}"""


BIBLICAL_EXAMPLE_PROMPT = """你是一位熟悉圣经与历世历代圣徒生命的属灵导师。

根据用户所描述的情绪处境或心理处境，请从以下两个来源之一选取**最贴近**的榜样性案例：
A. 圣经中的人物（如约瑟、大卫、以利亚、约伯、抹大拉的马利亚、保罗等）
B. 历史上的基督徒圣徒（如奥古斯丁、约翰·卫斯理、戴德生、科里·邓·布姆、马丁·路德等）

请提供一个案例，包含以下内容：
1. **person**：人物姓名（简短，如"大卫"或"约伯"）
2. **era**：时代背景（如"旧约时期"、"使徒时代"、"17世纪清教徒"）
3. **similar_situation**：2-3 句，简述此人所经历的与用户处境相似的具体困境或情绪状态
4. **biblical_response**：2-3 句，说明此人如何在信仰中回应这一处境——其具体行动、祷告、或转变
5. **key_verse**：一节相关经文（书卷 章:节 经文内容），从此人的经历中提炼，作为应用的锚点
6. **application**：1-2 句，将这个榜样的经历与用户的处境连结，给出实际的属灵功课

语言使用中文，简洁有力，有圣经根基，总字数不超过 300 字。
【CRITICAL】你只允许输出合法的 JSON 对象。不要 markdown 代码块、不要任何解释文字、不要任何前后缀。输出的第一个字符必须是 {，最后一个字符必须是 }。
请严格按以下 JSON 格式输出：
{
  "person": "...",
  "era": "...",
  "similar_situation": "...",
  "biblical_response": "...",
  "key_verse": "...",
  "application": "..."
}"""


def _strip_markdown_json(raw: str) -> str:
    """Remove ```json / ``` fences and any leading prose that LLMs sometimes add."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    # Extract the outermost JSON object/array even if the model added prose before it
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    return raw


def _call_llm_with_fallback(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 600,
    temperature: float = 0.7,
    tag: str = "llm",
) -> str:
    """
    Try Gemini first; fall back to SiliconFlow/DeepSeek-V3 on any error.
    Returns the raw text content string, or raises the last exception.
    """
    # Force English output when the request asked for it (per-request ContextVar).
    try:
        from lang_context import localize_system_prompt as _loc_sys
        system_prompt = _loc_sys(system_prompt)
    except Exception:
        pass
    seed_hint = f"[{int(time.time() * 1000) % 99991}]"
    user_content = f"{user_message} {seed_hint}"

    providers = []
    if GEMINI_API_CHAT_KEY and _gemini_in_cooldown():
        print(f"[{tag}] Gemini 跳过(429 冷却中)，直接用 SiliconFlow", flush=True)
    elif GEMINI_API_CHAT_KEY:
        providers.append((GEMINI_CHAT_URL, {
            "Authorization": f"Bearer {GEMINI_API_CHAT_KEY}",
            "Content-Type": "application/json",
        }, GEMINI_CHAT_MODEL, "Gemini"))
    else:
        print(f"[{tag}] Gemini unavailable: GEMINI_API_CHAT_KEY not set", flush=True)

    # Always include SiliconFlow as fallback
    if DEEPSEEK_API_KEY:
        providers.append((DEEPSEEK_CHAT_URL, {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }, DEEPSEEK_CHAT_MODEL, "DeepSeek"))
    if SILICONFLOW_API_KEY:
        providers.append((SILICONFLOW_CHAT_URL, siliconflow_headers(), SILICONFLOW_CHAT_MODEL, "SiliconFlow"))

    last_exc = None
    for url, headers, model, provider in providers:
        # Lower temperature for JSON-output prompts to improve format adherence
        effective_temp = 0.1 if "json" in system_prompt.lower() else temperature
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": effective_temp,
            "max_tokens": max_tokens,
        }
        # Gemini: fast-fail on auth/quota issues (403/429) to avoid wasting retries
        _retries = 2 if provider == "Gemini" else None
        try:
            data = post_with_retry(url, payload, headers, max_retries=_retries)
            content = data["choices"][0]["message"]["content"]
            print(f"[{tag}] ok via {provider} len={len(content)}", flush=True)
            return content
        except Exception as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            print(f"[{tag}] {provider} failed status={status}: {type(e).__name__}: {str(e)[:120]}", flush=True)
            if provider == "Gemini" and status in (403, 429):
                print(f"[{tag}] Gemini quota/auth issue ({status}), downgrading to SiliconFlow...", flush=True)
            last_exc = e
            continue

    raise last_exc or RuntimeError(f"[{tag}] all providers failed")


def fetch_biblical_example(query_text: str) -> dict:
    print(f'[biblical_example] query={query_text[:60]}...', flush=True)
    cache_key = _cache_key(BIBLICAL_EXAMPLE_PROMPT, query_text, 500)
    cached = llm_cache.get(cache_key)
    if cached:
        print('[biblical_example] cache hit', flush=True)
        return cached
    try:
        raw_content = _call_llm_with_fallback(
            system_prompt=BIBLICAL_EXAMPLE_PROMPT,
            user_message=query_text,
            max_tokens=500,
            temperature=0.7,
            tag="biblical_example",
        )
    except Exception as e:
        print(f'[biblical_example] all providers failed: {e}', flush=True)
        return {"person":"大卫","era":"旧约","similar_situation":"面对极大压力时依靠神","biblical_response":"转向神、祷告求力量","key_verse":"诗篇 56:3-4","application":"停下来祷告交托重担","service_error":str(e)[:80]}
    raw = _strip_markdown_json(raw_content)
    try:
        result = json.loads(raw)
        llm_cache.set(cache_key, result)
        print(f'[biblical_example] ok person={result.get("person")} era={result.get("era")}', flush=True)
        return result
    except json.JSONDecodeError:
        print('[biblical_example] JSON parse error, returning raw text', flush=True)
        return {"person":"","era":"","similar_situation":raw,"biblical_response":"","key_verse":"","application":"","parse_error":True}


SERMON_PROMPT = """你是一位深植于改革宗传统、受过神学训练、具有牧养心肠的传道人。
请根据会众所描述的情绪处境或人生挣扎，撰写一篇完整、高质量的个性化讲章。

讲章须具备以下完整结构，严格按 JSON 格式输出：

{
  "title": "讲章标题（有诗意、有力量、贴合主题）",
  "theme_verse": "主题经文（书卷 章:节 — 经文原文）",
  "introduction": "引言（4-6句：以处境共鸣切入，描绘这处境的真实感受，引出属灵张力，以圣经意象作桥梁，自然过渡到主题）",
  "sections": [
    {
      "heading": "第一段标题",
      "content": "段落内容（6-9句：深入剖析这处境的属灵本质，以神学概念为骨架，以圣经叙事或人物为血肉，语言有重量、有温度，引领会众看见神的角度）",
      "supporting_verse": "支持经文（书卷 章:节 — 完整经文原文）"
    },
    {
      "heading": "第二段标题",
      "content": "段落内容（6-9句：深化主题，聚焦神在基督里的回应——受苦、同在、救赎，用具体的圣经图景说话，避免空洞安慰）",
      "supporting_verse": "支持经文（书卷 章:节 — 完整经文原文）"
    },
    {
      "heading": "第三段标题",
      "content": "段落内容（6-9句：从神学转向生命应用，描述信心的回应是什么样子，语气从剖析转为邀请，充满盼望与力量）",
      "supporting_verse": "支持经文（书卷 章:节 — 完整经文原文）"
    }
  ],
  "spiritual_diagnosis": "属灵问题剖析（3-4句：温柔但诚实地洞察这处境背后的属灵根源或张力，不是指责，是牧者的眼光——看见挣扎，也看见神的邀请）",
  "historical_case": {
    "person": "人物名",
    "era": "时代背景",
    "story": "案例叙述（4-6句：生动描述其相似处境、内心挣扎与信仰回应，须来自圣经人物或基督教历史上真实人物，有细节，有张力，有转折）",
    "lesson": "从这案例得到的属灵功课（2-3句）"
  },
  "application": "可操作建议（3条具体的属灵操练或行动步骤，每条以'你可以……'开头，每条后附1-2句解释为何这样做有属灵意义）",
  "encouragement": "勉励与安慰（3-4句：充满盼望的话语，宣告神的信实与同在，语言有诗意，让人在苦中仍能看见光）",
  "prayer": "带领祷告（5-7句：以第一人称祷告语气撰写，诚实倾诉处境，认罪、信靠、感恩、求恩，语气真挚深沉）",
  "conclusion": "结语与盼望（3-4句：呼应引言，以末世盼望或基督复活的角度作结，留下余韵，让人带着力量离开）"
}

要求：
- 语言风格：属灵书信与布道台的结合，有诗意、有神学深度、有牧者温度
- 神学立场：以基督为中心，恩典为根基，圣灵为动力
- 总长度：1200-1800字（中文）
- 严格输出 JSON，不要附带 markdown 代码块或其他说明"""


FAITH_QA_PROMPT = """你是一位受过严格神学训练的基督教护教学者与牧师，精通系统神学、圣约神学、基要派与福音派传统。
请根据提问者的问题，给出全面、有深度、有实践性的回答。

严格按以下 JSON 格式输出，不要附带 markdown 代码块或任何其他说明：

{
  "question_summary": "用一句话准确概括提问者的核心问题",
  "nature_analysis": "问题本质分析（3-5句）：从系统神学与圣约神学角度，剖析这个问题的神学本质、历史背景以及它为何重要，指出其中涉及的核心教义张力或误解根源",
  "contextual_analysis": "具体情景分析（3-5句）：结合提问者可能的实际处境，分析这个问题在信仰生活、教会实践或个人灵修中的具体表现，展示神学如何照进真实生活",
  "scriptures": [
    {
      "reference": "书卷 章:节",
      "text": "完整经文原文",
      "relevance": "为什么这节经文最能回应这个问题（2-3句）"
    },
    {
      "reference": "书卷 章:节",
      "text": "完整经文原文",
      "relevance": "为什么这节经文最能回应这个问题（2-3句）"
    },
    {
      "reference": "书卷 章:节",
      "text": "完整经文原文",
      "relevance": "为什么这节经文最能回应这个问题（2-3句）"
    }
  ],
  "right_thinking": "正确思考方式（4-6句）：基于圣经与改革宗神学传统，指导提问者如何从神的视角重新框架这个问题，纠正常见的神学偏差，建立以基督为中心的思考模式",
  "action_steps": [
    "行动建议一：具体可操作，含属灵意义说明",
    "行动建议二：具体可操作，含属灵意义说明",
    "行动建议三：具体可操作，含属灵意义说明"
  ],
  "prayer_direction": "祷告方向示范（5-7句，以第一人称祷告语气）：认罪、信靠、感恩、具体祈求，语气真挚，针对性强，让提问者能直接使用"
}

神学立场要求：
- 以圣经为最高权威（圣经无误论）
- 基督中心解经（所有问题最终指向基督的救赎）
- 圣约神学框架（旧约与新约的连续性与应验）
- 福音派与基要派的信仰坚守（三位一体、道成肉身、代赎、复活、再来）
- 语言：有神学深度但不失温度，学术严谨但贴近生活
- 总长度：900-1400字（中文）"""


def generate_faith_qa(question: str) -> dict:
    print(f'[faith_qa] generate_faith_qa question={question[:60]}...', flush=True)
    cache_key = _cache_key(FAITH_QA_PROMPT, question, 2200)
    cached = llm_cache.get(cache_key)
    if cached:
        print('[faith_qa] cache hit', flush=True)
        return cached
    try:
        raw_content = _call_llm_with_fallback(
            system_prompt=FAITH_QA_PROMPT,
            user_message=question,
            max_tokens=2200,
            temperature=0.7,
            tag="faith_qa",
        )
    except Exception as e:
        print(f'[faith_qa] all providers failed: {e}', flush=True)
        return {"question_summary": question, "nature_analysis": f"（信仰问答服务暂时不可用，请稍后重试。错误：{str(e)[:80]}）", "contextual_analysis": "", "scriptures": [], "right_thinking": "", "action_steps": [], "prayer_direction": "", "service_error": str(e)[:120]}
    raw = _strip_markdown_json(raw_content)
    try:
        result = json.loads(raw)
        llm_cache.set(cache_key, result)
        print(f'[faith_qa] ok question_summary={result.get("question_summary", "")[:40]}', flush=True)
        return result
    except json.JSONDecodeError:
        print('[faith_qa] JSON parse error, returning raw text', flush=True)
        return {"question_summary": question, "nature_analysis": raw, "contextual_analysis": "", "scriptures": [], "right_thinking": "", "action_steps": [], "prayer_direction": "", "parse_error": True}


def generate_sermon(query_text: str) -> dict:
    print(f'[sermon] generate_sermon query={query_text[:60]}...', flush=True)
    cache_key = _cache_key(SERMON_PROMPT, query_text, 2800)
    cached = llm_cache.get(cache_key)
    if cached:
        print('[sermon] cache hit', flush=True)
        return cached
    try:
        raw_content = _call_llm_with_fallback(
            system_prompt=SERMON_PROMPT,
            user_message=query_text,
            max_tokens=2800,
            temperature=0.9,
            tag="sermon",
        )
    except Exception as e:
        print(f'[sermon] all providers failed: {e}', flush=True)
        return {"title":"在风暴中靠主平静","theme_verse":"诗篇 46:1-3","introduction":f"（讲章生成服务暂时不可用，请稍后重试。错误：{str(e)[:80]}）","sections":[],"conclusion":"","service_error":str(e)[:120]}
    raw = _strip_markdown_json(raw_content)
    try:
        result = json.loads(raw)
        llm_cache.set(cache_key, result)
        print(f'[sermon] ok title={result.get("title", "")}', flush=True)
        return result
    except json.JSONDecodeError:
        print('[sermon] JSON parse error, returning raw intro text', flush=True)
        return {"title":"讲章","introduction":raw,"parse_error":True}


def generate_verse_prayer(reference: str, text: str, language: str = "zh") -> dict:
    """根据一处经文生成简短祷告。返回 {prayer, reference}（前端读 data.prayer）。"""
    print(f'[verse_prayer] reference={reference}', flush=True)
    wants_en = str(language or "").lower().startswith("en")
    if wants_en:
        user_msg = (
            f"Bible reference: {reference}\nVerse text: {text}\n"
            "Write a short, warm, first-person prayer based on this verse, about 80-120 English words. "
            "Return only the prayer body. Do not include a title, quotation marks, explanations, or Chinese characters."
        )
        system_prompt = (
            "You are a gentle pastoral prayer writer. Write entirely in natural English, "
            "with biblically faithful language and standard English Bible references."
        )
    else:
        user_msg = (
            f"经文出处：{reference}\n经文内容：{text}\n"
            "请根据这处经文，写一段简短（约80-120字）、温暖、第一人称的祷告。"
            "只输出祷告正文，不要任何标题、引号或解释。"
        )
        system_prompt = "你是一位牧者，善于根据圣经经文带领简短的祷告。用简体中文，语气温柔、合乎圣经真理。"
    try:
        raw = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_msg, max_tokens=400, temperature=0.7, tag="verse_prayer",
        )
        prayer = (raw or "").strip()
        if not prayer:
            raise ValueError("empty prayer")
        print(f'[verse_prayer] ok len={len(prayer)}', flush=True)
        return {"prayer": prayer, "reference": reference}
    except Exception as e:
        print(f'[verse_prayer] failed: {e}', flush=True)
        if wants_en:
            return {
                "prayer": f"Lord, thank You for speaking to me through {reference}. Help me receive Your Word with faith, remember it throughout this day, and walk in obedience by Your grace. In the name of Jesus Christ, amen.",
                "reference": reference, "service_error": str(e)[:120],
            }
        return {
            "prayer": f"主啊，谢谢你借着{reference}向我说话。求你帮助我默想你的话语、存记在心，并靠你的恩典去遵行。奉主耶稣的名祷告，阿们。",
            "reference": reference, "service_error": str(e)[:120],
        }


def generate_meditation_questions(reference: str, text: str, language: str = "zh") -> dict:
    """根据一处经文生成默想问题。返回 {questions: [...]}（前端读 data.questions）。"""
    print(f'[meditation] reference={reference}', flush=True)
    wants_en = str(language or "").lower().startswith("en")
    if wants_en:
        user_msg = (
            f"Bible reference: {reference}\nVerse text: {text}\n"
            "Create 4 personal devotional meditation questions based on this verse. "
            "Return only a JSON string array, for example [\"Question one\", \"Question two\"]. "
            "Do not include Chinese characters or any extra text."
        )
        system_prompt = (
            "You are a pastor guiding Scripture meditation. Write entirely in natural English. "
            "Ask reflective, pastoral questions that help the reader observe, examine the heart, and respond in faith."
        )
    else:
        user_msg = (
            f"经文出处：{reference}\n经文内容：{text}\n"
            "请基于这处经文，提出 4 个适合个人灵修默想的问题，帮助读者反思与应用。"
            "只输出一个 JSON 字符串数组，例如 [\"问题一\", \"问题二\"]，不要任何其它文字。"
        )
        system_prompt = "你是带领灵修默想的牧者，善于提出引导反思与应用的问题。用简体中文。"
    try:
        raw = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=user_msg, max_tokens=600, temperature=0.7, tag="meditation",
        )
        parsed = json.loads(_strip_markdown_json(raw))
        if isinstance(parsed, dict) and isinstance(parsed.get("questions"), list):
            items = parsed["questions"]
        elif isinstance(parsed, list):
            items = parsed
        else:
            items = []
        questions = [str(q).strip() for q in items if str(q).strip()]
        if not questions:
            raise ValueError("empty questions")
        print(f'[meditation] ok count={len(questions)}', flush=True)
        return {"questions": questions}
    except Exception as e:
        print(f'[meditation] failed: {e}', flush=True)
        if wants_en:
            return {
                "questions": [
                    f"What does {reference} reveal about God's character, will, or promise?",
                    "How does this verse speak to my current situation with comfort, correction, or challenge?",
                    "Where do I need to repent, trust, or respond with faith?",
                    "What concrete step can I take today to live out this verse?",
                ],
                "service_error": str(e)[:120],
            }
        return {
            "questions": [
                f"这处经文（{reference}）让我看见神怎样的属性与心意？",
                "它对我现在的处境有什么提醒、安慰或挑战？",
                "我需要在哪方面悔改，或凭信心做出回应？",
                "今天我可以如何把这节经文具体活出来？",
            ],
            "service_error": str(e)[:120],
        }


def post_with_retry(url: str, payload: dict, headers: dict, max_retries: int | None = None) -> dict:
    model = payload.get('model', url.split('/')[-1])
    print(f'[api] POST {url.split("/v1/")[-1]} model={model}', flush=True)
    _max_retries = max_retries if max_retries is not None else MAX_RETRIES
    # 长输出(如查经 max_tokens=6000)生成耗时久，按 max_tokens 放宽读超时，避免 60s ReadTimeout
    _mt = payload.get('max_tokens', 0) or 0
    _timeout = 180 if _mt >= 2000 else REQUEST_TIMEOUT
    for attempt in range(1, _max_retries + 1):
        try:
            t0 = time.perf_counter()
            response = requests.post(url, json=payload, headers=headers, timeout=_timeout)
            response.raise_for_status()
            print(f'[api] ok latency={round((time.perf_counter()-t0)*1000)}ms attempt={attempt}', flush=True)
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            _body0 = ''
            try:
                _body0 = (e.response.text or '').lower()
            except Exception:
                pass
            # 月度消费上限 429：重试无意义，直接失败（普通限流 429 仍重试）
            _spend_cap = ('spending cap' in _body0) or ('ai.studio/spend' in _body0)
            if status in (429, 500, 502, 503, 504) and attempt < _max_retries and not _spend_cap:
                wait = RETRY_BACKOFF ** attempt
                print(f'[api] HTTP {status}, retry {attempt}/{_max_retries - 1}, wait {wait:.1f}s', flush=True)
                time.sleep(wait)
                continue
            body = ''
            try:
                body = e.response.text[:500]
            except Exception:
                pass
            # Log payload (sanitized) for 400/401 debugging
            safe_payload = {k: v for k, v in payload.items() if k != 'messages'}
            if 'messages' in payload:
                safe_payload['msg_count'] = len(payload['messages'])
                safe_payload['first_msg_preview'] = str(payload['messages'][0].get('content', ''))[:80] if payload['messages'] else ''
            print(f'[api] HTTPError {status} after {attempt} attempts body={body} payload={safe_payload}', flush=True)
            _bl = body.lower()
            if status == 429 or 'resource_exhausted' in _bl or 'spend' in _bl:
                _record_ai_issue('quota')
            elif status == 403 or 'insufficient' in _bl:
                _record_ai_issue('balance')
            raise
        except (
            requests.exceptions.Timeout,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        ) as e:
            if attempt < _max_retries:
                wait = RETRY_BACKOFF ** attempt
                print(f'[api] connection error ({type(e).__name__}), retry {attempt}/{_max_retries - 1}, wait {wait:.1f}s', flush=True)
                time.sleep(wait)
                continue
            print(f'[api] connection failed after {attempt} attempts: {e}', flush=True)
            raise


def siliconflow_headers() -> dict:
    if not SILICONFLOW_API_KEY:
        raise RuntimeError("SILICONFLOW_API_KEY is required")
    return {
        "Authorization": f"Bearer {SILICONFLOW_API_KEY}",
        "Content-Type": "application/json",
    }


def chat_url_and_headers() -> tuple[str, dict]:
    """Chat API 优先使用 Gemini；若 key 未配置则降级到 SiliconFlow/DeepSeek-V3。"""
    if GEMINI_API_CHAT_KEY:
        # Gemini API keys typically start with 'AI' and are ~39 chars
        if not GEMINI_API_CHAT_KEY.startswith(('AI', 'ya29.')):
            print(f'[api] WARN: GEMINI_API_CHAT_KEY format looks unusual (prefix={GEMINI_API_CHAT_KEY[:4]}... len={len(GEMINI_API_CHAT_KEY)}). Expecting keys starting with AI...', flush=True)
        print(f'[api] Gemini endpoint={GEMINI_CHAT_URL} model={GEMINI_CHAT_MODEL}', flush=True)
        return GEMINI_CHAT_URL, {
            "Authorization": f"Bearer {GEMINI_API_CHAT_KEY}",
            "Content-Type": "application/json",
        }
    # Gemini 未配置时：优先 DeepSeek 官方（便宜且余额不过期），再退 SiliconFlow
    if DEEPSEEK_API_KEY:
        print('[api] GEMINI key not set, falling back to DeepSeek', flush=True)
        return DEEPSEEK_CHAT_URL, {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    print('[api] GEMINI_API_CHAT_KEY not set, falling back to SiliconFlow/DeepSeek-V3', flush=True)
    return SILICONFLOW_CHAT_URL, siliconflow_headers()


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return (vectors / norms).astype(np.float32)


def sigmoid(value: float) -> float:
    if value >= 0:
        z = np.exp(-value)
        return float(1.0 / (1.0 + z))
    z = np.exp(value)
    return float(z / (1.0 + z))



# ---------------------------------------------------------------------------
# MMR (Maximal Marginal Relevance) diversity re-ranking
# Reference: Carbonell & Goldstein (1998)
# ---------------------------------------------------------------------------
DEFAULT_MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.5"))


def mmr_rerank(
    query_text: str,
    verses: list[dict],
    top_n: int,
    lambda_: float = DEFAULT_MMR_LAMBDA,
) -> list[dict]:
    """Maximal Marginal Relevance re-ranking to improve result diversity.

    Balances relevance (similarity to query) against novelty (dissimilarity to
    already-selected verses).  lambda_=1.0 → pure relevance; lambda_=0.0 → pure diversity.

    The verse vectors are approximated by embedding their raw_text on the fly only
    if a verse vector is not already stored; otherwise the pre-computed combined_score
    is used as a scalar proxy for relevance, avoiding an extra embedding call.

    Algorithm::
        selected = []
        remaining = all candidates
        while len(selected) < top_n and remaining:
            best = argmax_{d in remaining} [
                lambda_ * relevance(d) - (1-lambda_) * max_{s in selected} sim(d, s)
            ]
            selected.append(best)

    Returns top_n verses re-ordered for diversity.
    """
    if not verses or top_n <= 0:
        return verses[:top_n]
    if len(verses) <= 1:
        return verses[:top_n]

    import numpy as _np

    # Relevance proxy: use pre-computed final_score / combined_score (already normalised 0-1)
    def rel(v: dict) -> float:
        return float(v.get("final_score") or v.get("combined_score") or 0.0)

    # Try to embed verse texts for diversity computation; fall back to title-overlap heuristic
    try:
        texts = [str(v.get("raw_text") or "") for v in verses]
        vecs = get_embeddings(texts)   # (n, d) normalised
        use_vecs = True
    except Exception:
        use_vecs = False

    def sim_pair(i: int, j: int) -> float:
        if use_vecs:
            return float(_np.dot(vecs[i], vecs[j]))
        # Fallback: Jaccard on character 4-grams
        a = set(texts[i][k:k+4] for k in range(len(texts[i])-3)) if len(texts[i]) > 3 else set()
        b = set(texts[j][k:k+4] for k in range(len(texts[j])-3)) if len(texts[j]) > 3 else set()
        return len(a & b) / max(len(a | b), 1)

    selected_idx: list[int] = []
    remaining_idx: list[int] = list(range(len(verses)))

    while len(selected_idx) < top_n and remaining_idx:
        best_i = -1
        best_score = float("-inf")
        for i in remaining_idx:
            relevance = lambda_ * rel(verses[i])
            if selected_idx:
                max_sim = max(sim_pair(i, j) for j in selected_idx)
                diversity = (1.0 - lambda_) * max_sim
            else:
                diversity = 0.0
            score = relevance - diversity
            if score > best_score:
                best_score = score
                best_i = i
        selected_idx.append(best_i)
        remaining_idx.remove(best_i)

    result = []
    for rank, idx in enumerate(selected_idx):
        item = dict(verses[idx])
        item["mmr_rank"] = rank + 1
        item["mmr_score"] = round(rel(verses[idx]), 4)
        result.append(item)

    print(f"[mmr] reranked {len(verses)} → {len(result)} diverse verses (lambda={lambda_})", flush=True)
    return result

def get_reranker() -> Any:
    global RERANKER
    global RERANKER_LOAD_ERROR
    if RERANKER is not None:
        return RERANKER
    try:
        from sentence_transformers import CrossEncoder
    except ImportError as exc:
        RERANKER_LOAD_ERROR = (
            "sentence-transformers is not installed. "
            "Add sentence-transformers and torch to requirements.txt and redeploy."
        )
        raise RuntimeError(RERANKER_LOAD_ERROR) from exc
    try:
        RERANKER = CrossEncoder(RERANK_MODEL_NAME)
        RERANKER_LOAD_ERROR = None
        return RERANKER
    except Exception as exc:
        RERANKER_LOAD_ERROR = f"Failed to load rerank model '{RERANK_MODEL_NAME}': {exc}"
        raise RuntimeError(RERANKER_LOAD_ERROR) from exc


def _embed_via_gemini(batch: list[str]) -> "list[list[float]]":
    """Gemini embeddings（OpenAI 兼容 /embeddings，复用 GEMINI_API_CHAT_KEY）。
    主模型不可用时沿 _GEMINI_EMBED_CHAIN 自动降级（gemini-embedding-001 → text-embedding-004）。"""
    global _GEMINI_EMBED_ACTIVE
    headers = {"Authorization": f"Bearer {GEMINI_API_CHAT_KEY}", "Content-Type": "application/json"}
    models = [_GEMINI_EMBED_ACTIVE] if _GEMINI_EMBED_ACTIVE else _GEMINI_EMBED_CHAIN
    last_exc: "Exception | None" = None
    for model in models:
        try:
            payload = {"model": model, "input": batch, "dimensions": EMBED_DIM}
            data = post_with_retry(GEMINI_EMBED_URL, payload, headers)
            vecs = [item["embedding"] for item in data["data"]]
            if _GEMINI_EMBED_ACTIVE != model:
                print(f'[embeddings] gemini embed model = {model} (dim={len(vecs[0]) if vecs else "?"})', flush=True)
                _GEMINI_EMBED_ACTIVE = model
            return vecs
        except Exception as e:
            last_exc = e
            print(f'[embeddings] gemini model {model} failed: {type(e).__name__}: {e}', flush=True)
            continue
    raise last_exc if last_exc else RuntimeError("all gemini embed models failed")


def _embed_via_fallback(batch: list[str]) -> "list[list[float]] | None":
    """SiliconFlow 不可用时的第二 embeddings 供应商（OpenAI 兼容 /embeddings）。
    失败或返回维度不为 EMBED_DIM 时返回 None（交由调用方退化为零向量）。"""
    if not (EMBED_FALLBACK_URL and EMBED_FALLBACK_KEY):
        return None
    payload = {"model": EMBED_FALLBACK_MODEL, "input": batch, "encoding_format": "float"}
    headers = {"Authorization": f"Bearer {EMBED_FALLBACK_KEY}", "Content-Type": "application/json"}
    try:
        print(f'[embeddings] trying fallback provider url={EMBED_FALLBACK_URL} model={EMBED_FALLBACK_MODEL}', flush=True)
        data = post_with_retry(EMBED_FALLBACK_URL, payload, headers)
        vecs = [item["embedding"] for item in data["data"]]
        if vecs and len(vecs[0]) != EMBED_DIM:
            print(f'[embeddings] fallback dim {len(vecs[0])} != {EMBED_DIM}，与库内向量不同空间，丢弃', flush=True)
            return None
        print(f'[embeddings] fallback provider ok: {len(vecs)} vectors', flush=True)
        return vecs
    except Exception as exc:
        print(f'[embeddings] fallback provider failed: {type(exc).__name__}: {exc}', flush=True)
        return None


def get_embeddings(texts: list[str]) -> np.ndarray:
    global _EMBED_DIM_ACTUAL
    print(f'[embeddings] get_embeddings: {len(texts)} texts, provider={EMBED_PROVIDER}, batch_size={EMBEDDING_BATCH_SIZE}', flush=True)
    all_embeddings = []
    consec_fail = 0
    for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[start:start + EMBEDDING_BATCH_SIZE]
        if consec_fail >= 2:
            # 熔断：连续失败（如消费上限耗尽），余下批次直接零向量，避免启动卡死
            if consec_fail == 2:
                print('[embeddings] CIRCUIT OPEN: 连续失败，余下批次跳过 API 直接用零向量', flush=True)
                consec_fail += 1
            dim = _EMBED_DIM_ACTUAL or EMBED_DIM
            all_embeddings.extend([[0.0] * dim for _ in batch])
            continue
        print(f'[embeddings] batch {start//EMBEDDING_BATCH_SIZE + 1}: {len(batch)} texts', flush=True)
        try:
            if EMBED_PROVIDER == "gemini" and GEMINI_API_CHAT_KEY:
                vecs = _embed_via_gemini(batch)
            else:
                payload = {"model": SILICONFLOW_EMBEDDING_MODEL, "input": batch, "encoding_format": "float"}
                data = post_with_retry(SILICONFLOW_EMBEDDING_URL, payload, siliconflow_headers())
                vecs = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(vecs)
            if vecs:
                _EMBED_DIM_ACTUAL = len(vecs[0])
            consec_fail = 0
        except Exception as exc:
            print(f'[embeddings] primary({EMBED_PROVIDER}) ERROR: {type(exc).__name__}: {exc}', flush=True)
            fb = _embed_via_fallback(batch)
            if fb is not None:
                all_embeddings.extend(fb)
                if fb:
                    _EMBED_DIM_ACTUAL = len(fb[0])
                consec_fail = 0
            else:
                consec_fail += 1
                dim = _EMBED_DIM_ACTUAL or EMBED_DIM
                print(f'[embeddings] FALLBACK: using zero vectors (dim={dim}) for {len(batch)} texts', flush=True)
                for _ in batch:
                    all_embeddings.append([0.0] * dim)
    print(f'[embeddings] done: {len(all_embeddings)} embeddings received', flush=True)
    embeddings = np.asarray(all_embeddings, dtype=np.float32)
    return l2_normalize(embeddings)


def load_json(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_BIBLE_INDEX: dict[str, dict[tuple, dict]] | None = None


def _get_bible_index() -> dict[str, dict[tuple, dict]]:
    """Lazy-load CUV and ESV bibles into a (book, chapter, verse) -> row dict."""
    global _BIBLE_INDEX
    if _BIBLE_INDEX is not None:
        return _BIBLE_INDEX
    index: dict[str, dict[tuple, dict]] = {"cuv": {}, "esv": {}}
    for lang, filename in (("cuv", "cuv_bible.csv"), ("esv", "esv_bible.csv")):
        path = _HERE / "bible" / filename
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["book"], int(row["chapter"]), int(row["verse"]))
                index[lang][key] = {
                    "pk_id": f"{lang}_{row['book']}_{row['chapter']}_{row['verse']}",
                    "book_name": row["book"],
                    "chapter": int(row["chapter"]),
                    "verse": int(row["verse"]),
                    "raw_text": row["text"],
                    "combined_score": 0.0,
                    "final_score": 0.0,
                    "rerank_score": None,
                    "matched_features": [],
                    "counterpart": None,
                    "from_lookup": True,
                }
    _BIBLE_INDEX = index
    return _BIBLE_INDEX


def build_feature_text(feature: dict) -> str:
    parts = [
        str(feature.get("source_keyword", "")).strip(),
        str(feature.get("explanation", "")).strip(),
        str(feature.get("layer", "")).strip(),
        str(feature.get("feature_id", "")).strip(),
    ]
    return " | ".join(part for part in parts if part)


def feature_key(feature: dict) -> str:
    return f"{feature.get('layer')}:{feature.get('feature_id')}"


def load_or_build_feature_embeddings(
    features: list[dict],
    cache_file: str = EMBEDDING_CACHE_FILE,
) -> tuple[list[dict], np.ndarray]:
    cache_path = Path(cache_file)
    cache = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            cache = json.load(f)
        print(f'[embeddings] cache file loaded: {len(cache)} entries from {cache_path.name}', flush=True)
    else:
        print(f'[embeddings] no cache file found at {cache_path.name}, will build from scratch', flush=True)

    missing_features = []
    for feature in features:
        key = feature_key(feature)
        if key not in cache:
            missing_features.append(feature)

    if missing_features:
        print(f'[embeddings] fetching {len(missing_features)} missing embeddings from API...', flush=True)
        texts = [build_feature_text(feature) for feature in missing_features]
        embeddings = get_embeddings(texts)
        
        # 检查是否所有嵌入都是零向量（API 失败的情况）
        all_zero = all(np.allclose(emb, 0) for emb in embeddings)
        if all_zero:
            print(f'[embeddings] WARNING: all embeddings are zero vectors (API failed), not saving cache to avoid pollution', flush=True)
        else:
            for feature, embedding in zip(missing_features, embeddings, strict=True):
                cache[feature_key(feature)] = embedding.tolist()
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            print(f'[embeddings] cache updated and saved: {len(cache)} total entries', flush=True)
    else:
        print(f'[embeddings] all {len(features)} features found in cache, no API call needed', flush=True)

    ordered_embeddings = np.asarray([cache[feature_key(feature)] for feature in features], dtype=np.float32)
    ordered_embeddings = l2_normalize(ordered_embeddings)
    return features, ordered_embeddings


def map_matches_by_feature(matches: list[dict]) -> dict[str, dict]:
    return {f"{item.get('layer')}:{item.get('feature_id')}": item for item in matches}


def select_top_features(
    query_text: str,
    features: list[dict],
    feature_embeddings: np.ndarray,
    top_k: int = DEFAULT_TOP_FEATURES,
    preference_vec=None,
) -> list[dict]:
    print(f'[features] selecting top {top_k} features for query: {query_text[:60]}...', flush=True)
    query_vec = get_embeddings([query_text])
    # Personalised retrieval: fuse query vector with user preference vector
    if preference_vec is not None:
        try:
            import numpy as _np
            _alpha = 0.25
            _fused = (1.0 - _alpha) * query_vec[0] + _alpha * preference_vec
            _norm = _np.linalg.norm(_fused)
            if _norm > 1e-8:
                query_vec = _fused.reshape(1, -1) / _norm
                print(f'[features] preference fusion applied (alpha={_alpha})', flush=True)
        except Exception as _pref_err:
            print(f'[features] preference fusion failed: {_pref_err}', flush=True)
    scores = np.dot(feature_embeddings, query_vec[0])
    ranked_indices = np.argsort(scores)[::-1][:top_k]
    selected = []
    for idx in ranked_indices:
        feature = features[idx]
        selected.append(
            {
                "feature_id": feature.get("feature_id"),
                "layer": feature.get("layer"),
                "model_id": feature.get("model_id"),
                "source_keyword": feature.get("source_keyword"),
                "explanation": feature.get("explanation"),
                "similarity": float(scores[idx]),
                "feature_key": feature_key(feature),
            }
        )
    print(f'[features] top features: {[f["feature_key"] for f in selected]}', flush=True)
    return selected


def aggregate_verses(
    selected_features: list[dict],
    matches_by_feature: dict[str, dict],
    top_verses_per_language: int = DEFAULT_TOP_VERSES_PER_LANGUAGE,
    candidate_pool_per_language: int | None = None,
) -> dict[str, list[dict]]:
    print(f'[verses] aggregating verses from {len(selected_features)} features, top_per_lang={top_verses_per_language}', flush=True)
    aggregated = {"cuv": {}, "esv": {}}
    for feature in selected_features:
        feature_match = matches_by_feature.get(feature["feature_key"], {})
        for language in ("cuv", "esv"):
            for verse in feature_match.get("matches", {}).get(language, []):
                pk_id = verse.get("pk_id")
                if not pk_id:
                    continue
                verse_score = float(verse.get("score", 0.0))
                combined_score = 0.6 * feature["similarity"] + 0.4 * verse_score
                existing = aggregated[language].get(pk_id)
                feature_hit = {
                    "feature_id": feature.get("feature_id"),
                    "layer": feature.get("layer"),
                    "source_keyword": feature.get("source_keyword"),
                    "explanation": feature.get("explanation"),
                    "similarity": feature.get("similarity"),
                    "verse_score": verse_score,
                }
                if existing is None:
                    aggregated[language][pk_id] = {
                        "pk_id": pk_id,
                        "book_name": _display_book_name(language, verse.get("book_name") or ""),
                        "chapter": verse.get("chapter"),
                        "verse": verse.get("verse"),
                        "raw_text": verse.get("raw_text"),
                        "combined_score": combined_score,
                        "final_score": combined_score,
                        "best_feature_similarity": feature.get("similarity"),
                        "best_verse_score": verse_score,
                        "rerank_score": None,
                        "matched_features": [feature_hit],
                    }
                else:
                    existing["combined_score"] = max(existing["combined_score"], combined_score)
                    existing["final_score"] = existing["combined_score"]
                    existing["best_feature_similarity"] = max(existing["best_feature_similarity"], feature.get("similarity"))
                    existing["best_verse_score"] = max(existing["best_verse_score"], verse_score)
                    existing["matched_features"].append(feature_hit)

    # Build lookup index for cross-language verse pairing by (book_name, chapter, verse)
    def verse_location_key(v):
        return (_english_book_name(v.get("book_name") or ""), v.get("chapter"), v.get("verse"))

    def bible_lookup_key(target_language: str, v):
        english_book = _english_book_name(v.get("book_name") or "")
        book = _zh_book_name(english_book) if target_language == "cuv" else english_book
        return (book, v.get("chapter"), v.get("verse"))

    def counterpart_payload(v):
        if v is None:
            return None
        return {key: value for key, value in v.items() if key != "counterpart"}

    cuv_by_location = {verse_location_key(v): v for v in aggregated["cuv"].values()}
    esv_by_location = {verse_location_key(v): v for v in aggregated["esv"].values()}

    # Attach counterpart to each verse; if missing, look it up from bible CSV
    bible_index = _get_bible_index()
    for v in aggregated["cuv"].values():
        loc = verse_location_key(v)
        partner = esv_by_location.get(loc)
        if partner is None:
            csv_key = bible_lookup_key("esv", v)
            partner = bible_index["esv"].get(csv_key)
        v["counterpart"] = counterpart_payload(partner)

    for v in aggregated["esv"].values():
        loc = verse_location_key(v)
        partner = cuv_by_location.get(loc)
        if partner is None:
            csv_key = bible_lookup_key("cuv", v)
            partner = bible_index["cuv"].get(csv_key)
        v["counterpart"] = counterpart_payload(partner)

    final_output = {}
    for language, verses in aggregated.items():
        ranked = sorted(verses.values(), key=lambda item: item["combined_score"], reverse=True)
        limit = candidate_pool_per_language if candidate_pool_per_language is not None else top_verses_per_language
        final_output[language] = ranked[:limit]
        print(f'[verses] {language.upper()}: {len(final_output[language])} verses selected (pool limit={limit})', flush=True)
    return final_output


def build_verse_evidence(verse: dict) -> dict:
    """Build a compact explanation chain from retrieval signals already present."""
    matched = sorted(
        verse.get("matched_features") or [],
        key=lambda item: float(item.get("similarity") or 0.0),
        reverse=True,
    )
    top_features = []
    for item in matched[:3]:
        top_features.append(
            {
                "feature_key": f"{item.get('layer')}:{item.get('feature_id')}",
                "source_keyword": item.get("source_keyword"),
                "explanation": item.get("explanation"),
                "similarity": round(float(item.get("similarity") or 0.0), 4),
                "verse_score": round(float(item.get("verse_score") or 0.0), 4),
            }
        )

    final_score = float(verse.get("final_score") or verse.get("combined_score") or 0.0)
    best_feature_similarity = float(verse.get("best_feature_similarity") or 0.0)
    best_verse_score = float(verse.get("best_verse_score") or 0.0)
    uncertainty = []
    if final_score < 0.35:
        uncertainty.append("overall_score_low")
    if len(matched) <= 1:
        uncertainty.append("single_feature_match")
    if verse.get("rerank_score") is None:
        uncertainty.append("not_reranked")

    return {
        "method": "dense_feature_to_verse_aggregation",
        "top_features": top_features,
        "signals": {
            "final_score": round(final_score, 4),
            "combined_score": round(float(verse.get("combined_score") or 0.0), 4),
            "best_feature_similarity": round(best_feature_similarity, 4),
            "best_verse_score": round(best_verse_score, 4),
            "rerank_score": verse.get("rerank_score"),
        },
        "uncertainty": uncertainty,
        "summary": (
            "This verse was surfaced because its exemplar match overlaps with the selected emotion features. "
            "Use it as a reflective lead, not as a definitive interpretation."
        ),
    }


def attach_evidence_chains(verse_summary: dict[str, list[dict]]) -> dict[str, list[dict]]:
    for verses in verse_summary.values():
        for verse in verses:
            verse["evidence_chain"] = build_verse_evidence(verse)
    return verse_summary


def rerank_verses(
    query_text: str,
    verses: list[dict],
    top_n: int,
    rerank_weight: float = DEFAULT_RERANK_WEIGHT,
) -> tuple[list[dict], str | None]:
    """Returns (reranked_verses, error_message_or_None)."""
    print(f'[rerank] cross-encoder reranking {len(verses)} verses, top_n={top_n}, weight={rerank_weight}', flush=True)
    if not verses:
        return [], None
    try:
        reranker = get_reranker()
    except RuntimeError as exc:
        print(f'[rerank] reranker load failed, falling back to combined_score: {exc}', flush=True)
        sorted_verses = sorted(verses, key=lambda v: v.get("combined_score", 0.0), reverse=True)
        return sorted_verses[:top_n], str(exc)
    clipped_weight = min(max(rerank_weight, 0.0), 1.0)
    sentence_pairs = [(query_text, str(item.get("raw_text", ""))) for item in verses]
    try:
        rerank_scores = reranker.predict(sentence_pairs)
    except Exception as exc:
        sorted_verses = sorted(verses, key=lambda v: v.get("combined_score", 0.0), reverse=True)
        return sorted_verses[:top_n], f"Reranker predict failed: {exc}"
    reranked = []
    for verse, raw_score in zip(verses, rerank_scores, strict=True):
        normalized_rerank_score = sigmoid(float(raw_score))
        fused_score = (1.0 - clipped_weight) * float(verse.get("combined_score", 0.0)) + clipped_weight * normalized_rerank_score
        reranked_item = dict(verse)
        reranked_item["rerank_score"] = round(normalized_rerank_score, 4)
        reranked_item["final_score"] = round(fused_score, 4)
        reranked.append(reranked_item)
    reranked.sort(key=lambda item: item["final_score"], reverse=True)
    print(f'[rerank] cross-encoder done: top verse final_score={reranked[0]["final_score"] if reranked else "n/a"}', flush=True)
    return reranked[:top_n], None


LLM_RERANK_SYSTEM_PROMPT = """你是一位深谙圣经与属灵情感的牧者。
给定一段情绪或处境描述，以及若干圣经经文候选，请根据经文在属灵上对该处境的**安慰、光照、回应**程度，从高到低排序。
【CRITICAL】你只允许输出合法的 JSON 数组。不要 markdown 代码块、不要任何解释文字、不要任何前后缀。输出的第一个字符必须是 [，最后一个字符必须是 ]。
只返回排序后的经文编号（整数），不要附带任何说明。
示例输出：[3, 1, 5, 2, 4]"""


def llm_rerank_verses(
    query_text: str,
    verses: list[dict],
    top_n: int,
) -> tuple[list[dict], str | None]:
    """Use LLM to rerank verses by spiritual relevance. Gemini primary, SiliconFlow fallback."""
    if not verses:
        return [], None
    numbered = "\n".join(
        f"{i + 1}. [{v.get('book_name')} {v.get('chapter')}:{v.get('verse')}] {v.get('raw_text', '')}"
        for i, v in enumerate(verses)
    )
    user_msg = f"处境描述：{query_text}\n\n候选经文：\n{numbered}"
    # Build provider list: Gemini primary, SiliconFlow fallback（429 冷却期内跳过 Gemini）
    providers = []
    if GEMINI_API_CHAT_KEY and _gemini_in_cooldown():
        print('[llm] Gemini 跳过(429 冷却中)，直接用 SiliconFlow', flush=True)
    elif GEMINI_API_CHAT_KEY:
        providers.append((GEMINI_CHAT_URL, {
            "Authorization": f"Bearer {GEMINI_API_CHAT_KEY}",
            "Content-Type": "application/json",
        }, GEMINI_CHAT_MODEL, "Gemini"))
    if DEEPSEEK_API_KEY:
        providers.append((DEEPSEEK_CHAT_URL, {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }, DEEPSEEK_CHAT_MODEL, "DeepSeek"))
    if SILICONFLOW_API_KEY:
        providers.append((SILICONFLOW_CHAT_URL, siliconflow_headers(), SILICONFLOW_CHAT_MODEL, "SiliconFlow"))
    last_exc: Exception | None = None
    for url, headers, model, provider in providers:
        print(f'[rerank] LLM reranking {len(verses)} verses via {provider}/{model}', flush=True)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": LLM_RERANK_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.1,
            "max_tokens": 128,
        }
        try:
            data = post_with_retry(url, payload, headers, max_retries=2)
            raw = data["choices"][0]["message"]["content"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            order: list[int] = json.loads(raw)
            seen: set[int] = set()
            reranked: list[dict] = []
            for rank, idx in enumerate(order):
                real_idx = int(idx) - 1
                if 0 <= real_idx < len(verses) and real_idx not in seen:
                    item = dict(verses[real_idx])
                    item["rerank_score"] = round(1.0 - rank / max(len(order), 1), 4)
                    item["final_score"] = item["rerank_score"]
                    reranked.append(item)
                    seen.add(real_idx)
            for i, v in enumerate(verses):
                if i not in seen:
                    item = dict(v)
                    item["rerank_score"] = 0.0
                    item["final_score"] = round(float(v.get("combined_score", 0.0)), 4)
                    reranked.append(item)
            print(f'[rerank] ok via {provider}', flush=True)
            return reranked[:top_n], None
        except Exception as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            print(f'[rerank] {provider} failed status={status}: {exc}, trying next provider...', flush=True)
            last_exc = exc
            continue
    print(f'[rerank] all providers failed, falling back to combined_score', flush=True)
    fallback = sorted(verses, key=lambda v: v.get("combined_score", 0.0), reverse=True)
    return fallback[:top_n], f"LLM rerank failed: {last_exc}"


# ---------------------------------------------------------------------------
# TTL-aware LRU cache (used for both LLM responses and verse query results)
# ---------------------------------------------------------------------------
_VERSE_CACHE_TTL_SECS = int(os.getenv("VERSE_CACHE_TTL", "300"))  # 5 min default
_LLM_CACHE_TTL_SECS   = int(os.getenv("LLM_CACHE_TTL",   "600"))  # 10 min default


class _TTLCache:
    """Thread-safe LRU + TTL cache.

    Entries expire after ``ttl_seconds`` regardless of access frequency.
    When full, the least-recently-used entry is evicted first.
    """

    def __init__(self, max_size: int = 256, ttl_seconds: int = 300):
        import collections
        import threading
        self._store: "collections.OrderedDict[str, tuple]" = collections.OrderedDict()
        self._max = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            if key not in self._store:
                return None
            value, exp = self._store[key]
            if time.monotonic() > exp:
                del self._store[key]
                return None
            # Move to end (most-recently used)
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            elif len(self._store) >= self._max:
                self._store.popitem(last=False)  # evict LRU
            self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            live = sum(1 for _, (_, exp) in self._store.items() if exp > now)
            return {"size": len(self._store), "live_entries": live, "max_size": self._max, "ttl_seconds": self._ttl}


llm_cache   = _TTLCache(max_size=256, ttl_seconds=_LLM_CACHE_TTL_SECS)
verse_cache = _TTLCache(max_size=512, ttl_seconds=_VERSE_CACHE_TTL_SECS)


def _cache_key(system_prompt: str, user_message: str, max_tokens: int) -> str:
    """Generate cache key from prompt parameters."""
    import hashlib
    content = f"{system_prompt[:100]}|{user_message[:100]}|{max_tokens}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def _verse_cache_key(query_text: str, user_id: str = "", top_k: int = 5, enable_mmr: bool = True) -> str:
    """Stable cache key for verse query results.

    Incorporates query text, user context, and retrieval parameters so that
    different users or settings always get independent cache entries.
    """
    import hashlib
    content = f"{query_text.strip()}|{user_id}|{top_k}|{int(enable_mmr)}"
    return "verse:" + hashlib.sha1(content.encode()).hexdigest()[:20]

def call_chat(system_prompt: str, user_message: str) -> str:
    cache_key = _cache_key(system_prompt, user_message, 600)
    cached = llm_cache.get(cache_key)
    if cached:
        return cached
    # Build provider list: Gemini primary, SiliconFlow fallback（429 冷却期内跳过 Gemini）
    providers = []
    if GEMINI_API_CHAT_KEY and _gemini_in_cooldown():
        print('[llm] Gemini 跳过(429 冷却中)，直接用 SiliconFlow', flush=True)
    elif GEMINI_API_CHAT_KEY:
        providers.append((GEMINI_CHAT_URL, {
            "Authorization": f"Bearer {GEMINI_API_CHAT_KEY}",
            "Content-Type": "application/json",
        }, GEMINI_CHAT_MODEL, "Gemini"))
    if DEEPSEEK_API_KEY:
        providers.append((DEEPSEEK_CHAT_URL, {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }, DEEPSEEK_CHAT_MODEL, "DeepSeek"))
    if SILICONFLOW_API_KEY:
        providers.append((SILICONFLOW_CHAT_URL, siliconflow_headers(), SILICONFLOW_CHAT_MODEL, "SiliconFlow"))
    for url, headers, model, provider in providers:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 600,
        }
        try:
            data = post_with_retry(url, payload, headers, max_retries=2)
            result = data["choices"][0]["message"]["content"].strip()
            print(f'[call_chat] ok via {provider}', flush=True)
            llm_cache.set(cache_key, result)
            return result
        except Exception as e:
            status = getattr(getattr(e, 'response', None), 'status_code', None)
            print(f'[call_chat] {provider} failed status={status}: {type(e).__name__}: {str(e)[:120]}', flush=True)
            continue
    print('[call_chat] all providers failed, returning empty', flush=True)
    return "{}"


def assess_psychological_state(query_text: str, language: str = "zh") -> dict:
    print(f'[guidance] assess_psychological_state query={query_text[:60]}...', flush=True)
    wants_en = str(language or "").lower().startswith("en")
    system_prompt = PSYCHOLOGICAL_SYSTEM_PROMPT_EN if wants_en else PSYCHOLOGICAL_SYSTEM_PROMPT
    cache_key = _cache_key(system_prompt, query_text, 400)
    cached = llm_cache.get(cache_key)
    if cached:
        print('[guidance] cache hit, returning cached result', flush=True)
        return cached
    try:
        raw_content = _call_llm_with_fallback(
            system_prompt=system_prompt,
            user_message=query_text,
            max_tokens=1200,
            temperature=0.7,
            tag="guidance",
        )
    except Exception as e:
        print(f'[guidance] all providers failed: {e}', flush=True)
        if wants_en:
            return {
                "core_emotions": ["anxiety", "restless longing"],
                "psychological_assessment": "The struggle you describe is real, and it is not hidden from God. He meets restless hearts with patient mercy rather than rejection.",
                "coping_suggestions": ["You can breathe slowly and pray a short surrender prayer.", "You can bring this need to a trusted believer for prayer."],
                "spiritual_guidance": "God is our refuge and strength, a very present help in trouble. Your need is not too small for His care or too tangled for His grace. In Christ, you are invited to come near without pretending to be strong.",
                "core_need": "Your soul's deepest longing right now is to rest in God's presence and receive His steady love.",
                "service_error": str(e)[:80],
            }
        return {"core_emotions":["焦虑","不安"],"psychological_assessment":"AI服务暂时不可用，请稍后重试。","coping_suggestions":["深呼吸并安静片刻","向神祷告交托","与朋友分享感受"],"spiritual_guidance":"神是我们的避难所和力量","core_need":"安全感与神的同在","service_error":str(e)[:80]}
    raw = _strip_markdown_json(raw_content)
    try:
        result = json.loads(raw)
        llm_cache.set(cache_key, result)
        print(f'[guidance] ok emotions={result.get("core_emotions", [])}', flush=True)
        return result
    except json.JSONDecodeError:
        print(f'[guidance] JSON parse error, returning raw text', flush=True)
        return {"core_emotions":[],"psychological_assessment":raw,"coping_suggestions":[],"spiritual_guidance":"","core_need":"","parse_error":True}


def query_emotion_verses(
    query_text: str,
    top_features: int = DEFAULT_TOP_FEATURES,
    top_verses_per_language: int = DEFAULT_TOP_VERSES_PER_LANGUAGE,
    features_file: str = FEATURES_FILE,
    matches_file: str = MATCHES_FILE,
    cache_file: str = EMBEDDING_CACHE_FILE,
    include_guidance: bool = False,
    enable_rerank: bool = DEFAULT_ENABLE_RERANK,
    rerank_candidates: int = DEFAULT_RERANK_CANDIDATES,
    rerank_weight: float = DEFAULT_RERANK_WEIGHT,
    rerank_mode: str = "cross_encoder",
    preference_vec=None,
    enable_mmr: bool = True,
    mmr_lambda: float = DEFAULT_MMR_LAMBDA,
    mmr_candidates: int = 0,
) -> dict:
    """rerank_mode: 'llm' | 'cross_encoder' | 'none'

    MMR post-processing (default enabled):
      enable_mmr   – apply Maximal Marginal Relevance after rerank
      mmr_lambda   – lambda parameter (0.5 = balanced; 1.0 = relevance-only)
      mmr_candidates – extra candidates fetched for MMR pool (0 = use rerank_candidates)
    """
    # Fast path: return cached result if available
    _user_id_key = str(id(preference_vec)) if preference_vec is not None else "anon"
    _vcache_key = _verse_cache_key(query_text, user_id=_user_id_key, top_k=top_verses_per_language, enable_mmr=enable_mmr)
    _cached = verse_cache.get(_vcache_key)
    if _cached is not None:
        print(f'[query_emotion_verses] cache HIT key={_vcache_key}', flush=True)
        _cached["_cache"] = "HIT"
        return _cached

    print(
        f'[query_emotion_verses] start: query={query_text[:60]}... '
        f'top_features={top_features} top_verses={top_verses_per_language} '
        f'rerank={enable_rerank}/{rerank_mode} mmr={enable_mmr}',
        flush=True,
    )
    t_total = time.perf_counter()
    features, feature_embeddings, matches_by_feature = _ensure_loaded(features_file, matches_file, cache_file)
    selected_features = select_top_features(query_text, features, feature_embeddings, top_k=top_features, preference_vec=preference_vec)
    use_rerank = enable_rerank and rerank_mode != "none"
    # Pool size: largest of rerank_candidates, mmr_candidates, and the final top_k
    pool_size = max(top_verses_per_language, rerank_candidates, mmr_candidates or 0)
    verse_summary = aggregate_verses(
        selected_features,
        matches_by_feature,
        top_verses_per_language=top_verses_per_language,
        candidate_pool_per_language=pool_size if (use_rerank or enable_mmr) else None,
    )
    rerank_applied = False
    rerank_error: str | None = None
    if use_rerank:
        reranked_summary = {}
        for language, verses in verse_summary.items():
            if rerank_mode == "llm":
                reranked, err = llm_rerank_verses(
                    query_text=query_text,
                    verses=verses,
                    top_n=top_verses_per_language,
                )
            else:
                reranked, err = rerank_verses(
                    query_text=query_text,
                    verses=verses,
                    top_n=top_verses_per_language,
                    rerank_weight=rerank_weight,
                )
            reranked_summary[language] = reranked
            if err and rerank_error is None:
                rerank_error = err
        verse_summary = reranked_summary
        rerank_applied = rerank_error is None
    # MMR diversity post-processing
    mmr_applied = False
    if enable_mmr and top_verses_per_language > 1:
        try:
            mmr_summary = {}
            for language, verses in verse_summary.items():
                mmr_summary[language] = mmr_rerank(
                    query_text=query_text,
                    verses=verses,
                    top_n=top_verses_per_language,
                    lambda_=mmr_lambda,
                )
            verse_summary = mmr_summary
            mmr_applied = True
        except Exception as _mmr_err:
            print(f'[mmr] failed, skipping: {_mmr_err}', flush=True)
    verse_summary = attach_evidence_chains(verse_summary)
    active_model = (
        LLM_RERANK_MODEL if rerank_mode == "llm"
        else RERANK_MODEL_NAME if rerank_mode == "cross_encoder"
        else None
    )
    result = {
        "query_text": query_text,
        "selected_emotions": selected_features,
        "verse_summary": verse_summary,
        "rerank": {
            "enabled": use_rerank,
            "mode": rerank_mode,
            "applied": rerank_applied,
            "model": active_model if use_rerank else None,
            "candidate_pool_per_language": pool_size if (use_rerank or enable_mmr) else None,
            "weight": rerank_weight if rerank_mode == "cross_encoder" and use_rerank else None,
            "error": rerank_error,
        },
        "mmr": {
            "enabled": enable_mmr,
            "applied": mmr_applied,
            "lambda": mmr_lambda,
        },
    }
    if include_guidance:
        result["guidance"] = assess_psychological_state(query_text)
    _elapsed_ms = round((time.perf_counter()-t_total)*1000)
    print(
        f'[query_emotion_verses] done: total={_elapsed_ms}ms '
        f'rerank_applied={rerank_applied} mmr_applied={mmr_applied}',
        flush=True,
    )
    result["_cache"] = "MISS"
    result["_latency_ms"] = _elapsed_ms
    verse_cache.set(_vcache_key, result)
    return result


def result_to_markdown(result: dict) -> str:
    lines = []
    lines.append("# Emotion Query Result")
    lines.append("")
    lines.append(f"**Query**: {result.get('query_text', '')}")
    lines.append("")
    lines.append("## Matched Emotion Features")
    lines.append("")
    for idx, feature in enumerate(result.get("selected_emotions", []), start=1):
        lines.append(
            f"- **{idx}. {feature.get('layer')}:{feature.get('feature_id')}** | "
            f"keyword=`{feature.get('source_keyword')}` | similarity={feature.get('similarity', 0.0):.4f}"
        )
        lines.append(f"  - {feature.get('explanation', '')}")
    for language in ("cuv", "esv"):
        verses = result.get("verse_summary", {}).get(language, [])
        lines.append("")
        lines.append(f"## {language.upper()} Verses")
        lines.append("")
        for idx, verse in enumerate(verses, start=1):
            lines.append(
                f"- **{idx}. {verse.get('pk_id')}** | score={verse.get('combined_score', 0.0):.4f} | "
                f"{verse.get('book_name')} {verse.get('chapter')}:{verse.get('verse')}"
            )
            lines.append(f"  - {verse.get('raw_text', '')}")
    lines.append("")
    return "\n".join(lines)


def result_to_rows(result: dict) -> list[dict]:
    feature_lookup = {
        item["feature_key"]: item for item in result.get("selected_emotions", [])
    }
    rows = []
    for language, verses in result.get("verse_summary", {}).items():
        for rank, verse in enumerate(verses, start=1):
            matched_features = verse.get("matched_features", [])
            matched_feature_keys = []
            matched_feature_explanations = []
            for feature_hit in matched_features:
                feature_key_value = f"{feature_hit.get('layer')}:{feature_hit.get('feature_id')}"
                matched_feature_keys.append(feature_key_value)
                matched_feature_explanations.append(
                    feature_lookup.get(feature_key_value, {}).get("explanation", "")
                )
            rows.append(
                {
                    "query_text": result.get("query_text", ""),
                    "language": language,
                    "rank": rank,
                    "pk_id": verse.get("pk_id"),
                    "book_name": _zh_book_name(verse.get("book_name") or ""),
                    "chapter": verse.get("chapter"),
                    "verse": verse.get("verse"),
                    "combined_score": verse.get("combined_score"),
                    "final_score": verse.get("final_score"),
                    "rerank_score": verse.get("rerank_score"),
                    "best_feature_similarity": verse.get("best_feature_similarity"),
                    "best_verse_score": verse.get("best_verse_score"),
                    "raw_text": verse.get("raw_text"),
                    "matched_feature_keys": " | ".join(matched_feature_keys),
                    "matched_feature_explanations": " | ".join(matched_feature_explanations),
                }
            )
    return rows


def export_result_files(result: dict, output_dir: str = DEFAULT_OUTPUT_DIR, slug: str | None = None) -> dict:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if slug is None:
        slug = str(int(time.time()))

    json_path = output_path / f"emotion_query_{slug}.json"
    markdown_path = output_path / f"emotion_query_{slug}.md"
    csv_path = output_path / f"emotion_query_{slug}.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(result_to_markdown(result))

    rows = result_to_rows(result)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "query_text", "language", "rank", "pk_id", "book_name", "chapter", "verse",
            "combined_score", "final_score", "rerank_score", "best_feature_similarity", "best_verse_score", "raw_text",
            "matched_feature_keys", "matched_feature_explanations",
        ])
        writer.writeheader()
        if rows:
            writer.writerows(rows)

    return {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "csv": str(csv_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Natural language -> emotion features -> verse summary")
    parser.add_argument("query", nargs="?", help="自然语言查询文本")
    parser.add_argument("--query-file", help="从文本文件读取查询")
    parser.add_argument("--top-features", type=int, default=DEFAULT_TOP_FEATURES)
    parser.add_argument("--top-verses", type=int, default=DEFAULT_TOP_VERSES_PER_LANGUAGE)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--slug", default=None)
    parser.add_argument("--export", action="store_true", help="导出 JSON/Markdown/CSV")
    parser.add_argument("--markdown", action="store_true", help="在终端输出 Markdown")
    parser.add_argument("--json", action="store_true", help="在终端输出 JSON")
    parser.add_argument("--guidance", action="store_true", help="调用 LLM 生成心理状态评估与灵性指导")
    parser.add_argument("--enable-rerank", action="store_true", help="启用轻量 rerank 精排")
    parser.add_argument("--rerank-candidates", type=int, default=DEFAULT_RERANK_CANDIDATES)
    parser.add_argument("--rerank-weight", type=float, default=DEFAULT_RERANK_WEIGHT)
    return parser.parse_args()


def resolve_query_text(args: argparse.Namespace) -> str:
    if args.query_file:
        return Path(args.query_file).read_text(encoding="utf-8").strip()
    if args.query:
        return args.query.strip()
    raise ValueError("请提供 query 参数或 --query-file")


def main() -> None:
    args = parse_args()
    query = resolve_query_text(args)
    result = query_emotion_verses(
        query_text=query,
        top_features=args.top_features,
        top_verses_per_language=args.top_verses,
        include_guidance=args.guidance,
        enable_rerank=args.enable_rerank,
        rerank_candidates=args.rerank_candidates,
        rerank_weight=args.rerank_weight,
    )

    if args.export:
        paths = export_result_files(result, output_dir=args.output_dir, slug=args.slug)
        print(json.dumps({"exported": paths}, ensure_ascii=False, indent=2))

    if args.markdown:
        print(result_to_markdown(result))
    elif args.json or not args.export:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
