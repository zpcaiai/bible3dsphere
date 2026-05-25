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
    # Alternate spellings seen in data
    '腓利门书':'Philemon',
}

def clean_text(t: str) -> str:
    """Remove CUV word-spacing and ideographic spaces."""
    return t.replace('\u3000', '').replace(' ', '').strip()

# ── Load CSV into lookup: (book_en, chapter, verse) → text ───────────────
print("Loading CSV...", end=' ', flush=True)
verse_db: dict[tuple, str] = {}
with open(ROOT / 'bible/cuv_bible.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        key = (row['book'], row['chapter'], row['verse'])
        verse_db[key] = clean_text(row['text'])
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

def get_chapter(book_en: str, chapter: str) -> str:
    """Return first 3 verses of a chapter as preview."""
    texts = []
    for v in range(1, 4):
        t = verse_db.get((book_en, chapter, str(v)))
        if t:
            texts.append(t)
    return ''.join(texts) + ('…' if texts else '')

# ── Parse a ref string ────────────────────────────────────────────────────
# Patterns: 创1:1  创1:1-3  创1  创2,6  王上1:1
REF_RE = re.compile(
    r'^([^\d]+?)\s*(\d+)(?:[:\uff1a](\d+)(?:[-\u2013](\d+))?)?$'
)

def resolve_ref(ref: str) -> str | None:
    ref = ref.strip()
    # Normalize Chinese colon
    ref = ref.replace('\uff1a', ':')
    # Handle comma-separated chapters like "书2,6" → take first
    if ',' in ref and ':' not in ref:
        ref = ref.split(',')[0].strip()
    m = REF_RE.match(ref)
    if not m:
        return None
    zh_book, chapter, v_start, v_end = m.group(1), m.group(2), m.group(3), m.group(4)
    zh_book = zh_book.strip()
    book_en = BOOK_MAP.get(zh_book)
    if not book_en:
        print(f"  ⚠ Unknown book: '{zh_book}' in ref '{ref}'", file=sys.stderr)
        return None
    if v_start:
        return get_verses(book_en, chapter, v_start, v_end)
    else:
        return get_chapter(book_en, chapter)

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
