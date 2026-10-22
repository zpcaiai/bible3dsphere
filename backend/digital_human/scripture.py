from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def canon_index() -> dict[str, dict[int, int]]:
    source = Path(__file__).resolve().parents[2] / "bible" / "esv_bible.csv"
    books: dict[str, dict[int, int]] = {}
    with source.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            book = re.sub(r"\s+", " ", row["book"].strip()).lower()
            chapter = int(row["chapter"])
            verse = int(row["verse"])
            chapters = books.setdefault(book, {})
            chapters[chapter] = max(verse, chapters.get(chapter, 0))
    return books


BOOK_ALIASES = {"psalm": "psalms", "song of songs": "song of solomon"}


def expand_reference(locator: str) -> tuple[str, ...]:
    """Validate every citation part against the local canon, without quoting it.

    Semicolons reset verse shorthand; commas retain the preceding chapter.
    A single invalid part rejects the entire citation.
    """
    if not isinstance(locator, str) or not locator.strip() or len(locator) > 120:
        return ()
    value = re.sub(r"\s+", " ", locator.strip()).replace("–", "-").replace("—", "-")
    books = canon_index()
    names = sorted(set(books) | set(BOOK_ALIASES), key=len, reverse=True)
    result: list[str] = []
    book = None
    try:
        for section in value.split(";"):
            section = section.strip().lower()
            if not section:
                return ()
            matched = next((name for name in names if section == name or section.startswith(name + " ")), None)
            if matched:
                book = BOOK_ALIASES.get(matched, matched)
                section = section[len(matched):].strip()
            if book not in books:
                return ()
            chapters = books[book]
            label = book.title()
            if not section:
                result.append(label)
                continue
            chapter_context = None
            for part in section.split(","):
                part = part.strip()
                if not re.fullmatch(r"\d+(?::\d+)?(?:-\d+(?::\d+)?)?", part):
                    return ()
                if ":" not in part:
                    start, _, end = part.partition("-")
                    first, last = int(start), int(end or start)
                    if chapter_context is not None or len(chapters) == 1:
                        chapter = chapter_context or 1
                        if not 1 <= first <= last <= chapters[chapter]:
                            return ()
                        result.append(f"{label} {chapter}:{first}" + (f"-{last}" if first != last else ""))
                        chapter_context = chapter
                    else:
                        if first > last or last - first > 150 or not all(ch in chapters for ch in range(first, last + 1)):
                            return ()
                        result.append(f"{label} {first}" + (f"-{last}" if first != last else ""))
                    continue
                start, _, end = part.partition("-")
                first_ch, first_v = (int(item) for item in start.split(":"))
                if ":" in end:
                    last_ch, last_v = (int(item) for item in end.split(":"))
                else:
                    last_ch, last_v = first_ch, int(end or first_v)
                if (first_ch, first_v) > (last_ch, last_v):
                    return ()
                if first_ch not in chapters or last_ch not in chapters:
                    return ()
                if not 1 <= first_v <= chapters[first_ch] or not 1 <= last_v <= chapters[last_ch]:
                    return ()
                for ch in range(first_ch, last_ch + 1):
                    if ch not in chapters:
                        return ()
                    lo = first_v if ch == first_ch else 1
                    hi = last_v if ch == last_ch else chapters[ch]
                    result.append(f"{label} {ch}:{lo}" + (f"-{hi}" if lo != hi else ""))
                chapter_context = last_ch
                if len(result) > 150:
                    return ()
    except (ValueError, KeyError):
        return ()
    return tuple(dict.fromkeys(result))


def resolve_reference(locator: str) -> bool:
    return bool(expand_reference(locator))
