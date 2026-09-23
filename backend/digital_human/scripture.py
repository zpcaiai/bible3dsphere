from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path

REFERENCE_RE = re.compile(
    r"^(?P<book>[1-3]?\s*[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+"
    r"(?P<chapter>\d+)(?:(?P<chapter_range>-)(?P<chapter_end>\d+)|:"
    r"(?P<verse>\d+)(?:-(?P<verse_end>\d+))?)?$"
)


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


def resolve_reference(locator: str) -> bool:
    match = REFERENCE_RE.fullmatch(re.sub(r"\s+", " ", locator.strip()))
    if not match:
        return False
    chapters = canon_index().get(match.group("book").lower())
    if not chapters:
        return False
    chapter = int(match.group("chapter"))
    if chapter not in chapters:
        return False
    if match.group("chapter_end") is not None:
        end = int(match.group("chapter_end"))
        return end >= chapter and all(item in chapters for item in range(chapter, end + 1))
    if match.group("verse") is None:
        return True
    start = int(match.group("verse"))
    end = int(match.group("verse_end") or start)
    return 1 <= start <= end <= chapters[chapter]
