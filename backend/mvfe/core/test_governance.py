from backend.mvfe.core.governance import ConstitutionLayer


def test_audit_flags_chinese_prescription_and_divine_certainty():
    layer = ConstitutionLayer()

    report = layer.audit("你必须马上去做，这是神的旨意。", {"drift_score": 0.1})

    assert report.passed is False
    assert report.risk_level == "high"
    assert "manipulation" in report.categories
    assert "divine_certainty" in report.categories


def test_audit_warns_on_high_drift_determinism():
    layer = ConstitutionLayer()

    report = layer.audit("This will lead to failure definitely.", {"drift_score": 0.9})

    assert report.passed is False
    assert report.formation_danger_flag is True
    assert report.risk_level == "high"
    assert "deterministic_language" in report.categories
    assert "formation_danger" in report.categories


def test_audit_allows_probabilistic_reflection():
    layer = ConstitutionLayer()

    report = layer.audit(
        "This may suggest a season of weariness, though other interpretations are possible.",
        {"drift_score": 0.2},
    )

    assert report.passed is True
    assert report.warnings == []
    assert report.risk_level == "low"


def test_sanitize_softens_common_prescriptive_language():
    layer = ConstitutionLayer()
    report = layer.audit("你必须接受这是神的旨意。", {"drift_score": 0.1})

    sanitized = layer.sanitize("你必须接受这是神的旨意。", report)

    assert sanitized.startswith("[SYSTEM NOTE:")
    assert "你必须" not in sanitized
    assert "这是神的旨意" not in sanitized
