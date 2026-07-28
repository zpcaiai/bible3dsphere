"""Rebuild the table catalog from `migrations/*.sql` — one parser, one place.

There were briefly three copies of this logic: one in the deletion-propagation test, one
in the erasure schema verification test, and one inlined in the privacy assessment. Two of
them agreed only by luck. The first version was wrong in a way that made a safety check
pass for the wrong reason — it recognised a column only when it started a line, but the EMD
migrations pack several per line:

    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,

so `email` was never seen, the "personal tables" set came out empty, and
`personal ⊆ erase_list` held trivially. Duplicated parsers drift; a drifting parser under a
privacy check is the worst place for it. Hence: production module, imported by everything
that needs it, with the packed-column case pinned by a test.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"

_CREATE_TABLE = re.compile(
    r"CREATE TABLE (?:IF NOT EXISTS )?([a-zA-Z0-9_.]+)\s*\((.*?)\n\);", re.S
)
_NOT_A_COLUMN = frozenset({
    "PRIMARY", "UNIQUE", "FOREIGN", "CHECK", "CONSTRAINT", "EXCLUDE", "LIKE",
})
_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*")


def split_top_level(body: str) -> list[str]:
    """Split a CREATE TABLE body on commas that are not inside parentheses."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def columns_of(body: str) -> set[str]:
    """Column names declared in a CREATE TABLE body, ignoring table constraints."""
    columns: set[str] = set()
    for part in split_top_level(body):
        tokens = part.strip().split()
        if not tokens:
            continue
        name = tokens[0].strip('"')
        if name.upper() in _NOT_A_COLUMN:
            continue
        if _IDENTIFIER.fullmatch(name):
            columns.add(name)
    return columns


@lru_cache(maxsize=1)
def catalog() -> dict[str, frozenset[str]]:
    """{table: columns} across every migration — the offline `information_schema`."""
    tables: dict[str, set[str]] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in _CREATE_TABLE.finditer(text):
            name = match.group(1).split(".")[-1]
            tables.setdefault(name, set()).update(columns_of(match.group(2)))
    return {name: frozenset(columns) for name, columns in tables.items()}


def tables_with(column: str) -> set[str]:
    return {name for name, columns in catalog().items() if column in columns}


def emd_tables() -> set[str]:
    return {name for name in catalog() if name.startswith("formation_twin_emd_")}
