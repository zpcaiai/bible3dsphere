import hashlib

import pytest

from backend.core import security


def test_sanitize_text_removes_dangerous_tags_and_handlers():
    value = security.sanitize_text("<script>alert(1)</script><p onclick=x>safe</p>")

    assert "script" not in value.lower()
    assert "onclick" not in value.lower()
    assert "safe" in value


def test_sanitize_text_preserves_harmless_angle_brackets():
    assert security.sanitize_text("a < b and c > b") == "a < b and c > b"


@pytest.mark.parametrize("value", ["2026-05-27", "1999-12-31"])
def test_validate_date_str_accepts_valid_dates(value):
    assert security.validate_date_str(value) == value


@pytest.mark.parametrize("value", ["2026/05/27", "2026-13-01", "2026-01-32"])
def test_validate_date_str_rejects_invalid_dates(value):
    with pytest.raises(ValueError):
        security.validate_date_str(value)


def test_hash_and_verify_password_round_trip():
    password = "testpassword123"
    stored = security.hash_password(password)

    assert security.verify_password(password, stored) is True
    assert security.verify_password("wrong", stored) is False


def test_verify_password_legacy_hash():
    password = "testpassword123"
    salt = "abcd1234efgh5678"
    digest = hashlib.sha256((salt + password).encode()).hexdigest()

    assert security.verify_password(password, f"{salt}:{digest}") is True
