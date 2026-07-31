from __future__ import annotations

from .models import SourceDocument


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceDocument] = {}

    def add(self, source: SourceDocument) -> None:
        if source.source_id in self._sources:
            raise ValueError(f"Duplicate source_id: {source.source_id}")
        self._sources[source.source_id] = source

    def get(self, source_id: str) -> SourceDocument:
        return self._sources[source_id]

    def list_ids(self) -> list[str]:
        return sorted(self._sources)

    def __len__(self) -> int:
        return len(self._sources)
