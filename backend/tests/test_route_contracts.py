"""Route contract coverage for the modular FastAPI routers.

These tests intentionally avoid database calls. They catch accidental endpoint
removal, method changes, router import breakage, and untracked app-level route
duplication while service-level tests cover handler behavior.
"""
import importlib
import sys
import types
from collections import Counter

import pytest
from fastapi.routing import APIRoute

pytestmark = pytest.mark.no_db

for mod_name in [
    "psycopg2",
    "psycopg2.extras",
    "fastapi_limiter",
    "slowapi",
    "slowapi.util",
    "slowapi.errors",
    "bcrypt",
    "httpx",
]:
    if mod_name not in sys.modules:
        try:
            __import__(mod_name)
        except ImportError:
            sys.modules[mod_name] = types.ModuleType(mod_name)


EXPECTED_ROUTER_ROUTES = {
    "routers.accountability": {
        ("GET", "/api/accountability/goals"),
        ("POST", "/api/accountability/goals"),
        ("POST", "/api/accountability/checkin"),
        ("DELETE", "/api/accountability/goals/{gid}"),
    },
    "routers.admin_catalog": {
        ("GET", "/api/admin/seekers-courses"),
        ("POST", "/api/admin/seekers-courses"),
        ("PUT", "/api/admin/seekers-courses/{course_id}"),
        ("DELETE", "/api/admin/seekers-courses/{course_id}"),
        ("GET", "/api/admin/seekers-courses/r2-files"),
        ("GET", "/api/admin/sunday-school-videos"),
        ("POST", "/api/admin/sunday-school-videos"),
        ("PUT", "/api/admin/sunday-school-videos/{vid}"),
        ("DELETE", "/api/admin/sunday-school-videos/{vid}"),
        ("GET", "/api/admin/dew"),
        ("GET", "/api/admin/dew/{date}/{tier}"),
        ("DELETE", "/api/admin/dew/{date}/{tier}"),
        ("GET", "/api/admin/hymns/r2-files"),
        ("GET", "/api/admin/books/marks-stats"),
        ("GET", "/api/admin/disciple/profiles"),
        ("GET", "/api/admin/disciple/assessments"),
        ("GET", "/api/admin/disciple/relationships"),
        ("POST", "/api/admin/disciple/relationships/{rel_id}/end"),
        ("GET", "/api/admin/examen"),
        ("GET", "/api/admin/examen/{entry_id}"),
        ("GET", "/api/admin/checkups"),
        ("GET", "/api/admin/gospel-diagnoses"),
        ("GET", "/api/admin/agent-runs"),
        ("GET", "/api/admin/domain-events"),
    },
    "routers.admin_content": {
        ("DELETE", "/api/admin/gratitude-entries/{gid}"),
        ("DELETE", "/api/admin/memory-verses/{vid}"),
        ("DELETE", "/api/admin/push-subscriptions"),
        ("GET", "/api/admin/bible-reading-progress"),
        ("GET", "/api/admin/chat-messages"),
        ("GET", "/api/admin/checkins"),
        ("GET", "/api/admin/devotion-journals"),
        ("GET", "/api/admin/friendships"),
        ("GET", "/api/admin/gratitude-entries"),
        ("GET", "/api/admin/guardian/emotions"),
        ("GET", "/api/admin/guardian/messages"),
        ("GET", "/api/admin/guardian/prayers"),
        ("GET", "/api/admin/guardian/spiritual-checkins"),
        ("GET", "/api/admin/habits"),
        ("GET", "/api/admin/habits/{habit_id}/executions"),
        ("GET", "/api/admin/memory-verses"),
        ("GET", "/api/admin/posts"),
        ("GET", "/api/admin/posts/{post_id}/comments"),
        ("GET", "/api/admin/prayers"),
        ("GET", "/api/admin/push-subscriptions"),
        ("GET", "/api/admin/reading-enrollments"),
        ("GET", "/api/admin/reading-progress"),
        ("GET", "/api/admin/recycle-bin"),
        ("GET", "/api/admin/sermon-journals"),
        ("GET", "/api/admin/shared-notes"),
        ("GET", "/api/admin/testimonies"),
        ("GET", "/api/admin/voice-groups"),
        ("POST", "/api/admin/comments/{cid}/delete"),
        ("POST", "/api/admin/comments/{cid}/restore"),
        ("POST", "/api/admin/devotion-journals/{jid}/delete"),
        ("POST", "/api/admin/devotion-journals/{jid}/restore"),
        ("POST", "/api/admin/posts/{post_id}/delete"),
        ("POST", "/api/admin/posts/{post_id}/pin"),
        ("POST", "/api/admin/posts/{post_id}/restore"),
        ("POST", "/api/admin/posts/{post_id}/unpin"),
        ("POST", "/api/admin/prayers/{prayer_id}/delete"),
        ("POST", "/api/admin/prayers/{prayer_id}/restore"),
        ("POST", "/api/admin/recycle-bin/{item_type}/{item_id}/restore"),
        ("POST", "/api/admin/sermon-journals/{jid}/delete"),
        ("POST", "/api/admin/sermon-journals/{jid}/restore"),
        ("POST", "/api/admin/shared-notes/{note_id}/unshare"),
        ("POST", "/api/admin/testimonies/{tid}/delete"),
        ("POST", "/api/admin/testimonies/{tid}/restore"),
        ("POST", "/api/admin/voice-groups/{gid}/delete"),
    },
    "routers.admin_ops": {
        ("GET", "/api/admin/analytics/engagement-series"),
        ("GET", "/api/admin/analytics/feature-adoption"),
        ("GET", "/api/admin/analytics/overview"),
        ("GET", "/api/admin/billing/summary"),
        ("GET", "/api/admin/plans"),
        ("GET", "/api/admin/subscriptions"),
        ("POST", "/api/admin/subscriptions/{sid}/change-plan"),
        ("POST", "/api/admin/subscriptions/{sid}/set-status"),
        ("GET", "/api/admin/verse-feedback"),
        ("GET", "/api/admin/verse-feedback/top"),
    },
    "routers.admin_users": {
        ("GET", "/api/admin/dashboard"),
        ("GET", "/api/admin/users"),
        ("GET", "/api/admin/users/{email}"),
        ("POST", "/api/admin/users/{email}/ban"),
        ("POST", "/api/admin/users/{email}/unban"),
        ("POST", "/api/admin/users/{email}/set-admin"),
        ("POST", "/api/admin/users/{email}/reset-password"),
        ("GET", "/api/admin/churches"),
        ("GET", "/api/admin/churches/{cid}/members"),
        ("POST", "/api/admin/churches/{cid}/rename"),
        ("POST", "/api/admin/churches/{cid}/toggle-active"),
        ("POST", "/api/admin/churches/{cid}/regenerate-code"),
        ("POST", "/api/admin/churches/{cid}/dissolve"),
        ("GET", "/api/admin/audit-log"),
    },
    "routers.agent": {("GET", "/api/agent/meta"), ("POST", "/api/agent/chat")},
    "routers.bible_map": {
        ("GET", "/api/bible-map/territories"),
        ("GET", "/api/bible-map/territories/at"),
        ("GET", "/api/bible-map/events"),
        ("GET", "/api/bible-map/prophecies"),
        ("GET", "/api/bible-map/campaigns"),
        ("GET", "/api/bible-map/graph"),
        ("POST", "/api/bible-map/ai"),
    },
    "routers.bible_search": {
        ("GET", "/api/bible/search"),
    },
    "routers.books": {
        ("POST", "/api/books/mark"),
        ("GET", "/api/books/marks"),
        ("GET", "/api/books/stats"),
    },
    "routers.characters": {
        ("GET", "/api/characters"),
        ("GET", "/api/characters/stats"),
        ("GET", "/api/characters/graph"),
        ("GET", "/api/characters/knowledge-graph"),
        ("GET", "/api/characters/relationship-types"),
        ("GET", "/api/characters/subgraphs"),
        ("GET", "/api/characters/subgraphs/{slug}"),
        ("GET", "/api/characters/{identifier}/relationships"),
        ("GET", "/api/characters/{identifier}"),
    },
    "routers.checkup": {
        ("GET", "/api/checkup/meta"),
        ("POST", "/api/checkup/submit"),
        ("GET", "/api/checkup/history"),
    },
    "routers.church": {
        ("GET", "/api/church/me"),
        ("POST", "/api/church/create"),
        ("POST", "/api/church/join"),
        ("GET", "/api/church/members"),
        ("POST", "/api/church/regenerate-code"),
        ("POST", "/api/church/leave"),
    },
    "routers.church_integration": {
        ("POST", "/api/church-integration/connections"),
        ("GET", "/api/church-integration/connections/current"),
        ("POST", "/api/church-integration/recommend"),
        ("POST", "/api/church-integration/rhythms"),
        ("GET", "/api/church-integration/rhythms"),
        ("POST", "/api/church-integration/checkins"),
        ("POST", "/api/church-integration/reentry-plans"),
        ("GET", "/api/church-integration/profiles"),
        ("POST", "/api/church-integration/profiles"),
    },
    "routers.community": {("GET", "/api/community/emotion-heatmap")},
    "routers.community_feed": {
        ("GET", "/api/community/feed"),
        ("POST", "/api/community/feed"),
        ("DELETE", "/api/community/feed/{post_id}"),
        ("POST", "/api/community/feed/{post_id}/amen"),
        ("GET", "/api/community/feed/{post_id}/comments"),
        ("POST", "/api/community/feed/{post_id}/comments"),
        ("DELETE", "/api/community/feed/comments/{comment_id}"),
    },
    "routers.confession": {("POST", "/api/confession/record")},
    "routers.dew": {("GET", "/api/dew/today")},
    "routers.discipleship": {
        ("GET", "/api/discipleship/stages"),
        ("POST", "/api/discipleship/assessments"),
        ("POST", "/api/discipleship/recommend"),
        ("POST", "/api/discipleship/paths"),
        ("GET", "/api/discipleship/paths/active"),
        ("POST", "/api/discipleship/paths/{pid}/steps"),
        ("PATCH", "/api/discipleship/steps/{sid}"),
        ("POST", "/api/discipleship/paths/{pid}/review"),
    },
    "routers.discern": {
        ("GET", "/api/discern/meta"),
        ("POST", "/api/discern/run"),
        ("GET", "/api/discern/history"),
    },
    "routers.disciple": {
        ("GET", "/api/disciple/meta"),
        ("GET", "/api/disciple/profile"),
        ("GET", "/api/disciple/review/{kind}"),
        ("GET", "/api/disciple/graph"),
        ("GET", "/api/disciple/milestones"),
        ("POST", "/api/disciple/cron/notify"),
        ("POST", "/api/disciple/cron/worker"),
        ("POST", "/api/disciple/assess"),
        ("GET", "/api/disciple/history"),
        ("POST", "/api/disciple/mentor"),
        ("GET", "/api/disciple/network"),
        ("POST", "/api/disciple/network"),
        ("POST", "/api/disciple/network/{rel_id}/end"),
    },
    "routers.gift_calling": {
        ("GET", "/api/gift/meta"),
        ("GET", "/api/gift/profile"),
        ("POST", "/api/gift/assess"),
        ("GET", "/api/gift/history"),
        ("GET", "/api/gift/assessment/{aid}"),
        ("POST", "/api/gift/feedback"),
        ("GET", "/api/gift/feedback"),
        ("POST", "/api/gift/review"),
        ("GET", "/api/gift/review"),
    },
    "routers.batch1_4": {
        ("GET", "/api/spiritual-formation/batch1-4/meta"),
        ("POST", "/api/spiritual-formation/batch1-4/orchestrate"),
        ("POST", "/api/spiritual-formation/batch1-4/records/{domain}/{record_type}"),
        ("GET", "/api/spiritual-formation/batch1-4/records/{domain}/{record_type}"),
        ("GET", "/api/spiritual-formation/batch1-4/records/{domain}/{record_type}/{record_id}"),
        ("DELETE", "/api/spiritual-formation/batch1-4/records/{domain}/{record_type}/{record_id}"),
        ("GET", "/api/spiritual-formation/batch1-4/summary"),
    },
    "routers.accountability_group": {
        ("POST", "/api/accountability-group/groups"),
        ("GET", "/api/accountability-group/groups"),
        ("GET", "/api/accountability-group/groups/{gid}"),
        ("POST", "/api/accountability-group/groups/{gid}/members"),
        ("POST", "/api/accountability-group/groups/{gid}/goals"),
        ("GET", "/api/accountability-group/groups/{gid}/goals"),
        ("POST", "/api/accountability-group/groups/{gid}/checkins"),
        ("GET", "/api/accountability-group/groups/{gid}/checkins"),
        ("POST", "/api/accountability-group/groups/{gid}/prayer-requests"),
        ("GET", "/api/accountability-group/groups/{gid}/prayer-requests"),
        ("POST", "/api/accountability-group/groups/{gid}/review"),
    },
    "routers.mentor": {
        ("POST", "/api/mentor/relationships"),
        ("GET", "/api/mentor/relationships"),
        ("PATCH", "/api/mentor/relationships/{rid}"),
        ("POST", "/api/mentor/relationships/{rid}/sessions"),
        ("GET", "/api/mentor/relationships/{rid}/sessions"),
        ("PATCH", "/api/mentor/sessions/{sid}"),
        ("POST", "/api/mentor/relationships/{rid}/observations"),
        ("GET", "/api/mentor/relationships/{rid}/observations"),
        ("GET", "/api/mentor/questions"),
        ("POST", "/api/mentor/recommend"),
        ("POST", "/api/mentor/relationships/{rid}/action-plans"),
        ("GET", "/api/mentor/relationships/{rid}/action-plans"),
        ("POST", "/api/mentor/relationships/{rid}/review"),
    },
    "routers.examen": {
        ("GET", "/api/examen/today"),
        ("POST", "/api/examen"),
        ("GET", "/api/examen/history"),
    },
    "routers.fasting": {
        ("GET", "/api/fasting/practices"),
        ("POST", "/api/fasting/recommend"),
        ("POST", "/api/fasting/plans"),
        ("GET", "/api/fasting/plans/active"),
        ("PATCH", "/api/fasting/plans/{pid}"),
        ("POST", "/api/fasting/plans/{pid}/checkins"),
        ("POST", "/api/fasting/plans/{pid}/review"),
        ("POST", "/api/fasting/simplicity/audit"),
        ("GET", "/api/fasting/simplicity/audit/latest"),
        ("POST", "/api/fasting/simplicity/actions"),
        ("PATCH", "/api/fasting/simplicity/actions/{aid}"),
    },
    "routers.fruit": {
        ("GET", "/api/fruit/dimensions"),
        ("POST", "/api/fruit/assessments"),
        ("GET", "/api/fruit/assessments"),
        ("GET", "/api/fruit/latest"),
        ("GET", "/api/fruit/trends"),
        ("POST", "/api/fruit/insights"),
    },
    "routers.formation_advanced": {
        ("GET", "/api/formation-advanced/meta"),
        ("GET", "/api/formation-advanced/bible-doctrine/topics"),
        ("POST", "/api/formation-advanced/bible-doctrine/paths"),
        ("GET", "/api/formation-advanced/bible-doctrine/paths/active"),
        ("POST", "/api/formation-advanced/bible-doctrine/paths/{path_id}/progress"),
        ("GET", "/api/formation-advanced/bible-doctrine/graph/search"),
        ("POST", "/api/formation-advanced/bible-doctrine/apologetics/dialogues"),
        ("GET", "/api/formation-advanced/bible-doctrine/apologetics/dialogues"),
        ("POST", "/api/formation-advanced/formation-agent/profiles"),
        ("GET", "/api/formation-advanced/formation-agent/profile"),
        ("POST", "/api/formation-advanced/formation-agent/recommendations"),
        ("POST", "/api/formation-advanced/formation-agent/conversations"),
        ("GET", "/api/formation-advanced/formation-agent/conversations"),
        ("POST", "/api/formation-advanced/analytics/snapshots"),
        ("GET", "/api/formation-advanced/analytics/dashboard"),
        ("POST", "/api/formation-advanced/analytics/reports"),
        ("GET", "/api/formation-advanced/analytics/reports"),
        ("POST", "/api/formation-advanced/analytics/integrity-audits"),
        ("POST", "/api/formation-advanced/productization/tenants"),
        ("GET", "/api/formation-advanced/productization/tenants"),
        ("POST", "/api/formation-advanced/productization/tenants/{tenant_id}/members"),
        ("GET", "/api/formation-advanced/productization/subscription-plans"),
        ("POST", "/api/formation-advanced/productization/subscriptions"),
        ("POST", "/api/formation-advanced/productization/moderation-cases"),
        ("GET", "/api/formation-advanced/productization/deployment-health"),
        ("GET", "/api/formation-advanced/master-build/registry"),
        ("POST", "/api/formation-advanced/master-build/runs"),
        ("GET", "/api/formation-advanced/master-build/runs"),
        ("POST", "/api/formation-advanced/master-build/acceptance-checks"),
        ("GET", "/api/formation-advanced/master-build/acceptance-matrix"),
    },
    "routers.export": {("GET", "/api/export/me")},
    "routers.feedback": {
        ("POST", "/api/feedback/verse"),
        ("GET", "/api/feedback/verse"),
        ("GET", "/api/feedback/preference-preview"),
    },
    "routers.film_studio": {
        ("POST", "/api/film/start"),
        ("POST", "/api/film/start-ppt"),
        ("GET", "/api/film/status/{jid}"),
        ("GET", "/api/film/sse/{jid}"),
        ("GET", "/api/film/download/{fname}"),
        ("GET", "/film-clips/{fname}"),
        ("GET", "/film-studio"),
    },
    "routers.fuel": {("GET", "/api/fuel/meta"), ("GET", "/api/fuel/pack/{key}")},
    "routers.geo": {
        ("GET", "/api/geo/scripture"),
        ("GET", "/api/geo/entity"),
        ("GET", "/api/geo/routes/{route_name}"),
        ("GET", "/api/geo/paul"),
        ("GET", "/api/geo/timeline"),
        ("GET", "/api/geo/regions"),
        ("GET", "/api/geo/relations"),
        ("GET", "/api/geo/landmarks"),
        ("GET", "/api/geo/exodus"),
    },
    "routers.gospel": {
        ("GET", "/api/gospel/meta"),
        ("POST", "/api/gospel/diagnose"),
        ("GET", "/api/gospel/history"),
    },
    "routers.spiritual_formation": {
        ("GET", "/api/spiritual-formation/meta"),
        ("POST", "/api/spiritual-formation/recommend"),
        ("POST", "/api/spiritual-formation/generate-plan"),
        ("POST", "/api/spiritual-formation/daily-examens"),
        ("GET", "/api/spiritual-formation/daily-examens"),
        ("GET", "/api/spiritual-formation/daily-examens/{entry_id}"),
        ("DELETE", "/api/spiritual-formation/daily-examens/{entry_id}"),
        ("POST", "/api/spiritual-formation/thought-captive"),
        ("GET", "/api/spiritual-formation/thought-captive"),
        ("POST", "/api/spiritual-formation/grace-recovery"),
        ("GET", "/api/spiritual-formation/grace-recovery"),
        ("POST", "/api/spiritual-formation/plans"),
        ("GET", "/api/spiritual-formation/plans"),
        ("GET", "/api/spiritual-formation/plans/active"),
        ("PUT", "/api/spiritual-formation/plans/{plan_id}"),
        ("POST", "/api/spiritual-formation/holy-life/day-logs"),
        ("GET", "/api/spiritual-formation/holy-life/day-logs"),
        ("GET", "/api/spiritual-formation/holy-life/today"),
        ("GET", "/api/spiritual-formation/holy-life/day-logs/{log_id}"),
        ("DELETE", "/api/spiritual-formation/holy-life/day-logs/{log_id}"),
        ("GET", "/api/spiritual-formation/holy-life/horarium/day-logs"),
        ("GET", "/api/spiritual-formation/holy-life/horarium/hours"),
        ("GET", "/api/spiritual-formation/holy-life/horarium/streak"),
        ("GET", "/api/spiritual-formation/holy-life/horarium/today"),
        ("POST", "/api/spiritual-formation/holy-life/horarium/day-logs"),
        ("POST", "/api/spiritual-formation/holy-life/purpose-review"),
        ("POST", "/api/spiritual-formation/holy-life/rule-of-life"),
        ("GET", "/api/spiritual-formation/holy-life/summary"),
        ("GET", "/api/spiritual-formation/weekly-review"),
        ("GET", "/api/spiritual-formation/fruit-progress"),
        ("GET", "/api/spiritual-formation/new-creation-map"),
    },
    "routers.sabbath": {
        ("POST", "/api/sabbath/plans"),
        ("GET", "/api/sabbath/plans/active"),
        ("PATCH", "/api/sabbath/plans/{pid}"),
        ("POST", "/api/sabbath/sessions"),
        ("PATCH", "/api/sabbath/sessions/{sid}"),
        ("POST", "/api/sabbath/audit"),
        ("GET", "/api/sabbath/audit/latest"),
        ("POST", "/api/sabbath/boundaries"),
        ("GET", "/api/sabbath/boundaries"),
        ("GET", "/api/sabbath/recommend"),
    },
    "routers.gratitude": {
        ("POST", "/api/gratitude"),
        ("GET", "/api/gratitude/list"),
        ("GET", "/api/gratitude/review"),
        ("DELETE", "/api/gratitude/{gid}"),
    },
    "routers.guardian": {
        ("POST", "/api/guardian/message"),
        ("POST", "/api/guardian/checkin/emotion"),
        ("POST", "/api/guardian/checkin/spiritual"),
        ("POST", "/api/guardian/prayer"),
        ("GET", "/api/guardian/prayer"),
        ("POST", "/api/guardian/devotion"),
        ("GET", "/api/guardian/devotion"),
        ("GET", "/api/guardian/profile"),
        ("GET", "/api/guardian/state"),
        ("GET", "/api/guardian/memories"),
        ("GET", "/api/guardian/insights"),
        ("GET", "/api/guardian/push-prefs"),
        ("POST", "/api/guardian/push-prefs"),
    },
    "routers.idolatry": {
        ("GET", "/api/idolatry/meta"),
        ("GET", "/api/idolatry/signals"),
        ("POST", "/api/idolatry/assess"),
        ("GET", "/api/idolatry/patterns"),
        ("GET", "/api/idolatry/latest"),
    },
    "routers.journal": {
        ("GET", "/api/devotion/journals"),
        ("POST", "/api/devotion/journals"),
        ("GET", "/api/devotion/journals/{journal_id}"),
        ("DELETE", "/api/devotion/journals/{journal_id}"),
    },
    "routers.memory": {
        ("POST", "/api/memory/verses"),
        ("GET", "/api/memory/due"),
        ("GET", "/api/memory/list"),
        ("GET", "/api/memory/milestones"),
        ("POST", "/api/memory/review"),
        ("DELETE", "/api/memory/verses/{vid}"),
    },
    "routers.mvfe_stats": {("GET", "/api/mvfe/stats")},
    "routers.pastoral": {("GET", "/api/pastoral/weekly")},
    "routers.pilgrim": {("GET", "/api/pilgrim/current"), ("GET", "/api/pilgrim/journey")},
    "routers.prayer": {
        ("DELETE", "/api/prayers/{prayer_id}"),
        ("GET", "/api/prayer-share/{share_token}"),
        ("GET", "/api/prayers"),
        ("PATCH", "/api/prayers/{prayer_id}/status"),
        ("POST", "/api/prayer-share/{share_token}/amen"),
        ("POST", "/api/prayers"),
        ("POST", "/api/prayers/{prayer_id}/amen"),
        ("POST", "/api/prayers/{prayer_id}/share"),
        ("PUT", "/api/prayers/{prayer_id}"),
    },
    "routers.push": {
        ("GET", "/api/push/vapid-public-key"),
        ("GET", "/api/push/prefs"),
        ("POST", "/api/push/subscribe"),
        ("POST", "/api/push/prefs"),
        ("POST", "/api/push/unsubscribe"),
        ("POST", "/api/push/test"),
        ("POST", "/api/push/run-due"),
        ("POST", "/api/push/fcm/register"),
        ("POST", "/api/push/fcm/unregister"),
        ("GET", "/api/push/fcm/status"),
    },
    "routers.reading": {
        ("POST", "/api/reading/enroll"),
        ("GET", "/api/reading/status"),
        ("POST", "/api/reading/complete"),
        ("POST", "/api/reading/uncomplete"),
    },
    "routers.realtime": {
        ("GET", "/api/rtc/ice-servers"),
        ("POST", "/api/rtc/ws-ticket"),
        ("GET", "/api/friends"),
        ("POST", "/api/friends/request"),
        ("POST", "/api/friends/accept"),
        ("POST", "/api/friends/remove"),
        ("GET", "/api/chat/history"),
        ("POST", "/api/chat/read"),
        ("POST", "/api/chat/recall"),
        ("GET", "/api/groups/{gid}/chat"),
        ("POST", "/api/groups/{gid}/chat"),
        ("POST", "/api/groups/{gid}/chat/recall"),
    },
    "routers.speech": {
        ("POST", "/api/speech/transcribe"),
    },
    "routers.stats": {
        ("GET", "/api/stats"),
        ("POST", "/api/stats/track"),
        ("GET", "/api/layout"),
        ("GET", "/api/history"),
        ("GET", "/api/feature"),
        ("GET", "/api/retrieval/evaluation"),
    },
    "routers.verse": {
        ("POST", "/api/query"),
        ("POST", "/api/guidance"),
        ("POST", "/api/biblical-example"),
        ("POST", "/api/verse-prayer"),
        ("POST", "/api/meditation-questions"),
        ("POST", "/api/translate"),
        ("POST", "/api/sermon"),
        ("POST", "/api/faith-qa"),
        ("POST", "/api/punctuation"),
        ("POST", "/api/tts"),
    },
    "routers.virtues": {("POST", "/api/virtues/evaluate")},
    "routers.voice": {
        ("GET", "/api/voice/config"),
        ("GET", "/api/voice/groups"),
        ("POST", "/api/voice/groups"),
        ("POST", "/api/voice/groups/join"),
        ("POST", "/api/voice/direct/token"),
        ("GET", "/api/voice/groups/{gid}/members"),
        ("POST", "/api/voice/groups/{gid}/token"),
        ("POST", "/api/voice/groups/{gid}/leave"),
        ("DELETE", "/api/voice/groups/{gid}"),
    },
    "routers.waiting": {
        ("GET", "/api/waiting/meta"),
        ("GET", "/api/waiting/cases"),
        ("POST", "/api/waiting/cases"),
        ("POST", "/api/waiting/cases/{case_id}/analyze"),
        ("POST", "/api/waiting/cases/{case_id}/practices/generate"),
        ("GET", "/api/waiting/cases/{case_id}"),
        ("POST", "/api/waiting/cases/{case_id}/reflect"),
        ("POST", "/api/waiting/practices/{practice_id}/complete"),
    },
}


KNOWN_APP_DUPLICATES = {
    ("GET", "/api/devotion/journals"),
    ("POST", "/api/devotion/journals"),
    ("GET", "/api/devotion/journals/{journal_id}"),
    ("DELETE", "/api/devotion/journals/{journal_id}"),
    ("GET", "/api/stats"),
    ("POST", "/api/stats/track"),
    ("GET", "/api/layout"),
    ("POST", "/api/translate"),
    ("GET", "/api/history"),
    ("GET", "/api/feature"),
    ("GET", "/api/retrieval/evaluation"),
    ("POST", "/api/guidance"),
    ("POST", "/api/biblical-example"),
    ("POST", "/api/verse-prayer"),
    ("POST", "/api/punctuation"),
    ("POST", "/api/meditation-questions"),
    ("POST", "/api/query"),
    ("POST", "/api/sermon"),
    ("POST", "/api/faith-qa"),
    ("POST", "/api/tts"),
    ("GET", "/film-studio"),
}


def route_contract(router):
    return {
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }


@pytest.mark.parametrize("module_name, expected", sorted(EXPECTED_ROUTER_ROUTES.items()))
def test_router_route_contract(module_name, expected):
    module = importlib.import_module(module_name)
    assert hasattr(module, "router")
    assert route_contract(module.router) == expected


def test_all_expected_router_routes_are_registered_on_main_app():
    import main

    app_routes = route_contract(main.app)
    expected_routes = set().union(*EXPECTED_ROUTER_ROUTES.values())

    assert expected_routes <= app_routes


def test_legacy_search_post_route_is_registered_on_main_app():
    import main

    assert ("POST", "/api/search") in route_contract(main.app)


def test_legacy_search_post_does_not_validate_body_before_handler():
    from routers import bible_search

    route = next(
        route
        for route in bible_search.compat_router.routes
        if isinstance(route, APIRoute) and route.path == "/api/search"
    )

    assert route.dependant.body_params == []


def test_legacy_search_decodes_old_payload_shapes():
    from routers import bible_search

    assert bible_search._decode_compat_body(b'{"query": "light", "top": "2", "lang": "esv"}') == {
        "query": "light",
        "top": "2",
        "lang": "esv",
    }
    assert bible_search._decode_compat_body(b'"{\\"query\\": \\"hope\\", \\"top\\": 1}"') == {
        "query": "hope",
        "top": 1,
    }
    assert bible_search._decode_compat_body("希望与平安".encode()) == {"query": "希望与平安"}


@pytest.mark.asyncio
async def test_legacy_search_post_accepts_old_payload_keys(monkeypatch):
    from routers import bible_search

    monkeypatch.setattr(bible_search, "_semantic_search", lambda q, lang, top: None)
    monkeypatch.setattr(
        bible_search,
        "_keyword_search",
        lambda q, top: [{"pkId": "GEN.1.1", "query": q, "top": top}],
    )

    handler = getattr(bible_search.search_compat, "__wrapped__", bible_search.search_compat)
    class RequestStub:
        async def body(self):
            return b'{"query": "light", "top": "2", "lang": "esv"}'

    response = await handler(
        request=RequestStub(),
        q=None,
    )

    assert response == {
        "success": True,
        "data": [{"pkId": "GEN.1.1", "query": "light", "top": 2}],
        "source": "keyword",
    }


def test_main_app_has_no_untracked_duplicate_routes():
    import main

    route_keys = [
        (method, route.path)
        for route in main.app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    ]
    duplicates = {key for key, count in Counter(route_keys).items() if count > 1}

    assert duplicates <= KNOWN_APP_DUPLICATES


@pytest.mark.parametrize("path", ["/api/translate", "/api/punctuation", "/api/tts"])
def test_limited_verse_post_routes_keep_payload_in_request_body(path):
    from routers.verse import router

    route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path == path
    )
    body_params = {param.name for param in route.dependant.body_params}
    query_params = {param.name for param in route.dependant.query_params}

    assert "payload" in body_params
    assert "payload" not in query_params
