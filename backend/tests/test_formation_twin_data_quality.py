import pytest

from formation_twin.data_quality import owner_quality_report


pytestmark = pytest.mark.no_db


class FakeCursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.queries = []

    def execute(self, query, params):
        self.queries.append((query, params))

    def fetchone(self):
        return next(self.rows)


def test_quality_report_is_owner_scoped_and_fail_closed():
    cursor = FakeCursor([(10, 1, 2, 1, 3, 2), (1,)])

    report = owner_quality_report(cursor, email="person@example.com")

    assert report == {
        "total_events": 10,
        "invalid_time_events": 1,
        "missing_governance_events": 2,
        "sensitive_leak_candidates": 1,
        "rejected_or_quarantined": 3,
        "excluded_events": 2,
        "orphaned_sensitive_records": 1,
        "quality_passed": False,
        "valid_event_ratio": 0.5,
    }
    assert all(params == ("person@example.com",) for _, params in cursor.queries)


def test_empty_owner_dataset_passes_without_division_by_zero():
    cursor = FakeCursor([(0, 0, 0, 0, 0, 0), (0,)])
    report = owner_quality_report(cursor, email="empty@example.com")
    assert report["quality_passed"] is True
    assert report["valid_event_ratio"] == 1.0
