"""
engine_i18n.py — 扩充引擎的服务端英文本地化层（lang=en 时把中文输出译成英文）

设计：
  · 递归遍历引擎返回的结果字典/列表，收集所有含中文的字符串；
  · 经文引用（如「弗4:26」「撒上18:8-9」）用确定性的 66 卷中英对照表转换为「Eph 4:26」「1 Sam 18:8-9」；
  · 其余中文用 LLM 按「保留语气、经文用 ESV、不增删内容」的受控提示批量翻译，一次请求译完整个结果；
  · 进程内缓存（zh→en）：固定的祷告脚手架/标签会大量复用，命中即免翻；
  · 任何失败（无 LLM / 网络 / 解析错误）→ 原样返回中文，永不报错、永不破坏结构。

对外：
  localize(result, lang, settings=None)  → dict（en 时英文，其它原样）
  localize_meta(meta, lang, settings=None)
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set

_CJK = re.compile(r"[㐀-鿿]")
# 进程内缓存：中文 → 英文
_CACHE: Dict[str, str] = {}

# 不参与翻译的键（布尔/内部标志/分类 key 等）
_SKIP_KEYS = {"ai_used", "crisis", "lang", "en_localized", "key", "en"}

# CUV 中文书卷缩写 → ESV 式英文缩写（66 卷）
BOOKS = {
    "创": "Gen", "出": "Exod", "利": "Lev", "民": "Num", "申": "Deut", "书": "Josh", "士": "Judg",
    "得": "Ruth", "撒上": "1 Sam", "撒下": "2 Sam", "王上": "1 Kgs", "王下": "2 Kgs",
    "代上": "1 Chr", "代下": "2 Chr", "拉": "Ezra", "尼": "Neh", "斯": "Esth", "伯": "Job",
    "诗": "Ps", "箴": "Prov", "传": "Eccl", "歌": "Song", "赛": "Isa", "耶": "Jer", "哀": "Lam",
    "结": "Ezek", "但": "Dan", "何": "Hos", "珥": "Joel", "摩": "Amos", "俄": "Obad", "拿": "Jonah",
    "弥": "Mic", "鸿": "Nah", "哈": "Hab", "番": "Zeph", "该": "Hag", "亚": "Zech", "玛": "Mal",
    "太": "Matt", "可": "Mark", "路": "Luke", "约": "John", "徒": "Acts", "罗": "Rom",
    "林前": "1 Cor", "林后": "2 Cor", "加": "Gal", "弗": "Eph", "腓": "Phil", "西": "Col",
    "帖前": "1 Thess", "帖后": "2 Thess", "提前": "1 Tim", "提后": "2 Tim", "多": "Titus",
    "门": "Phlm", "来": "Heb", "雅": "Jas", "彼前": "1 Pet", "彼后": "2 Pet",
    "约壹": "1 John", "约贰": "2 John", "约叁": "3 John", "犹": "Jude", "启": "Rev",
}
# 多字书卷优先匹配（撒上/撒下/王上/林前/约壹…）
_BOOK_KEYS = sorted(BOOKS.keys(), key=len, reverse=True)


def _has_cjk(s: str) -> bool:
    return bool(_CJK.search(s))


def is_reference(s: str) -> bool:
    """判断是否是一处经文引用（书卷缩写 + 章节），如「弗4:26」「撒上18:8-9」「诗119:103」。"""
    s = (s or "").strip()
    for b in _BOOK_KEYS:
        if s.startswith(b):
            rest = s[len(b):]
            return bool(re.fullmatch(r"[\d：:，,、\-—～~;；\s]+", rest)) and any(c.isdigit() for c in rest)
    return False


def convert_reference(ref: str) -> str:
    """「弗4:26」→「Eph 4:26」；不认识则原样返回。"""
    s = (ref or "").strip()
    for b in _BOOK_KEYS:
        if s.startswith(b):
            rest = s[len(b):].replace("：", ":").replace("，", ", ").replace("、", ", ").replace("—", "-").replace("～", "-").replace("~", "-")
            return f"{BOOKS[b]} {rest.strip()}"
    return ref


def _collect(obj: Any, out: Set[str]) -> None:
    if isinstance(obj, str):
        if _has_cjk(obj) and not is_reference(obj):
            out.add(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in _SKIP_KEYS:
                continue
            _collect(v, out)
    elif isinstance(obj, (list, tuple)):
        for it in obj:
            _collect(it, out)


def _apply(obj: Any, mapping: Dict[str, str]) -> Any:
    if isinstance(obj, str):
        if is_reference(obj):
            return convert_reference(obj)
        return mapping.get(obj, obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "ref" and isinstance(v, str):
                out[k] = convert_reference(v)
            elif k in _SKIP_KEYS:
                out[k] = v
            else:
                out[k] = _apply(v, mapping)
        return out
    if isinstance(obj, list):
        return [_apply(it, mapping) for it in obj]
    if isinstance(obj, tuple):
        return tuple(_apply(it, mapping) for it in obj)
    return obj


def _build_prompt(items: List[str]) -> str:
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(items))
    return (
        "You are a professional translator of Christian devotional and theological content. "
        "Translate each numbered Chinese string into natural, warm, pastoral English. Rules:\n"
        "- Preserve tone and meaning exactly; do NOT add, remove, summarize, or explain.\n"
        "- For any Bible quotation, render it in ESV wording.\n"
        "- Keep author/book names in their standard English (e.g. 傅格森=Ferguson, 巴刻=Packer, "
        "钟马田=Lloyd-Jones, 司布真=Spurgeon, 潘霍华=Bonhoeffer, 卢云=Nouwen, 慕安得烈=Andrew Murray, "
        "斯托得=Stott, 华森=Thomas Watson, 傅拉维=John Flavel, 沃弗=Volf, 里夫斯=Reeves, 派博=Piper, "
        "魏乐德=Dallas Willard, 倪柝声=Watchman Nee).\n"
        "- Keep it concise and readable; keep any punctuation/emoji that carries meaning.\n"
        "- Return ONLY a JSON array of strings, same length and order as the input, no keys, no commentary.\n\n"
        f"Input ({len(items)} strings):\n{numbered}\n"
    )


def _call_ai(prompt: str, settings: Any) -> Optional[str]:
    for modname, fn in (("waiting_engine", "call_ai_provider"), ("llm_provider", "call_llm")):
        try:
            mod = __import__(modname)
            f = getattr(mod, fn, None)
            if f:
                out = f(prompt) if settings is None else f(prompt, settings=settings)
                if out:
                    return out if isinstance(out, str) else str(out)
        except Exception:
            continue
    return None


def _llm_translate(items: List[str], settings: Any) -> Optional[Dict[str, str]]:
    if not items:
        return {}
    raw = _call_ai(_build_prompt(items), settings)
    if not raw:
        return None
    try:
        m = re.search(r"\[.*\]", raw, re.S)
        arr = json.loads(m.group(0) if m else raw)
        if isinstance(arr, list) and len(arr) == len(items):
            return {zh: str(en) for zh, en in zip(items, arr) if en}
    except Exception:
        return None
    return None


def localize(result: Dict[str, Any], lang: Optional[str], settings: Any = None) -> Dict[str, Any]:
    """lang=en 时把 result 里的中文译成英文（经文引用走确定性映射）；其它/失败原样返回中文。"""
    if not isinstance(result, dict):
        return result
    if not lang or str(lang).lower().startswith("zh"):
        return result

    strings: Set[str] = set()
    _collect(result, strings)
    todo = [s for s in strings if s not in _CACHE]
    if todo:
        translated = _llm_translate(todo, settings)
        if translated:
            _CACHE.update(translated)
        # 未能翻译的：留空表示回退（保持中文），不写缓存
    mapping = {s: _CACHE[s] for s in strings if s in _CACHE}

    out = _apply(result, mapping)
    out["lang"] = "en"
    # 是否真的完成了英文化（全部中文串都命中缓存）
    out["en_localized"] = all(s in _CACHE for s in strings) if strings else True
    return out


def localize_meta(meta: Dict[str, Any], lang: Optional[str], settings: Any = None) -> Dict[str, Any]:
    return localize(meta, lang, settings)
