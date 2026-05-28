"""
Smoke-tests that all domain routers compile and have expected routes registered.
These tests require no database connection.
"""
import importlib
import sys
import types

# ── Stub heavy dependencies so routers can be imported in isolation ───────────
for mod_name in [
    "psycopg2", "psycopg2.extras",
    "fastapi_limiter", "slowapi", "slowapi.util", "slowapi.errors",
    "bcrypt", "httpx",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)


def test_stats_router_routes():
    from routers.stats import router
    paths = {r.path for r in router.routes}
    assert "/api/stats" in paths
    assert "/api/layout" in paths
    assert "/api/history" in paths
    assert "/api/feature" in paths
    assert "/api/retrieval/evaluation" in paths


def test_verse_router_routes():
    from routers.verse import router
    paths = {r.path for r in router.routes}
    assert "/api/query" in paths
    assert "/api/guidance" in paths
    assert "/api/sermon" in paths
    assert "/api/faith-qa" in paths
    assert "/api/tts" in paths


def test_journal_router_routes():
    from routers.journal import router
    paths = {r.path for r in router.routes}
    assert "/api/devotion/journals" in paths
    assert "/api/devotion/journals/{journal_id}" in paths
    assert "/api/sermon/journals" in paths
    assert "/api/sermon/journals/{journal_id}" in paths


def test_prayer_router_routes():
    from routers.prayer import router
    paths = {r.path for r in router.routes}
    assert "/api/prayers" in paths
    assert "/api/prayers/{prayer_id}/amen" in paths
    assert "/api/prayers/{prayer_id}/status" in paths


def test_deps_module_exports():
    from core.deps import init_deps, acquire_conn, release_conn, get_settings
    assert callable(init_deps)
    assert callable(acquire_conn)
    assert callable(release_conn)
    assert callable(get_settings)
