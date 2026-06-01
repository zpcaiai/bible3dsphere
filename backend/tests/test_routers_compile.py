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


def test_idolatry_router_routes():
    from routers.idolatry import router
    paths = {r.path for r in router.routes}
    assert "/api/idolatry/meta" in paths
    assert "/api/idolatry/signals" in paths
    assert "/api/idolatry/assess" in paths
    assert "/api/idolatry/patterns" in paths
    assert "/api/idolatry/latest" in paths


def test_waiting_router_routes():
    from routers.waiting import router
    paths = {r.path for r in router.routes}
    assert "/api/waiting/meta" in paths
    assert "/api/waiting/cases" in paths
    assert "/api/waiting/cases/{case_id}" in paths
    assert "/api/waiting/cases/{case_id}/analyze" in paths
    assert "/api/waiting/cases/{case_id}/practices/generate" in paths
    assert "/api/waiting/cases/{case_id}/reflect" in paths
    assert "/api/waiting/practices/{practice_id}/complete" in paths


def test_pastoral_router_routes():
    from routers.pastoral import router
    paths = {r.path for r in router.routes}
    assert "/api/pastoral/weekly" in paths


def test_examen_router_routes():
    from routers.examen import router
    paths = {r.path for r in router.routes}
    assert "/api/examen/today" in paths
    assert "/api/examen" in paths
    assert "/api/examen/history" in paths


def test_push_router_routes():
    from routers.push import router
    paths = {r.path for r in router.routes}
    assert "/api/push/vapid-public-key" in paths
    assert "/api/push/subscribe" in paths
    assert "/api/push/run-due" in paths


def test_reading_router_routes():
    from routers.reading import router
    paths = {r.path for r in router.routes}
    assert "/api/reading/enroll" in paths
    assert "/api/reading/status" in paths
    assert "/api/reading/complete" in paths


def test_memory_router_routes():
    from routers.memory import router
    paths = {r.path for r in router.routes}
    assert "/api/memory/verses" in paths
    assert "/api/memory/due" in paths
    assert "/api/memory/review" in paths


def test_gratitude_router_routes():
    from routers.gratitude import router
    paths = {r.path for r in router.routes}
    assert "/api/gratitude" in paths
    assert "/api/gratitude/list" in paths


def test_accountability_router_routes():
    from routers.accountability import router
    paths = {r.path for r in router.routes}
    assert "/api/accountability/goals" in paths
    assert "/api/accountability/checkin" in paths


def test_confession_router_routes():
    from routers.confession import router
    paths = {r.path for r in router.routes}
    assert "/api/confession/record" in paths


def test_export_router_routes():
    from routers.export import router
    paths = {r.path for r in router.routes}
    assert "/api/export/me" in paths


def test_gospel_router_routes():
    from routers.gospel import router
    paths = {r.path for r in router.routes}
    assert "/api/gospel/meta" in paths
    assert "/api/gospel/diagnose" in paths
    assert "/api/gospel/history" in paths


def test_dew_router_routes():
    from routers.dew import router
    paths = {r.path for r in router.routes}
    assert "/api/dew/today" in paths


def test_checkup_router_routes():
    from routers.checkup import router
    paths = {r.path for r in router.routes}
    assert "/api/checkup/meta" in paths
    assert "/api/checkup/submit" in paths
