from query_emotion_verses import build_verse_evidence


def test_build_verse_evidence_uses_top_features_and_signals():
    verse = {
        "combined_score": 0.42,
        "final_score": 0.55,
        "best_feature_similarity": 0.7,
        "best_verse_score": 0.3,
        "rerank_score": 0.8,
        "matched_features": [
            {
                "layer": "1",
                "feature_id": "10",
                "source_keyword": "comfort",
                "explanation": "comfort in suffering",
                "similarity": 0.7,
                "verse_score": 0.3,
            },
            {
                "layer": "2",
                "feature_id": "20",
                "source_keyword": "hope",
                "explanation": "future hope",
                "similarity": 0.6,
                "verse_score": 0.25,
            },
        ],
    }

    evidence = build_verse_evidence(verse)

    assert evidence["method"] == "dense_feature_to_verse_aggregation"
    assert evidence["top_features"][0]["feature_key"] == "1:10"
    assert evidence["signals"]["final_score"] == 0.55
    assert "not_reranked" not in evidence["uncertainty"]


def test_build_verse_evidence_marks_uncertainty():
    evidence = build_verse_evidence({
        "combined_score": 0.2,
        "matched_features": [{"layer": "1", "feature_id": "10", "similarity": 0.2, "verse_score": 0.1}],
    })

    assert "overall_score_low" in evidence["uncertainty"]
    assert "single_feature_match" in evidence["uncertainty"]
    assert "not_reranked" in evidence["uncertainty"]
