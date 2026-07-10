"""Fail-closed contracts for the optional demo account."""

import pytest

from db_schema import DEFAULT_DEMO_EMAIL, demo_user_config, has_historical_demo_password


@pytest.mark.no_db
def test_demo_user_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv('SEED_DEMO_USER', raising=False)
    monkeypatch.delenv('DEMO_USER_EMAIL', raising=False)
    monkeypatch.delenv('DEMO_USER_PASSWORD', raising=False)

    assert demo_user_config() == (False, DEFAULT_DEMO_EMAIL, '')


@pytest.mark.no_db
def test_demo_user_requires_a_strong_explicit_password(monkeypatch):
    monkeypatch.setenv('SEED_DEMO_USER', 'true')
    monkeypatch.setenv('DEMO_USER_PASSWORD', 'too-short')

    with pytest.raises(RuntimeError, match='at least 12 characters'):
        demo_user_config()


@pytest.mark.no_db
def test_demo_user_requires_a_valid_email(monkeypatch):
    monkeypatch.setenv('SEED_DEMO_USER', 'true')
    monkeypatch.setenv('DEMO_USER_EMAIL', 'not-an-email')
    monkeypatch.setenv('DEMO_USER_PASSWORD', 'unique-demo-password')

    with pytest.raises(RuntimeError, match='valid DEMO_USER_EMAIL'):
        demo_user_config()


@pytest.mark.no_db
def test_demo_user_accepts_explicit_isolated_configuration(monkeypatch):
    monkeypatch.setenv('SEED_DEMO_USER', 'true')
    monkeypatch.setenv('DEMO_USER_EMAIL', 'DEMO@EXAMPLE.COM')
    monkeypatch.setenv('DEMO_USER_PASSWORD', 'unique-demo-password')

    assert demo_user_config() == (True, 'demo@example.com', 'unique-demo-password')


@pytest.mark.no_db
def test_historical_account_is_locked_only_when_public_password_still_matches():
    assert has_historical_demo_password(
        'old-hash',
        lambda password, stored: (password, stored) == ('John', 'old-hash'),
    )
    assert not has_historical_demo_password('changed-hash', lambda _password, _stored: False)
    assert not has_historical_demo_password('', lambda _password, _stored: True)
