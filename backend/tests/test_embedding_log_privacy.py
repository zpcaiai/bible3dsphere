"""Log-boundary unit regressions with injected transport errors, not provider acceptance."""
import logging

import pytest
import requests

from mvfe.db import vector


@pytest.mark.parametrize('http_status', [404, None])
def test_provider_failure_does_not_log_credentials_or_input(monkeypatch, caplog, http_status):
    neutral_key = 'NEUTRAL_UNIT_KEY_NOT_A_CREDENTIAL'
    neutral_input = 'NEUTRAL_PRIVATE_INPUT_FIXTURE'
    neutral_token = 'NEUTRAL_UNIT_TOKEN'
    message = (
        'https://provider.invalid/embedding?key=' + neutral_key
        + '&access_token=' + neutral_token + '&input=' + neutral_input
    )
    if http_status is not None:
        response = requests.Response()
        response.status_code = http_status
        response.url = message
        error = requests.HTTPError(message, response=response)
    else:
        error = requests.ConnectionError(message)
    calls = []

    def inject_transport_error(*args, **kwargs):
        calls.append(kwargs['timeout'])
        raise error

    monkeypatch.setattr(requests, 'post', inject_transport_error)
    monkeypatch.setattr(vector, '_gemini_embed_failed', False)
    monkeypatch.setattr(vector, '_embedding_cache', {})
    embed = vector._gemini_embed_with_fallback(neutral_key)
    with caplog.at_level(logging.WARNING, logger=vector.__name__):
        actual = embed(neutral_input)
        following = embed('NEUTRAL_FOLLOWING_INPUT')

    # The real handler and existing fallback execute; no external request succeeds.
    assert calls == [15]
    assert vector._gemini_embed_failed is True
    assert actual == vector._hash_embed_fn(neutral_input)
    assert following == vector._hash_embed_fn('NEUTRAL_FOLLOWING_INPUT')
    assert len(caplog.records) == 1
    for secret in [neutral_key, neutral_token, neutral_input, 'provider.invalid']:
        assert secret not in caplog.text
        assert secret not in repr(caplog.records[0].args)
    assert type(error).__name__ in caplog.text
    if http_status is not None:
        assert str(http_status) in caplog.text
    assert caplog.records[0].exc_info is None
