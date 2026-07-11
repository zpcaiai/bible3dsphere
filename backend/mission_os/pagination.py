"""Validated pagination and explicit sort allowlists."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRequest:
    offset: int = 0
    limit: int = 50
    sort: str = "created_at"
    direction: str = "desc"

    def validate(self, allowed_sorts: frozenset[str]) -> "PageRequest":
        if self.offset < 0 or not 1 <= self.limit <= 200:
            raise ValueError("invalid pagination range")
        if self.sort not in allowed_sorts:
            raise ValueError("sort field is not allowed")
        if self.direction not in {"asc", "desc"}:
            raise ValueError("sort direction is not allowed")
        return self
