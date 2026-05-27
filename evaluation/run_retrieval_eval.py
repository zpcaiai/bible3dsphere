#!/usr/bin/env python3
"""Evaluate emotion-to-verse retrieval against a small curated gold set."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    theme: str
    hit: bool
    reciprocal_rank: float
    avoid_hit: bool
    first_expected_rank: int | None
    returned_refs: list[str]


def normalize_ref(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).replace("　", " ").split())


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_saved_results(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("results-file must be a JSON object keyed by case id")
    return data


def run_live_retrieval(cases: list[dict[str, Any]], top_k: int, backend: str) -> dict[str, list[dict[str, Any]]]:
    from search_bible_index import search_bible

    results: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        results[case["id"]] = search_bible(case["query"], top_k=top_k, backend=backend)
    return results


def score_case(case: dict[str, Any], results: list[dict[str, Any]], top_k: int) -> CaseScore:
    expected = {normalize_ref(ref) for ref in case.get("expected_refs", [])}
    avoid = {normalize_ref(ref) for ref in case.get("avoid_refs", [])}
    returned_refs = [normalize_ref(item.get("verse") or item.get("ref")) for item in results[:top_k]]

    first_expected_rank = None
    for index, ref in enumerate(returned_refs, start=1):
        if ref in expected:
            first_expected_rank = index
            break

    avoid_hit = any(ref in avoid for ref in returned_refs if ref)
    reciprocal_rank = 1.0 / first_expected_rank if first_expected_rank else 0.0
    return CaseScore(
        case_id=case["id"],
        theme=case.get("theme", ""),
        hit=first_expected_rank is not None,
        reciprocal_rank=reciprocal_rank,
        avoid_hit=avoid_hit,
        first_expected_rank=first_expected_rank,
        returned_refs=returned_refs,
    )


def aggregate(scores: list[CaseScore]) -> dict[str, Any]:
    total = len(scores)
    if total == 0:
        return {"case_count": 0, "hit_rate_at_k": 0.0, "mrr_at_k": 0.0, "avoid_rate_at_k": 0.0}
    return {
        "case_count": total,
        "hit_rate_at_k": sum(1 for score in scores if score.hit) / total,
        "mrr_at_k": sum(score.reciprocal_rank for score in scores) / total,
        "avoid_rate_at_k": sum(1 for score in scores if score.avoid_hit) / total,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT_DIR / "evaluation" / "retrieval_cases.json")
    parser.add_argument("--results-file", type=Path, help="Score a saved result JSON instead of running live retrieval")
    parser.add_argument("--output", type=Path, default=ROOT_DIR / "evaluation" / "reports" / "retrieval_eval_latest.json")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--backend", choices=["faiss", "qdrant"], default="faiss")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.results_file:
        results_by_case = load_saved_results(args.results_file)
    else:
        results_by_case = run_live_retrieval(cases, top_k=args.top_k, backend=args.backend)

    scores = [
        score_case(case, results_by_case.get(case["id"], []), top_k=args.top_k)
        for case in cases
    ]
    payload = {
        "top_k": args.top_k,
        "summary": aggregate(scores),
        "cases": [
            {
                "case_id": score.case_id,
                "theme": score.theme,
                "hit": score.hit,
                "first_expected_rank": score.first_expected_rank,
                "reciprocal_rank": score.reciprocal_rank,
                "avoid_hit": score.avoid_hit,
                "returned_refs": score.returned_refs,
            }
            for score in scores
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
