"""
Extract scripture texts from cuv_bible.csv for all refs used in mirrorData.js
Outputs: emotion-sphere-ui/public/verseCache.json
"""
import csv, json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Book name map: Chinese abbrev → English book name in CSV ──────────────
BOOK_MAP = {
    '创':'Genesis','出':'Exodus','利':'Leviticus','民':'Numbers','申':'Deuteronomy',
    '书':'Joshua','士':'Judges','得':'Ruth','撒上':'1 Samuel','撒下':'2 Samuel',
    '王上':'1 Kings','王下':'2 Kings','代上':'1 Chronicles','代下':'2 Chronicles',
    '拉':'Ezra','尼':'Nehemiah','斯':'Esther','伯':'Job','诗':'Psalms','箴':'Proverbs',
    '传':'Ecclesiastes','歌':'Song of Solomon','赛':'Isaiah','耶':'Jeremiah',
    '哀':'Lamentations','结':'Ezekiel','但':'Daniel','何':'Hosea','珥':'Joel',
    '摩':'Amos','俄':'Obadiah','拿':'Jonah','弥':'Micah','鸿':'Nahum','哈':'Habakkuk',
    '番':'Zephaniah','该':'Haggai','亚':'Zechariah','玛':'Malachi',
    '太':'Matthew','可':'Mark','路':'Luke','约':'John','徒':'Acts','罗':'Romans',
    '林前':'1 Corinthians','林后':'2 Corinthians','加':'Galatians','弗':'Ephesians',
    '腓':'Philippians','西':'Colossians','帖前':'1 Thessalonians','帖后':'2 Thessalonians',
    '提前':'1 Timothy','提后':'2 Timothy','多':'Titus','门':'Philemon',
    '来':'Hebrews','雅':'James','彼前':'1 Peter','彼后':'2 Peter',
    '约一':'1 John','约二':'2 John','约三':'3 John','犹':'Jude','启':'Revelation',
    # Alternate spellings / full book names seen in data
    '腓利门书':'Philemon',
    '约伯记':'Job','创世记':'Genesis','出埃及记':'Exodus','利未记':'Leviticus',
    '民数记':'Numbers','申命记':'Deuteronomy','约书亚记':'Joshua','士师记':'Judges',
    '路得记':'Ruth','历代志上':'1 Chronicles','历代志下':'2 Chronicles',
    '以斯拉记':'Ezra','尼希米记':'Nehemiah','以斯帖记':'Esther','诗篇':'Psalms',
    '箴言':'Proverbs','传道书':'Ecclesiastes','雅歌':'Song of Solomon',
    '以赛亚书':'Isaiah','耶利米书':'Jeremiah','耶利米哀歌':'Lamentations',
    '以西结书':'Ezekiel','但以理书':'Daniel','何西阿书':'Hosea','约珥书':'Joel',
    '阿摩司书':'Amos','俄巴底亚书':'Obadiah','约拿书':'Jonah','弥迦书':'Micah',
    '那鸿书':'Nahum','哈巴谷书':'Habakkuk','西番雅书':'Zephaniah','哈该书':'Haggai',
    '撒迦利亚书':'Zechariah','玛拉基书':'Malachi',
    '马太福音':'Matthew','马可福音':'Mark','路加福音':'Luke','约翰福音':'John',
    '使徒行传':'Acts','罗马书':'Romans','哥林多前书':'1 Corinthians',
    '哥林多后书':'2 Corinthians','加拉太书':'Galatians','以弗所书':'Ephesians',
    '腓立比书':'Philippians','歌罗西书':'Colossians','帖撒罗尼迦前书':'1 Thessalonians',
    '帖撒罗尼迦后书':'2 Thessalonians','提摩太前书':'1 Timothy','提摩太后书':'2 Timothy',
    '提多书':'Titus','希伯来书':'Hebrews','雅各书':'James','彼得前书':'1 Peter',
    '彼得后书':'2 Peter','约翰一书':'1 John','约翰二书':'2 John','约翰三书':'3 John',
    '犹大书':'Jude','启示录':'Revelation',
}

def clean_text(t: str) -> str:
    """Remove CUV word-spacing and ideographic spaces."""
    return t.replace('\u3000', '').replace(' ', '').strip()

# ── Load CSV into lookup: (book_en, chapter, verse) → text ───────────────
print("Loading CSV...", end=' ', flush=True)
verse_db: dict[tuple, str] = {}
book_chapters: dict[str, list[str]] = {}  # book_en → sorted chapter list
with open(ROOT / 'bible/cuv_bible.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        key = (row['book'], row['chapter'], row['verse'])
        verse_db[key] = clean_text(row['text'])
        book_chapters.setdefault(row['book'], [])
        if row['chapter'] not in book_chapters[row['book']]:
            book_chapters[row['book']].append(row['chapter'])
print(f"{len(verse_db):,} verses loaded")

def get_verses(book_en: str, chapter: str, v_start: str, v_end: str | None) -> str:
    """Return concatenated verse text for a range."""
    texts = []
    if v_end:
        for v in range(int(v_start), int(v_end) + 1):
            t = verse_db.get((book_en, chapter, str(v)))
            if t:
                texts.append(f"{v}节 {t}")
    else:
        t = verse_db.get((book_en, chapter, v_start))
        if t:
            texts.append(t)
    return ''.join(texts)

def get_chapter_preview(book_en: str, chapter: str, label: str = '') -> str:
    """Return first 3 verses of a chapter as preview."""
    texts = []
    for v in range(1, 4):
        t = verse_db.get((book_en, chapter, str(v)))
        if t:
            texts.append(t)
    prefix = f'[{label}] ' if label else ''
    return prefix + ''.join(texts) + ('……' if texts else '')

def get_chapter_range_preview(book_en: str, ch_start: int, ch_end: int, ref_label: str) -> str:
    """Return first 3 verses of each chapter in range (max 3 chapters shown)."""
    parts = []
    for ch in range(ch_start, min(ch_end + 1, ch_start + 3)):
        texts = []
        for v in range(1, 4):
            t = verse_db.get((book_en, str(ch), str(v)))
            if t:
                texts.append(t)
        if texts:
            parts.append(f'第{ch}章：' + ''.join(texts))
    if not parts:
        return ''
    suffix = f'……（共{ch_end - ch_start + 1}章）' if ch_end > ch_start + 2 else '……'
    return '\n'.join(parts) + suffix

# ── Parse a ref string ────────────────────────────────────────────────────
# Supported patterns:
#   创1:1            single verse
#   创1:1-3          verse range
#   创1              single chapter
#   代下17-20        chapter range (same book)
#   王上17-王下2      cross-book chapter range
#   太20，可10       compound comma (take each part)
#   太4，约13-21，徒2 compound multi-part
#   腓利门书10-11    alternate book name with verse range
#   约伯记           full book name only → chapter 1 preview

SINGLE_VERSE_RE = re.compile(r'^([^\d]+?)(\d+)[:\uff1a](\d+)(?:[-–](\d+))?$')
CHAPTER_RANGE_RE = re.compile(r'^([^\d]+?)(\d+)[-–](\d+)$')
SINGLE_CHAPTER_RE = re.compile(r'^([^\d]+?)(\d+)$')
BOOK_ONLY_RE = re.compile(r'^([^\d]+)$')

def parse_book(zh: str):
    zh = zh.strip()
    return BOOK_MAP.get(zh)

SINGLE_CHAPTER_BOOKS = {
    'Obadiah', 'Philemon', '2 John', '3 John', 'Jude',
}

def resolve_single(part: str) -> str | None:
    """Resolve one non-compound ref part."""
    part = part.strip().replace('\uff1a', ':')

    # Single verse or verse range: 创1:1  创1:1-3
    m = SINGLE_VERSE_RE.match(part)
    if m:
        book_en = parse_book(m.group(1))
        if not book_en: return None
        return get_verses(book_en, m.group(2), m.group(3), m.group(4))

    # Chapter range: 代下17-20
    # But for single-chapter books (腓利门书10-11) the numbers are verse numbers
    m = CHAPTER_RANGE_RE.match(part)
    if m:
        book_en = parse_book(m.group(1))
        if not book_en: return None
        if book_en in SINGLE_CHAPTER_BOOKS:
            # Treat as verse range in chapter 1
            return get_verses(book_en, '1', m.group(2), m.group(3))
        return get_chapter_range_preview(book_en, int(m.group(2)), int(m.group(3)), part)

    # Single chapter: 代下17  (or single-chapter book + verse: 腓利门书16)
    m = SINGLE_CHAPTER_RE.match(part)
    if m:
        book_en = parse_book(m.group(1))
        if not book_en: return None
        if book_en in SINGLE_CHAPTER_BOOKS:
            return get_verses(book_en, '1', m.group(2), None)
        return get_chapter_preview(book_en, m.group(2))

    # Book only: 约伯记
    m = BOOK_ONLY_RE.match(part)
    if m:
        book_en = parse_book(m.group(1))
        if not book_en: return None
        chs = book_chapters.get(book_en, ['1'])
        return get_chapter_preview(book_en, chs[0])

    return None

def resolve_ref(ref: str) -> str | None:
    ref = ref.strip()

    # Cross-book range: 王上17-王下2  (two book abbrevs with digits between)
    cross = re.match(r'^([^\d]+?)(\d+)[-–]([^\d]+?)(\d+)$', ref)
    if cross:
        b1 = parse_book(cross.group(1))
        b2 = parse_book(cross.group(3))
        parts = []
        if b1:
            parts.append(get_chapter_range_preview(b1, int(cross.group(2)), int(cross.group(2)) + 2, ''))
        if b2:
            parts.append(get_chapter_preview(b2, cross.group(4), cross.group(3) + cross.group(4)))
        result = '\n'.join(p for p in parts if p)
        return result or None

    # Compound comma ref: 太20，可10  /  太4，约13-21，徒2
    sep = '，' if '，' in ref else (',' if ',' in ref and ':' not in ref else None)
    if sep and sep in ref:
        parts = [p.strip() for p in ref.split(sep)]
        texts = []
        for p in parts:
            t = resolve_single(p)
            if t:
                texts.append(f'[{p}] {t}')
        return '\n'.join(texts) or None

    return resolve_single(ref)

# ── Extract all refs from mirrorData.js ──────────────────────────────────
print("Parsing mirrorData.js...", end=' ', flush=True)
with open(ROOT / 'emotion-sphere-ui/src/mirrorData.js', encoding='utf-8') as f:
    js = f.read()

refs: set[str] = set()
for m in re.finditer(r'"scriptures":\s*(\[[^\]]*\])', js):
    for r in json.loads(m.group(1)):
        refs.add(r.strip())

# Also grab theme scripture quotes (single strings)
for m in re.finditer(r'"scripture":\s*"([^"]+)"', js):
    # These are full sentences, not refs — skip
    pass

print(f"{len(refs)} unique refs")

# ── Build cache ───────────────────────────────────────────────────────────
cache: dict[str, str] = {}
missing = []
for ref in sorted(refs):
    text = resolve_ref(ref)
    if text:
        cache[ref] = text
    else:
        missing.append(ref)

print(f"Resolved: {len(cache)}, Missing/skipped: {len(missing)}")
if missing:
    print("  Missing:", missing[:20])

# ── Write output ──────────────────────────────────────────────────────────
out_path = ROOT / 'emotion-sphere-ui/public/verseCache.json'
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=None, separators=(',', ':'))

print(f"✅ Written to {out_path} ({out_path.stat().st_size//1024} KB)")
