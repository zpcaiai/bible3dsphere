from pathlib import Path

import pytest

from mission_os.errors import ERROR_CODES, MissionError
from mission_os.pagination import PageRequest


def test_stable_error_codes_and_unknown_code_rejected():
    assert len(ERROR_CODES) == 7
    assert MissionError("MISSION_FORBIDDEN", "forbidden").code == "MISSION_FORBIDDEN"
    with pytest.raises(ValueError):
        MissionError("UNKNOWN", "bad")


def test_pagination_rejects_arbitrary_sort_and_unbounded_limit():
    allowed = frozenset({"created_at", "risk_level"})
    assert PageRequest(sort="risk_level").validate(allowed).limit == 50
    with pytest.raises(ValueError):
        PageRequest(sort="summary").validate(allowed)
    with pytest.raises(ValueError):
        PageRequest(limit=1000).validate(allowed)


def test_generator_refuses_overwrite_and_invalid_names(tmp_path: Path):
    import sys
    sys.path.insert(0, str(Path(__file__).parents[2] / "scripts" / "mission_os"))
    from create_skill_module import generate

    created = generate(tmp_path, "field_notes")
    assert {p.name for p in created} >= {"domain.py", "repository.py", "service.py"}
    with pytest.raises(FileExistsError):
        generate(tmp_path, "field_notes")
    with pytest.raises(ValueError):
        generate(tmp_path, "../escape")
