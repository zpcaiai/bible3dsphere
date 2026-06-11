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
        ("GET", "/api/admin/posts"),
        ("POST", "/api/admin/posts/{post_id}/delete"),
        ("POST", "/api/admin/posts/{post_id}/restore"),
        ("POST", "/api/admin/posts/{post_id}/pin"),
        ("POST", "/api/admin/posts/{post_id}/unpin"),
        ("GET", "/api/admin/posts/{post_id}/comments"),
        ("POST", "/api/admin/comments/{cid}/delete"),
        ("POST", "/api/admin/comments/{cid}/restore"),
        ("GET", "/api/admin/prayers"),
        ("POST", "/api/admin/prayers/{prayer_id}/delete"),
        ("POST", "/api/admin/prayers/{prayer_id}/restore"),
        ("GET", "/api/admin/voice-groups"),
        ("POST", "/api/admin/voice-groups/{gid}/delete"),
        ("GET", "/api/admin/friendships"),
        ("GET", "/api/admin/chat-messages"),
        ("GET", "/api/admin/push-subscriptions"),
        ("DELETE", "/api/admin/push-subscriptions"),
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
    "routers.books": {
        ("POST", "/api/books/mark"),
        ("GET", "/api/books/marks"),
        ("GET", "/api/books/stats"),
    },
    "routers.characters": {
        ("GET", "/api/characters"),
        ("GET", "/api/characters/stats"),
        ("GET", "/api/characters/graph"),
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
    "routers.examen": {
        ("GET", "/api/examen/today"),
        ("POST", "/api/examen"),
        ("GET", "/api/examen/history"),
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
    "routers.gratitude": {
        ("POST", "/api/gratitude"),
        ("GET", "/api/gratitude/list"),
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
        ("POST", "/api/memory/review"),
        ("DELETE", "/api/memory/verses/{vid}"),
    },
    "routers.mvfe_stats": {("GET", "/api/mvfe/stats")},
    "routers.pastoral": {("GET", "/api/pastoral/weekly")},
    "routers.pilgrim": {("GET", "/api/pilgrim/current"), ("GET", "/api/pilgrim/journey")},
    "routers.prayer": {
        ("GET", "/api/prayers"),
        ("POST", "/api/prayers"),
        ("PATCH", "/api/prayers/{prayer_id}/status"),
        ("POST", "/api/prayers/{prayer_id}/amen"),
        ("PUT", "/api/prayers/{prayer_id}"),
        ("DELETE", "/api/prayers/{prayer_id}"),
    },
    "routers.push": {
        ("GET", "/api/push/vapid-public-key"),
        ("GET", "/api/push/prefs"),
        ("POST", "/api/push/subscribe"),
        ("POST", "/api/push/prefs"),
        ("POST", "/api/push/unsubscribe"),
        ("POST", "/api/push/test"),
        ("POST", "/api/push/run-due"),
    },
    "routers.reading": {
        ("POST", "/api/reading/enroll"),
        ("GET", "/api/reading/status"),
        ("POST", "/api/reading/complete"),
        ("POST", "/api/reading/uncomplete"),
    },
    "routers.realtime": {
        ("GET", "/api/rtc/ice-servers"),
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
