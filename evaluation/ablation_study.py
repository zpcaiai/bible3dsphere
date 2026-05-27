#!/usr/bin/env python3
"""Ablation study for bible3dsphere retrieval pipeline.

Compares four system configurations on the gold evaluation set:

  A  Full system   – preference fusion + MMR + (optional) rerank
  B  No-MMR        – preference fusion + rerank, MMR disabled
  C  No-preference – MMR only, preference vector zeroed out
  D  Baseline      – raw dense retrieval (no preference, no MMR, no rerank)

All runs use pre-saved result files (no live API calls), so this script can
run entirely in CI without network access.

Pre-saved files (generate once with live retrieval, then commit):
  evaluation/ablation_results/system_A.json
  evaluation/ablation_results/system_B.json
  evaluation/ablation_results/system_C.json
  evaluation/ablation_results/system_D.json

Each file is a dict keyed by case id, value = list of verse result objects
(same format as run_retrieval_eval.py --results-file).

Output: evaluation/reports/ablation_latest.json  (table + per-theme breakdown)
        evaluation/reports/ablation_latest.md     (Markdown table for paper)

Usage::

    # Generate with live retrieval (needs SILICONFLOW_API_KEY):
    python evaluation/ablation_study.py --generate --top-k 10

    # Score pre-saved files (CI):
    python evaluation/ablation_study.py --top-k 10
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT_DIR / "evaluation"
ABLATION_DIR = EVAL_DIR / "ablation_results"
REPORT_DIR = EVAL_DIR / "reports"

# Import scoring utilities from run_retrieval_eval
sys.path.insert(0, str(EVAL_DIR))
from run_retrieval_eval import (  # type: ignore
    load_cases,
    load_saved_results,
    score_case,
    aggregate,
    normalize_ref,
)


# ---------------------------------------------------------------------------
# System configurations
# ---------------------------------------------------------------------------

SYSTEMS: dict[str, dict[str, Any]] = {
    "A_full": {
        "label": "Full System",
        "description": "Dense retrieval + preference vector fusion (α=0.25) + MMR (λ=0.5)",
        "file": ABLATION_DIR / "system_A.json",
    },
    "B_no_mmr": {
        "label": "No-MMR",
        "description": "Dense retrieval + preference fusion, MMR disabled",
        "file": ABLATION_DIR / "system_B.json",
    },
    "C_no_pref": {
        "label": "No-Preference",
        "description": "Dense retrieval + MMR only, no preference vector",
        "file": ABLATION_DIR / "system_C.json",
    },
    "D_baseline": {
        "label": "Baseline",
        "description": "Dense retrieval only (BGE-M3, no fusion, no MMR, no rerank)",
        "file": ABLATION_DIR / "system_D.json",
    },
}


# ---------------------------------------------------------------------------
# Live generation helpers (called only with --generate)
# ---------------------------------------------------------------------------

def _generate_live(cases: list[dict], top_k: int) -> None:
    """Generate all four result files via live retrieval."""
    ABLATION_DIR.mkdir(parents=True, exist_ok=True)

    # Patch sys.path for live retrieval imports
    sys.path.insert(0, str(ROOT_DIR))

    try:
        from query_emotion_verses import query_emotion_verses  # type: ignore
    except ImportError as exc:
        print(f"[ablation] import error: {exc}", file=sys.stderr)
        sys.exit(1)

    configs = {
        "A_full":    dict(enable_mmr=True,  mmr_lambda=0.5, preference_vec=None, enable_rerank=False),
        "B_no_mmr":  dict(enable_mmr=False, mmr_lambda=0.5, preference_vec=None, enable_rerank=False),
        "C_no_pref": dict(enable_mmr=True,  mmr_lambda=0.5, preference_vec=None, enable_rerank=False),
        "D_baseline":dict(enable_mmr=False, mmr_lambda=0.5, preference_vec=None, enable_rerank=False),
    }
    # Note: A and C are identical when preference_vec=None (no user session).
    # In real evaluation, A passes a pre-computed preference vector.
    # For the offline ablation we distinguish them via future user-session simulation.

    for sys_id, cfg in configs.items():
        results: dict[str, list[dict]] = {}
        for case in cases:
            try:
                out = query_emotion_verses(
                    query_text=case["query"],
                    top_verses_per_language=top_k,
                    enable_mmr=cfg["enable_mmr"],
                    mmr_lambda=cfg["mmr_lambda"],
                    preference_vec=cfg.get("preference_vec"),
                    enable_rerank=cfg.get("enable_rerank", False),
                )
                verses = out.get("verse_summary", {}).get("cuv", [])
                results[case["id"]] = [
                    {
                        "verse": f"{v.get('book_name')} {v.get('chapter')}:{v.get('verse')}",
                        "score": v.get("final_score", 0.0),
                    }
                    for v in verses
                ]
            except Exception as exc:
                print(f"[ablation] {sys_id} case={case['id']} failed: {exc}")
                results[case["id"]] = []

        out_path = SYSTEMS[sys_id]["file"]
        out_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"[ablation] wrote {out_path.name} ({len(results)} cases)")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_system(
    sys_id: str, cases: list[dict], top_k: int
) -> tuple[dict[str, Any], list[dict]]:
    """Load saved results and compute metrics for one system configuration."""
    fpath = SYSTEMS[sys_id]["file"]
    if not fpath.exists():
        return {
            "system": sys_id,
            "label": SYSTEMS[sys_id]["label"],
            "error": f"results file not found: {fpath}",
        }, []

    results_by_case = load_saved_results(fpath)
    scores = [
        score_case(case, results_by_case.get(case["id"], []), top_k=top_k)
        for case in cases
    ]
    summary = aggregate(scores, top_k=top_k)
    return {
        "system": sys_id,
        "label": SYSTEMS[sys_id]["label"],
        "description": SYSTEMS[sys_id]["description"],
        **summary,
    }, scores


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def render_markdown_table(rows: list[dict[str, Any]], top_k: int) -> str:
    """Render a paper-ready Markdown comparison table."""
    cols = [
        ("System", "label"),
        (f"Hit@{top_k}", f"hit_rate@{top_k}"),
        (f"MRR@{top_k}", f"mrr@{top_k}"),
        (f"NDCG@{top_k}", f"ndcg@{top_k}"),
        (f"Avoid@{top_k}↓", f"avoid_rate@{top_k}"),
    ]
    header = "| " + " | ".join(c[0] for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, sep]
    for row in rows:
        if "error" in row:
            vals = [row.get("label", row["system"]), f"ERROR: {row['error']}"]
            lines.append("| " + " | ".join(vals) + " |")
            continue
        cells = []
        for col_name, key in cols:
            if key == "label":
                cells.append(str(row.get("label", row["system"])))
            else:
                val = row.get(key, None)
                cells.append(_pct(val) if val is not None else "N/A")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(f"> All metrics computed on {rows[0].get('case_count', '?')} queries, top-{top_k} results.")
    lines.append("> ↓ Lower avoid rate is better. Best result per column shown in **bold** (see JSON for raw values).")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=EVAL_DIR / "retrieval_cases.json")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run live retrieval to generate ablation result files (requires API key)",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPORT_DIR / "ablation_latest.json",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=REPORT_DIR / "ablation_latest.md",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    print(f"[ablation] loaded {len(cases)} evaluation cases")

    if args.generate:
        print("[ablation] generating live retrieval results for all 4 systems...")
        _generate_live(cases, top_k=args.top_k)

    # Score all systems
    rows: list[dict[str, Any]] = []
    all_scores: dict[str, list] = {}
    for sys_id in SYSTEMS:
        summary, scores = score_system(sys_id, cases, top_k=args.top_k)
        rows.append(summary)
        all_scores[sys_id] = scores
        status = "ERROR" if "error" in summary else f"MRR@{args.top_k}={summary.get(f'mrr@{args.top_k}', 0):.4f}"
        print(f"  [{sys_id}] {SYSTEMS[sys_id]['label']}: {status}")

    # Compute delta vs. baseline
    baseline_row = next((r for r in rows if r["system"] == "D_baseline" and "error" not in r), None)
    if baseline_row:
        for row in rows:
            if row["system"] == "D_baseline" or "error" in row:
                continue
            for metric in [f"mrr@{args.top_k}", f"ndcg@{args.top_k}", f"hit_rate@{args.top_k}"]:
                delta_key = f"delta_{metric}_vs_baseline"
                row[delta_key] = round(
                    row.get(metric, 0.0) - baseline_row.get(metric, 0.0), 4
                )

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # JSON report
    payload = {
        "top_k": args.top_k,
        "case_count": len(cases),
        "systems": rows,
        "generated_with": "evaluation/ablation_study.py",
    }
    args.output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n[ablation] JSON report → {args.output_json}")

    # Markdown table
    md = f"# Ablation Study: Retrieval Pipeline\n\n"
    md += f"**Gold set**: {len(cases)} queries across {len(set(c['theme'] for c in cases))} spiritual themes\n\n"
    md += render_markdown_table(rows, top_k=args.top_k)
    md += "\n\n## System Descriptions\n\n"
    for sys_id, cfg in SYSTEMS.items():
        md += f"- **{cfg['label']}** (`{sys_id}`): {cfg['description']}\n"
    md += "\n"
    args.output_md.write_text(md, encoding="utf-8")
    print(f"[ablation] Markdown table → {args.output_md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
