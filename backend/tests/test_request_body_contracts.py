"""Regression coverage for rate-limited request body annotations."""

import re

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


# ── PEP 563 + 限流 + Body 模型：这三样凑齐就会炸掉整个 OpenAPI schema ──────────

RISKY_COMBINATION = """`from __future__ import annotations` + a rate limit + a Pydantic body model"""


def _routers_with(*, postponed: bool, limited: bool, body_model: bool):
    """Find routers matching a combination of the three ingredients."""
    from pathlib import Path as _Path

    matches = []
    for path in sorted((_Path(__file__).resolve().parents[1] / "routers").glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        # 必须看真正的语句：media.py 的注释里就写着这句话，
        # 子串匹配会把「解释为什么不要它」误判成「用了它」。
        has_postponed = any(
            line.strip().startswith("from __future__ import")
            and "annotations" in line
            for line in text.splitlines()
        )
        has_limit = "limiter.limit(" in text or "@rate_limit(" in text
        has_body = re.search(r"=\s*Body\(", text) is not None
        if (has_postponed, has_limit, has_body) == (postponed, limited, body_model):
            matches.append(path.name)
    return matches


def test_no_router_combines_postponed_annotations_with_a_limited_body_model():
    """The three ingredients that broke `/openapi.json` for the entire app.

    slowapi wraps the endpoint, so FastAPI resolves the annotation *strings* against
    slowapi's namespace, where the request model does not exist. `ScriptTTSRequest`
    stayed a ForwardRef and `app.openapi()` raised — meaning no `/docs`, no schema, no
    client generation. It hid for a long time because the fallback limiter used when
    slowapi is absent returns the function unwrapped, so the failure only appears once
    the dependency is actually installed.

    `routers/media.py` was the only file with all three; it now deliberately omits the
    `__future__` import and says why. This test is what stops the next router from
    reintroducing it.
    """
    offenders = _routers_with(postponed=True, limited=True, body_model=True)
    assert offenders == [], (
        f"{offenders} combine {RISKY_COMBINATION}; drop the __future__ import "
        "(see the comment at the top of routers/media.py)"
    )


def test_the_invariant_check_is_actually_looking_at_something():
    """A guard against the scan silently matching nothing at all."""
    from pathlib import Path as _Path

    routers = list((_Path(__file__).resolve().parents[1] / "routers").glob("*.py"))
    assert len(routers) > 100, "router scan found almost nothing — glob broken?"
    # 大多数 router 确实用了 PEP 563，所以「零命中」不能是因为没人用它
    postponed_anywhere = _routers_with(postponed=True, limited=False, body_model=False)
    assert postponed_anywhere, "no router uses postponed annotations — scan is wrong"


def test_the_previously_broken_router_still_builds_its_schema():
    """Cheap, scoped version of the whole-app check so it runs on every commit."""
    from fastapi import FastAPI

    from routers.media import router

    app = FastAPI()
    app.include_router(router)
    spec = app.openapi()
    assert "/api/tts/script" in spec["paths"]
    assert "requestBody" in spec["paths"]["/api/tts/script"]["post"]


@pytest.mark.slow
def test_openapi_schema_builds_for_the_whole_app():
    """The full-app version — ~40s because it resolves 1600+ paths, so it is marked slow.

    The scoped test above is the one that runs on every commit; this one is the belt to
    its braces, for CI runs that include slow tests.
    """
    import main

    spec = main.app.openapi()
    assert len(spec["paths"]) > 1000
    assert "requestBody" in spec["paths"]["/api/tts/script"]["post"]


def test_rate_limited_endpoints_keep_a_resolvable_signature():
    import inspect

    from routers.media import tts_script

    annotation = inspect.signature(tts_script).parameters["payload"].annotation
    assert not isinstance(annotation, str), "annotation left unresolved as a string"
    assert annotation.__name__ == "ScriptTTSRequest"
