"""Regression coverage for rate-limited request body annotations."""

import pytest

pytestmark = pytest.mark.no_db


def test_rate_limited_models_remain_json_request_bodies():
    import main

    spec = main.app.openapi()
    for path in (
        "/api/auth/email/login",
        "/api/translate-batch",
        "/api/translate",
    ):
        operation = spec["paths"][path]["post"]
        assert "requestBody" in operation, path
        assert not any(
            parameter.get("name") == "payload"
            for parameter in operation.get("parameters", [])
        ), path


def test_legacy_course_catalogue_route_is_registered():
    import main

    spec = main.app.openapi()
    operation = spec["paths"]["/api/v1/courses"]["get"]
    parameter_names = {item["name"] for item in operation.get("parameters", [])}
    assert {"page", "per_page"} <= parameter_names
