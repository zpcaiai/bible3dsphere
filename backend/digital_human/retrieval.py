from __future__ import annotations

import math
import os
import re
from collections import Counter, deque
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

from .registry import catalog_artifact

_LATIN_WORD = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_CJK = re.compile(r"[\u3400-\u9fff]")


def _tokens(value: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", value.casefold()).strip()
    latin = _LATIN_WORD.findall(normalized)
    cjk = "".join(_CJK.findall(normalized))
    grams = list(cjk)
    grams.extend(cjk[index:index + 2] for index in range(max(0, len(cjk) - 1)))
    return latin + grams


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    numerator = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


class LocalEmbeddingScorer:
    """Optional dense scorer loaded only from an operator-provided local model.

    Network model downloads are intentionally disabled. Deployments must stage a
    reviewed model and set DIGITAL_HUMAN_EMBEDDING_MODEL_PATH.
    """

    def __init__(self, model_path: str):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_path, local_files_only=True)

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        vectors = self._model.encode([query, *documents], normalize_embeddings=True)
        return [_cosine(vectors[0], vector) for vector in vectors[1:]]


def configured_dense_scorer() -> LocalEmbeddingScorer | None:
    path = os.getenv("DIGITAL_HUMAN_EMBEDDING_MODEL_PATH", "").strip()
    if not path:
        return None
    try:
        return LocalEmbeddingScorer(path)
    except Exception:
        return None


@dataclass(frozen=True)
class RetrievalHit:
    truth_case_id: str
    question: str
    score: float
    lexical_score: float
    dense_score: float | None
    references: tuple[str, ...]
    grounding: str | None
    must_not_claim: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "truthCaseId": self.truth_case_id,
            "question": self.question,
            "score": round(self.score, 6),
            "lexicalScore": round(self.lexical_score, 6),
            "denseScore": round(self.dense_score, 6) if self.dense_score is not None else None,
            "references": list(self.references),
            "grounding": self.grounding,
            "mustNotClaim": list(self.must_not_claim),
        }


@dataclass(frozen=True)
class GraphPath:
    source: str
    target: str
    relationship_type: str
    evidence: tuple[str, ...]
    depth: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "target": self.target,
            "relationshipType": self.relationship_type,
            "evidence": list(self.evidence),
            "depth": self.depth,
        }


class CharacterGraph:
    def __init__(self, characters: Sequence[dict]):
        self._characters = {item["id"]: item for item in characters}
        self._labels: dict[str, set[str]] = {}
        self._edges: dict[str, list[GraphPath]] = {}
        for item in characters:
            self._labels[item["id"]] = {
                str(item["id"]).casefold(), str(item["canonicalName"]).casefold(),
                str(item["englishName"]).casefold(),
            }
            for relation in item.get("relationships", []):
                edge = GraphPath(
                    source=item["id"], target=str(relation["target"]),
                    relationship_type=str(relation["type"]),
                    evidence=tuple(str(value) for value in relation.get("evidence", [])), depth=1,
                )
                self._edges.setdefault(item["id"], []).append(edge)

    def retrieve(self, character_id: str, question: str, max_depth: int = 2, limit: int = 12) -> list[GraphPath]:
        if character_id not in self._characters:
            return []
        normalized = question.casefold()
        named_targets = {
            character for character, labels in self._labels.items()
            if character != character_id and any(label and label in normalized for label in labels)
        }
        queue = deque([(character_id, 0)])
        visited = {character_id}
        results: list[GraphPath] = []
        while queue and len(results) < limit:
            source, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self._edges.get(source, []):
                next_depth = depth + 1
                candidate = GraphPath(
                    source=edge.source, target=edge.target,
                    relationship_type=edge.relationship_type,
                    evidence=edge.evidence, depth=next_depth,
                )
                if not named_targets or edge.target in named_targets or source == character_id:
                    results.append(candidate)
                if edge.target in self._characters and edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, next_depth))
        results.sort(key=lambda item: (0 if item.target in named_targets else 1, item.depth, item.relationship_type, item.target))
        return results[:limit]


class HybridCharacterRetriever:
    """Fuse lexical BM25, optional local dense embeddings and graph evidence."""

    def __init__(self, *, dense_scorer=None, artifact: dict | None = None):
        self._artifact = artifact or catalog_artifact()
        self._characters = {item["id"]: item for item in self._artifact["characters"]}
        self._dense = dense_scorer if dense_scorer is not None else configured_dense_scorer()
        self.graph = CharacterGraph(self._artifact["characters"])

    @property
    def dense_enabled(self) -> bool:
        return self._dense is not None

    def retrieve(self, character_id: str, question: str, top_k: int = 5) -> dict[str, object]:
        character = self._characters.get(character_id)
        if character is None:
            raise KeyError(character_id)
        top_k = max(1, min(int(top_k), 12))
        cases = character.get("truthCases", [])
        documents = [str(item.get("question", "")) for item in cases]
        lexical = self._bm25(question, documents)
        dense: list[float | None] = [None] * len(cases)
        if self._dense and documents:
            try:
                values = self._dense.score(question, documents)
                if len(values) == len(documents):
                    dense = [max(-1.0, min(float(value), 1.0)) for value in values]
            except Exception:
                dense = [None] * len(cases)

        hits: list[RetrievalHit] = []
        query_norm = re.sub(r"\s+", "", question.casefold())
        for index, case in enumerate(cases):
            expected = case.get("expected") or {}
            exact_bonus = 0.15 if query_norm == re.sub(r"\s+", "", documents[index].casefold()) else 0.0
            structure_score = 1.0 if expected.get("mustReference") else 0.4
            if dense[index] is None:
                score = 0.85 * lexical[index] + 0.15 * structure_score + exact_bonus
            else:
                score = 0.55 * lexical[index] + 0.35 * max(0.0, dense[index]) + 0.10 * structure_score + exact_bonus
            hits.append(RetrievalHit(
                truth_case_id=str(case["id"]), question=documents[index], score=score,
                lexical_score=lexical[index], dense_score=dense[index],
                references=tuple(str(value) for value in expected.get("mustReference", [])),
                grounding=expected.get("minGrounding") or expected.get("grounding"),
                must_not_claim=tuple(str(value) for value in expected.get("mustNotClaim", [])),
            ))
        hits.sort(key=lambda item: (-item.score, item.truth_case_id))
        graph_paths = self.graph.retrieve(character_id, question)
        return {
            "characterId": character_id,
            "mode": "HYBRID_DENSE_LEXICAL_GRAPH" if any(item.dense_score is not None for item in hits) else "LEXICAL_GRAPH_DEGRADED",
            "hits": [item.to_dict() for item in hits[:top_k]],
            "graphPaths": [item.to_dict() for item in graph_paths],
            "personaSha256": character["persona"]["sha256"],
            "ragScope": list(character.get("ragScope", [])),
        }

    @staticmethod
    def _bm25(query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        query_terms = _tokens(query)
        if not query_terms:
            return [0.0] * len(documents)
        tokenized = [_tokens(document) for document in documents]
        average_length = sum(len(item) for item in tokenized) / max(len(tokenized), 1)
        document_frequency = Counter()
        for terms in tokenized:
            document_frequency.update(set(terms))
        scores: list[float] = []
        coverages: list[float] = []
        unique_query_terms = set(query_terms)
        for terms in tokenized:
            frequencies = Counter(terms)
            score = 0.0
            for term in query_terms:
                if not frequencies[term]:
                    continue
                idf = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
                denominator = frequencies[term] + 1.2 * (1 - 0.75 + 0.75 * len(terms) / max(average_length, 1.0))
                score += idf * (frequencies[term] * 2.2) / denominator
            scores.append(score)
            coverages.append(len(unique_query_terms.intersection(frequencies)) / max(len(unique_query_terms), 1))
        maximum = max(scores, default=0.0)
        return [
            (value / maximum) * coverages[index] if maximum else 0.0
            for index, value in enumerate(scores)
        ]


@lru_cache(maxsize=1)
def get_retriever() -> HybridCharacterRetriever:
    return HybridCharacterRetriever()
