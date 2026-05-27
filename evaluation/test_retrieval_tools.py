from pathlib import Path

from run_retrieval_eval import aggregate, normalize_ref, score_case

import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from artifact_manifest import build_manifest


def test_score_case_counts_first_expected_rank():
    case = {
        "id": "case-1",
        "theme": "comfort",
        "expected_refs": ["马太福音 6:34"],
        "avoid_refs": ["约伯记 2:9"],
    }
    results = [
        {"verse": "诗篇 23:4"},
        {"verse": " 马太福音   6:34 "},
    ]

    score = score_case(case, results, top_k=5)

    assert score.hit is True
    assert score.first_expected_rank == 2
    assert score.reciprocal_rank == 0.5
    assert score.avoid_hit is False


def test_aggregate_scores():
    case = {"id": "case-1", "theme": "wisdom", "expected_refs": ["雅各书 1:5"], "avoid_refs": []}
    hit = score_case(case, [{"verse": "雅各书 1:5"}], top_k=3)
    miss = score_case(case, [{"verse": "箴言 3:5"}], top_k=3)

    summary = aggregate([hit, miss])

    assert summary["case_count"] == 2
    assert summary["hit_rate_at_k"] == 0.5
    assert summary["mrr_at_k"] == 0.5


def test_normalize_ref_collapses_spacing():
    assert normalize_ref(" 马太福音　 6:34 ") == "马太福音 6:34"


def test_manifest_records_existing_and_missing_files(tmp_path):
    artifact = tmp_path / "sample_config.json"
    artifact.write_text('{"embedding_model":"test-model","vector_count":2}', encoding="utf-8")
    missing = tmp_path / "missing.npy"

    manifest = build_manifest([artifact, missing], tmp_path)

    assert manifest["artifact_count"] == 1
    assert manifest["artifacts"][0]["embedding_model"] == "test-model"
    assert manifest["artifacts"][0]["vector_count"] == 2
    assert manifest["missing"] == ["missing.npy"]
