#!/usr/bin/env python3
"""Evaluate emotion-to-verse retrieval against a curated gold set.

Metrics (all @k):
  hit_rate    – fraction of queries where ≥1 expected verse appears in top-k
  mrr         – Mean Reciprocal Rank of the first expected verse
  ndcg        – Normalised Discounted Cumulative Gain (binary relevance)
  avoid_rate  – fraction of queries where a blacklisted verse appears (lower is better)
  theme_mrr   – per-theme MRR breakdown

Usage
-----
Live retrieval (requires SILICONFLOW_API_KEY + local index)::

    python evaluation/run_retrieval_eval.py --top-k 10

Score saved results (no API needed — used in CI)::

    python evaluation/run_retrieval_eval.py \\
        --results-file evaluation/saved_results.json \\
        --output evaluation/reports/retrieval_eval_latest.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CaseScore:
    case_id: str
    theme: str
    hit: bool
    reciprocal_rank: float
    ndcg: float
    avoid_hit: bool
    first_expected_rank: int | None
    returned_refs: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def run_live_retrieval(
    cases: list[dict[str, Any]], top_k: int, backend: str
) -> dict[str, list[dict[str, Any]]]:
    from search_bible_index import search_bible  # type: ignore

    results: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        results[case["id"]] = search_bible(case["query"], top_k=top_k, backend=backend)
    return results


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _dcg(gains: list[float]) -> float:
    """Discounted Cumulative Gain."""
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def compute_ndcg(returned_refs: list[str], expected: set[str], top_k: int) -> float:
    """Binary-relevance NDCG@k."""
    gains = [1.0 if ref in expected else 0.0 for ref in returned_refs[:top_k]]
    dcg = _dcg(gains)
    # Ideal DCG: put all hits at the top
    n_hits = min(len(expected), top_k)
    ideal_gains = [1.0] * n_hits + [0.0] * (top_k - n_hits)
    idcg = _dcg(ideal_gains[:top_k])
    return dcg / idcg if idcg > 0 else 0.0


def score_case(case: dict[str, Any], results: list[dict[str, Any]], top_k: int) -> CaseScore:
    expected = {normalize_ref(ref) for ref in case.get("expected_refs", [])}
    avoid = {normalize_ref(ref) for ref in case.get("avoid_refs", [])}
    returned_refs = [
        normalize_ref(item.get("verse") or item.get("ref")) for item in results[:top_k]
    ]

    first_expected_rank: int | None = None
    for idx, ref in enumerate(returned_refs, start=1):
        if ref in expected:
            first_expected_rank = idx
            break

    avoid_hit = any(ref in avoid for ref in returned_refs if ref)
    reciprocal_rank = 1.0 / first_expected_rank if first_expected_rank else 0.0
    ndcg = compute_ndcg(returned_refs, expected, top_k)

    return CaseScore(
        case_id=case["id"],
        theme=case.get("theme", ""),
        hit=first_expected_rank is not None,
        reciprocal_rank=reciprocal_rank,
        ndcg=ndcg,
        avoid_hit=avoid_hit,
        first_expected_rank=first_expected_rank,
        returned_refs=returned_refs,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def aggregate(scores: list[CaseScore], top_k: int) -> dict[str, Any]:
    total = len(scores)
    if total == 0:
        return {
            "case_count": 0,
            f"hit_rate@{top_k}": 0.0,
            f"mrr@{top_k}": 0.0,
            f"ndcg@{top_k}": 0.0,
            f"avoid_rate@{top_k}": 0.0,
            "theme_breakdown": {},
        }

    by_theme: dict[str, list[CaseScore]] = defaultdict(list)
    for s in scores:
        by_theme[s.theme].append(s)

    theme_breakdown = {
        theme: {
            f"mrr@{top_k}": round(
                sum(s.reciprocal_rank for s in tscores) / len(tscores), 4
            ),
            f"ndcg@{top_k}": round(
                sum(s.ndcg for s in tscores) / len(tscores), 4
            ),
            f"hit_rate@{top_k}": round(
                sum(1 for s in tscores if s.hit) / len(tscores), 4
            ),
            "n": len(tscores),
        }
        for theme, tscores in sorted(by_theme.items())
    }

    return {
        "case_count": total,
        f"hit_rate@{top_k}": round(sum(1 for s in scores if s.hit) / total, 4),
        f"mrr@{top_k}": round(sum(s.reciprocal_rank for s in scores) / total, 4),
        f"ndcg@{top_k}": round(sum(s.ndcg for s in scores) / total, 4),
        f"avoid_rate@{top_k}": round(sum(1 for s in scores if s.avoid_hit) / total, 4),
        "theme_breakdown": theme_breakdown,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases",
        type=Path,
        default=ROOT_DIR / "evaluation" / "retrieval_cases.json",
    )
    parser.add_argument(
        "--results-file",
        type=Path,
        help="Score a saved result JSON instead of running live retrieval",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "evaluation" / "reports" / "retrieval_eval_latest.json",
    )
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--backend", choices=["faiss", "qdrant"], default="faiss")
    # CI gate: exit 1 if MRR@k falls below this threshold
    parser.add_argument("--min-mrr", type=float, default=0.0, help="Fail if MRR@k < threshold")
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

    summary = aggregate(scores, top_k=args.top_k)
    payload = {
        "top_k": args.top_k,
        "summary": summary,
        "cases": [
            {
                "case_id": s.case_id,
                "theme": s.theme,
                "hit": s.hit,
                "first_expected_rank": s.first_expected_rank,
                "reciprocal_rank": round(s.reciprocal_rank, 4),
                "ndcg": round(s.ndcg, 4),
                "avoid_hit": s.avoid_hit,
                "returned_refs": s.returned_refs,
            }
            for s in scores
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    mrr_key = f"mrr@{args.top_k}"
    if args.min_mrr > 0 and summary.get(mrr_key, 0.0) < args.min_mrr:
        print(f"\n[FAIL] {mrr_key}={summary[mrr_key]:.4f} < threshold {args.min_mrr}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
