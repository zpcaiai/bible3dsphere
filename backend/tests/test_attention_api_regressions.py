"""Database-backed regressions for Attention API contracts."""


def test_today_summary_resolves_local_focus_session_bounds(client, auth_headers):
    response = client.get('/api/attention/today/summary', headers=auth_headers)

    assert response.status_code == 200
    assert response.json()['date']


def test_challenge_template_endpoint_honors_english_request_language(client, auth_headers):
    response = client.get(
        '/api/attention/challenges/templates',
        headers={**auth_headers, 'X-Lang': 'en'},
    )

    assert response.status_code == 200
    for template in response.json()['templates']:
        for field in ('title', 'description', 'checkinPrompt', 'gentleGuideline'):
            assert not any('\u3400' <= char <= '\u9fff' for char in template[field])
