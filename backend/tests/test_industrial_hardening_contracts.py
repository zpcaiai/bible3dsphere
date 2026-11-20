"""Industrial backend hardening contracts: stdlib AST/SQL contracts + live PostgreSQL 17 integration tests.

Designed so that:
1. Stdlib `unittest` discovery (`ai_progress_sync.py verify`) runs `TestIndustrialHardeningDpContracts`
   with zero external runtime assumptions, zero skips, and zero hardcoded ports.
2. `pytest` runs BOTH `TestIndustrialHardeningDpContracts` AND all real PostgreSQL 17 + FastAPI
   HTTP integration tests (`test_pg_01_*` .. `test_pg_06_*`) against live PostgreSQL 17 with 0 skips.
"""
from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import unittest
import uuid


BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
ROUTERS_DIR = BACKEND_DIR / "routers"


class TestIndustrialHardeningDpContracts(unittest.TestCase):
    """Stdlib AST and migration checksum/structure contracts across Slices 1-7."""

    def test_01_additive_migration_0249_and_immutable_prior_checksums(self):
        m0245 = (MIGRATIONS_DIR / "0245_social_safety.sql").read_text(encoding="utf-8")
        m0246 = (MIGRATIONS_DIR / "0246_account_deletion_requests.sql").read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(m0245.encode("utf-8")).hexdigest(),
            "fc3e84c602dc59522004c37d95a187ffbff23a78a7a218c9b8f715186a3fd99a",
        )
        self.assertEqual(
            hashlib.sha256(m0246.encode("utf-8")).hexdigest(),
            "18617dfde727a09d0aeec92b9bc43d79e00d9a53ca9c273b5a2c2bd71fc62c84",
        )

        m0249_path = MIGRATIONS_DIR / "0249_industrial_erasure_and_safety_indexes.sql"
        self.assertTrue(m0249_path.is_file())
        m0249 = m0249_path.read_text(encoding="utf-8")
        for token in (
            "CREATE OR REPLACE FUNCTION erase_user_data(p_email text)",
            "FOR UPDATE",
            "DELETE FROM user_tokens WHERE lower(email) = v_email",
            "friendships",
            "chat_messages",
            "group_messages",
            "voice_groups",
            "direct_voice_rooms",
            "user_blocks",
            "social_reports",
            "CREATE OR REPLACE FUNCTION erasure_coverage_gaps()",
            "idx_user_blocks_pair",
            "idx_direct_voice_rooms_pair",
            "idx_account_deletion_requests_status",
            "idx_prayers_share_token",
            "fk_ordo_amoris_entries_user_email",
            "chk_attention_focus_actual_minutes",
        ):
            self.assertIn(token, m0249)

    def test_02_session_revocation_deletion_gating_and_ordo_tx_custody_ast(self):
        main_src = (BACKEND_DIR / "main.py").read_text(encoding="utf-8")
        auth_src = (ROUTERS_DIR / "main_extracted_auth_email.py").read_text(encoding="utf-8")
        ordo_src = (ROUTERS_DIR / "ordo_amoris_augustine.py").read_text(encoding="utf-8")

        for src in (main_src, auth_src, ordo_src):
            self.assertIsInstance(ast.parse(src), ast.Module)

        self.assertIn("DELETE FROM user_tokens WHERE LOWER(email) = LOWER(%s)", auth_src)
        self.assertIn("account_deletion_requests", main_src)
        self.assertIn("'processing', 'completed'", main_src)
        self.assertNotIn("'/api/rtc/ws-ticket'", main_src.split("startup_safe_paths", 1)[1][:400])
        self.assertIn("FOR SHARE OF u", ordo_src)
        self.assertIn("Session expired or revoked", ordo_src)

    def test_03_sermon_owner_isolation_and_personal_search_6_sources_ast(self):
        sermon_src = (ROUTERS_DIR / "main_extracted_sermon.py").read_text(encoding="utf-8")
        search_src = (ROUTERS_DIR / "personal_store.py").read_text(encoding="utf-8")

        self.assertIsInstance(ast.parse(sermon_src), ast.Module)
        self.assertIsInstance(ast.parse(search_src), ast.Module)

        self.assertIn("FROM sermon_journals WHERE email = %s AND deleted_at IS NULL", sermon_src)
        self.assertIn("WHERE id = %s AND (email = %s OR %s) AND deleted_at IS NULL", sermon_src)
        self.assertIn('@router.get("/personal/search")', search_src)
        self.assertIn('@router.get("/personal-search")', search_src)
        self.assertIn("ILIKE %s ESCAPE", search_src)
        self.assertIn("LATERAL jsonb_array_elements(", search_src)
        for source_name in ("devotion", "personal_note", "sermon", "prayer", "minutes", "memory"):
            self.assertIn(f'"{source_name}"', search_src)

    def test_04_mutual_block_sql_predicates_and_prayer_ddl_cleanup_ast(self):
        notes_src = (ROUTERS_DIR / "personal_notes.py").read_text(encoding="utf-8")
        evan_src = (ROUTERS_DIR / "evangelism.py").read_text(encoding="utf-8")
        voice_src = (ROUTERS_DIR / "voice.py").read_text(encoding="utf-8")
        rt_src = (ROUTERS_DIR / "realtime.py").read_text(encoding="utf-8")
        feed_src = (ROUTERS_DIR / "community_feed.py").read_text(encoding="utf-8")
        prayer_src = (ROUTERS_DIR / "prayer.py").read_text(encoding="utf-8")

        for src in (notes_src, evan_src, voice_src, rt_src, feed_src, prayer_src):
            self.assertIsInstance(ast.parse(src), ast.Module)

        self.assertIn("FROM user_blocks b", notes_src)
        self.assertIn("FROM user_blocks b", evan_src)
        self.assertIn("WHERE join_code=%s AND is_active=TRUE FOR UPDATE", voice_src)
        self.assertIn("UPDATE direct_voice_rooms SET expires_at = NOW()", rt_src)
        self.assertIn("'shared_note'", rt_src)
        self.assertIn("FOR UPDATE", feed_src)
        self.assertIn("INSERT INTO community_post_amens (post_id, email) VALUES (%s, %s) ON CONFLICT DO NOTHING", feed_src)

        prayer_tree = ast.parse(prayer_src)
        fn_nodes = [
            n for n in prayer_tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "get_shared_prayer"
        ]
        self.assertEqual(len(fn_nodes), 1)
        fn_segment = ast.get_source_segment(prayer_src, fn_nodes[0]) or ""
        self.assertNotIn("ALTER TABLE", fn_segment)
        self.assertNotIn("_ensure_share_column", fn_segment)

    def test_05_attention_focus_concurrency_uuid_timezone_and_health_pending_ast(self):
        focus_src = (ROUTERS_DIR / "attention" / "focus.py").read_text(encoding="utf-8")
        common_src = (ROUTERS_DIR / "attention" / "_common.py").read_text(encoding="utf-8")
        health_src = (ROUTERS_DIR / "main_extracted_health.py").read_text(encoding="utf-8")
        readiness_test_src = (BACKEND_DIR / "tests" / "test_readiness_diagnostics.py").read_text(encoding="utf-8")

        for src in (focus_src, common_src, health_src, readiness_test_src):
            self.assertIsInstance(ast.parse(src), ast.Module)

        self.assertIn("pg_advisory_xact_lock", focus_src)
        self.assertIn("_require_valid_uuid", focus_src)
        self.assertIn("_local_day_bounds", focus_src)
        self.assertIn("_pending_connections", health_src)
        self.assertIn("shutil.rmtree(root, ignore_errors=True)", readiness_test_src)


# ---------------------------------------------------------------------------
# Live PostgreSQL 17 + FastAPI End-to-End Integration Helpers (pytest)
# ---------------------------------------------------------------------------

def _reset_limiter() -> None:
    import main

    storage = getattr(getattr(main, "limiter", None), "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()


def _register_fresh_user(client, prefix: str, *, password: str = "SafePass#2026!") -> dict:
    _reset_limiter()
    tag = secrets.token_hex(5)
    email = f"{prefix}_{tag}@example.com"
    r_code = client.post("/api/auth/email/send-code", json={"email": email})
    assert r_code.status_code == 200, r_code.text
    dev_code = r_code.json()["dev_code"]

    r_reg = client.post(
        "/api/auth/email/register",
        json={
            "email": email,
            "code": dev_code,
            "password": password,
            "nickname": f"{prefix}_{tag[:4]}",
            "session_transport": "bearer",
        },
    )
    assert r_reg.status_code == 200, r_reg.text
    body = r_reg.json()
    token = body.get("token") or r_reg.cookies.get("biblesphere_session")
    assert token
    client.cookies.clear()
    return {
        "id": body["user"]["id"],
        "email": body["user"]["email"],
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def _ensure_shared_church(emails: list[str]) -> int:
    import main

    try:
        from core.deps import invalidate_church_cache
    except ImportError:
        from backend.core.deps import invalidate_church_cache  # type: ignore

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            join_code = ("CH" + secrets.token_hex(4)).upper()[:10]
            cur.execute(
                "INSERT INTO churches (name, slug, owner_email, join_code, is_default, is_active) "
                "VALUES (%s, %s, %s, %s, FALSE, TRUE) RETURNING id",
                (f"Hardening Church {join_code}", f"hc-{join_code.lower()}", emails[0], join_code),
            )
            church_id = int(cur.fetchone()[0])
            for idx, em in enumerate(emails):
                cur.execute("DELETE FROM church_members WHERE email = %s", (em,))
                cur.execute(
                    "INSERT INTO church_members (church_id, email, role) VALUES (%s, %s, %s)",
                    (church_id, em, "owner" if idx == 0 else "member"),
                )
        conn.commit()
    finally:
        main._release_db(conn)

    for em in emails:
        invalidate_church_cache(em)
    return church_id


# ---------------------------------------------------------------------------
# 1. Cross-User Sermon Journals Isolation & Admin Email Redaction
# ---------------------------------------------------------------------------

def test_pg_01_sermon_journals_cross_user_isolation_and_admin_redaction(client, monkeypatch):
    import main
    from routers import main_extracted_sermon as sermon_mod

    user_a = _register_fresh_user(client, "sermon_a")
    user_b = _register_fresh_user(client, "sermon_b")
    admin_u = _register_fresh_user(client, "sermon_adm")

    r_save = client.post(
        "/api/sermon/journals",
        headers=user_a["headers"],
        json={
            "date": "2026-11-15",
            "title": "Confidential Sermon Notes",
            "preacher": "Pastor Lin",
            "scripture": "Romans 8:28",
            "summary": "Grace in trials",
            "reflection": "Personal pastoral reflection for User A only",
        },
    )
    assert r_save.status_code == 200, r_save.text
    journal_id = r_save.json()["journal"]["id"]

    # Owner lists and fetches own sermon journal
    r_list_a = client.get("/api/sermon/journals", headers=user_a["headers"])
    assert r_list_a.status_code == 200
    assert r_list_a.json()["total"] == 1
    assert [it["id"] for it in r_list_a.json()["items"]] == [journal_id]
    assert r_list_a.json()["items"][0]["email"] == user_a["email"]

    # Non-owner User B cannot list or GET /{id} User A's sermon journal
    r_list_b = client.get("/api/sermon/journals", headers=user_b["headers"])
    assert r_list_b.status_code == 200
    assert r_list_b.json()["total"] == 0
    assert r_list_b.json()["items"] == []

    r_get_b = client.get(f"/api/sermon/journals/{journal_id}", headers=user_b["headers"])
    assert r_get_b.status_code == 404

    # Authorized admin viewing User A's journal gets 200 with raw 'email' omitted
    monkeypatch.setattr(sermon_mod, "_is_admin", lambda em: str(em).lower() == admin_u["email"].lower())
    r_get_adm = client.get(f"/api/sermon/journals/{journal_id}", headers=admin_u["headers"])
    assert r_get_adm.status_code == 200
    adm_item = r_get_adm.json()["journal"]
    assert adm_item["id"] == journal_id
    assert "email" not in adm_item

    # Revoking User A's token in PostgreSQL immediately blocks sermon journal reads (401)
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_tokens WHERE token = %s", (user_a["token"],))
        conn.commit()
    finally:
        main._release_db(conn)
    with main._SESSION_LOCK:
        main._SESSION_STORE.pop(user_a["token"], None)

    r_revoked = client.get("/api/sermon/journals", headers=user_a["headers"])
    assert r_revoked.status_code == 401


# ---------------------------------------------------------------------------
# 2. Industrial 6-Source Owner-Isolated Personal Search & Wildcard Escaping
# ---------------------------------------------------------------------------

def test_pg_02_personal_search_six_sources_wildcard_escape_and_pagination(client):
    import main

    user_a = _register_fresh_user(client, "psearch_a")
    user_b = _register_fresh_user(client, "psearch_b")
    church_id = _ensure_shared_church([user_a["email"], user_b["email"]])

    needle = f"ag6_{secrets.token_hex(3)}_100%_ok"
    decoy = needle.replace("100%_ok", "100X9ok")  # Would match ONLY if % or _ were unescaped!

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            # 1) devotion_journals (hit + wildcard decoy + User B record)
            cur.execute(
                "INSERT INTO devotion_journals (email, journal_date, title, scripture_text, reflection) "
                "VALUES (%s, '2026-11-10', %s, 'Psalm 23:1', %s)",
                (user_a["email"], f"Devotion {needle}", f"Deep meditation on {needle}"),
            )
            cur.execute(
                "INSERT INTO devotion_journals (email, journal_date, title, scripture_text, reflection) "
                "VALUES (%s, '2026-11-11', %s, 'Psalm 24:1', %s)",
                (user_a["email"], f"Decoy {decoy}", f"Unescaped decoy {decoy}"),
            )
            cur.execute(
                "INSERT INTO devotion_journals (email, journal_date, title, scripture_text, reflection) "
                "VALUES (%s, '2026-11-10', %s, 'Psalm 23:1', %s)",
                (user_b["email"], f"UserB Devotion {needle}", f"Other user {needle}"),
            )

            # 2) personal_notes (source_sermon_id IS NULL)
            cur.execute(
                "INSERT INTO personal_notes (id, email, note_date, scripture, reflection, shared) "
                "VALUES (%s, %s, '2026-11-12', 'John 15:5', %s, FALSE)",
                (f"pn_{secrets.token_hex(6)}", user_a["email"], f"Abiding note {needle}"),
            )

            # 3) sermon_journals
            cur.execute(
                "INSERT INTO sermon_journals (email, sermon_date, title, preacher, scripture, summary) "
                "VALUES (%s, '2026-11-13', %s, 'Pastor Chen', 'Ephesians 2:8', %s)",
                (user_a["email"], f"Sermon {needle}", f"Summary {needle}"),
            )
            cur.execute(
                "INSERT INTO sermon_journals (email, sermon_date, title, preacher, scripture, summary) "
                "VALUES (%s, '2026-11-13', %s, 'Pastor Chen', 'Ephesians 2:8', %s)",
                (user_b["email"], f"UserB Sermon {needle}", f"Summary {needle}"),
            )

            # 4) prayers
            cur.execute(
                "INSERT INTO prayers (email, nickname, content, is_anonymous, amen_count, church_id, is_public) "
                "VALUES (%s, 'Alice', %s, FALSE, 0, %s, FALSE)",
                (user_a["email"], f"Lord hear our prayer {needle}", church_id),
            )

            # 5) call_minutes_history
            cur.execute(
                "INSERT INTO call_minutes_history (email, title, summary, prayer_items) "
                "VALUES (%s, %s, %s, %s::jsonb)",
                (user_a["email"], f"Fellowship Minutes {needle}", "Weekly fellowship", json.dumps([needle])),
            )

            # 6) memory_decks (LATERAL jsonb_array_elements)
            cards = [
                {"id": "card-hit", "ref": "Romans 12:2", "textCuv": f"心意更新而变化 {needle}", "textEsv": "Be transformed"},
                {"id": "card-decoy", "ref": "Romans 12:1", "textCuv": f"Decoy {decoy}", "textEsv": "Living sacrifice"},
            ]
            cur.execute(
                "INSERT INTO memory_decks (email, cards, updated_at) VALUES (%s, %s::jsonb, NOW()) "
                "ON CONFLICT (email) DO UPDATE SET cards = EXCLUDED.cards, updated_at = NOW()",
                (user_a["email"], json.dumps(cards)),
            )
        conn.commit()
    finally:
        main._release_db(conn)

    for route in ("/api/personal/search", "/api/personal-search"):
        resp = client.get(route, params={"q": needle}, headers=user_a["headers"])
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["success"] is True
        assert data["query"] == needle
        assert data["counts"] == {
            "devotion": 1,
            "personal_note": 1,
            "sermon": 1,
            "prayer": 1,
            "minutes": 1,
            "memory": 1,
        }
        assert data["total"] == 6
        assert len(data["results"]) == 6
        for hit in data["results"]:
            assert set(hit.keys()) >= {"id", "source", "title", "date", "snippet", "scripture"}
            assert decoy not in hit["snippet"]

    # Source filter + pagination counts check
    r_filtered = client.get(
        "/api/personal/search",
        params={"q": needle, "sources": "devotion,memory", "limit": 1, "offset": 0},
        headers=user_a["headers"],
    )
    assert r_filtered.status_code == 200
    f_body = r_filtered.json()
    assert f_body["counts"] == {"devotion": 1, "memory": 1}
    assert f_body["total"] == 2
    assert {g["type"] for g in f_body["groups"]} == {"devotion", "memory"}

    # Cross-user isolation: User B only sees User B's 2 records
    r_user_b = client.get("/api/personal/search", params={"q": needle}, headers=user_b["headers"])
    assert r_user_b.status_code == 200
    b_body = r_user_b.json()
    assert b_body["total"] == 2
    assert b_body["counts"]["devotion"] == 1
    assert b_body["counts"]["sermon"] == 1
    assert b_body["counts"]["personal_note"] == 0
    assert b_body["counts"]["memory"] == 0


# ---------------------------------------------------------------------------
# 3. Password Reset Session Revocation, Deletion Gating & Ordo Tx Custody
# ---------------------------------------------------------------------------

def test_pg_03_password_reset_revokes_tokens_deletion_gates_session_and_ordo_custody(client, monkeypatch):
    import main
    from routers import ordo_amoris_augustine as ordo_mod

    user = _register_fresh_user(client, "custody_u")
    bearer_tok = user["token"]

    # Issue a second Cookie session and a mixed-case token row in PostgreSQL
    _reset_limiter()
    r_login_cookie = client.post(
        "/api/auth/email/login",
        json={"email": user["email"], "password": user["password"]},
    )
    assert r_login_cookie.status_code == 200
    cookie_tok = r_login_cookie.cookies.get("biblesphere_session")
    assert cookie_tok and cookie_tok != bearer_tok
    client.cookies.clear()

    mixed_tok = f"mixed_{secrets.token_urlsafe(24)}"
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_tokens (token, email, data, expires_at) "
                "VALUES (%s, %s, %s::jsonb, NOW() + INTERVAL '1 hour')",
                (mixed_tok, user["email"].upper(), json.dumps({"id": user["id"], "email": user["email"]})),
            )
        conn.commit()
    finally:
        main._release_db(conn)

    # Verify both Bearer and Cookie tokens work before password reset
    assert client.get("/api/ordo/history", headers={"Authorization": f"Bearer {bearer_tok}"}).status_code == 200
    assert client.get("/api/ordo/history", headers={"Cookie": f"biblesphere_session={cookie_tok}"}).status_code == 200

    # Reset password -> atomically revokes ALL user_tokens case-insensitively + evicts _SESSION_STORE
    _reset_limiter()
    r_code = client.post("/api/auth/email/send-reset-code", json={"email": user["email"]})
    assert r_code.status_code == 200, r_code.text
    reset_code = r_code.json()["dev_code"]

    new_password = "NewResetPass#2026!"
    r_reset = client.post(
        "/api/auth/email/reset-password",
        json={"email": user["email"], "code": reset_code, "password": new_password},
    )
    assert r_reset.status_code == 200, r_reset.text
    client.cookies.clear()

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_tokens WHERE LOWER(email) = LOWER(%s)", (user["email"],))
            remaining_tokens = cur.fetchone()[0]
    finally:
        main._release_db(conn)
    assert remaining_tokens == 0

    for old_headers in (
        {"Authorization": f"Bearer {bearer_tok}"},
        {"Cookie": f"biblesphere_session={cookie_tok}"},
        {"Authorization": f"Bearer {mixed_tok}"},
    ):
        assert client.get("/api/ordo/history", headers=old_headers).status_code == 401

    # Login with new password and test mid-flight token revocation in POST /api/ordo/analyze
    _reset_limiter()
    r_relogin = client.post(
        "/api/auth/email/login",
        json={"email": user["email"], "password": new_password, "session_transport": "bearer"},
    )
    assert r_relogin.status_code == 200
    fresh_tok = r_relogin.json()["token"]
    client.cookies.clear()

    orig_analyze = ordo_mod.engine.analyze

    def _analyze_with_midflight_revocation(*args, **kwargs):
        res = orig_analyze(*args, **kwargs)
        c2 = main._get_db()
        try:
            with c2.cursor() as cur2:
                cur2.execute("DELETE FROM user_tokens WHERE token = %s", (fresh_tok,))
            c2.commit()
        finally:
            main._release_db(c2)
        return res

    monkeypatch.setattr(ordo_mod.engine, "analyze", _analyze_with_midflight_revocation)
    r_ordo = client.post(
        "/api/ordo/analyze",
        headers={"Authorization": f"Bearer {fresh_tok}"},
        json={"loves": ["work", "god"], "text": "Testing transactional custody", "use_ai": False},
    )
    assert r_ordo.status_code == 401
    assert "revoked" in r_ordo.json()["detail"].lower() or "expired" in r_ordo.json()["detail"].lower()

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ordo_amoris_entries WHERE LOWER(email) = LOWER(%s)", (user["email"],))
            orphan_entries = cur.fetchone()[0]
    finally:
        main._release_db(conn)
    assert orphan_entries == 0

    # Test account_deletion_requests gating: pending_review allowed, processing/completed rejected
    _reset_limiter()
    r_login2 = client.post(
        "/api/auth/email/login",
        json={"email": user["email"], "password": new_password, "session_transport": "bearer"},
    )
    assert r_login2.status_code == 200
    tok2 = r_login2.json()["token"]
    client.cookies.clear()

    del_req_id = str(uuid.uuid4())
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO account_deletion_requests (id, user_id, status) "
                "VALUES (%s, %s, 'pending_review')",
                (del_req_id, user["id"]),
            )
        conn.commit()
    finally:
        main._release_db(conn)

    with main._SESSION_LOCK:
        main._SESSION_STORE.clear()
    assert client.get("/api/ordo/history", headers={"Authorization": f"Bearer {tok2}"}).status_code == 200

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE account_deletion_requests SET status = 'processing' WHERE id = %s", (del_req_id,))
        conn.commit()
    finally:
        main._release_db(conn)

    with main._SESSION_LOCK:
        main._SESSION_STORE.clear()
    assert client.get("/api/ordo/history", headers={"Authorization": f"Bearer {tok2}"}).status_code == 401

    _reset_limiter()
    r_blocked_login = client.post(
        "/api/auth/email/login",
        json={"email": user["email"], "password": new_password, "session_transport": "bearer"},
    )
    assert r_blocked_login.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 4. erase_user_data() Social/PII Sweep, Mixed-Case Tokens & Zero Coverage Gaps
# ---------------------------------------------------------------------------

def test_pg_04_erase_user_data_social_pii_mixed_case_tokens_and_zero_coverage_gaps(client):
    import main

    victim = _register_fresh_user(client, "erase_victim")
    peer = _register_fresh_user(client, "erase_peer")
    bystander = _register_fresh_user(client, "erase_bystander")

    v_email = victim["email"]
    p_email = peer["email"]
    b_email = bystander["email"]
    lo, hi = sorted([v_email, p_email])

    open_report_id = str(uuid.uuid4())
    closed_report_id = str(uuid.uuid4())
    reporter_report_id = str(uuid.uuid4())
    reviewed_by_victim_id = str(uuid.uuid4())

    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            # 1) Full migrated schema must have 0 erasure coverage gaps
            cur.execute("SELECT table_name, reason FROM erasure_coverage_gaps()")
            gaps = cur.fetchall()
            assert gaps == [], f"Unexpected erasure coverage gaps: {gaps}"

            # 2) Seed mixed-case tokens, friendships, chat_messages, direct_voice_rooms, user_blocks, social_reports
            cur.execute(
                "INSERT INTO user_tokens (token, email, data, expires_at) "
                "VALUES (%s, %s, '{}'::jsonb, NOW() + INTERVAL '1 hour')",
                (f"uc_{secrets.token_urlsafe(18)}", v_email.upper()),
            )
            cur.execute(
                "INSERT INTO friendships (requester, addressee, status, user_low, user_high) "
                "VALUES (%s, %s, 'accepted', %s, %s) ON CONFLICT (user_low, user_high) DO NOTHING",
                (v_email, p_email, lo, hi),
            )
            cur.execute(
                "INSERT INTO chat_messages (sender, recipient, body) VALUES (%s, %s, 'Erase me DM')",
                (v_email, p_email),
            )
            cur.execute(
                "INSERT INTO direct_voice_rooms (id, user_low, user_high, expires_at) "
                "VALUES (%s, %s, %s, NOW() + INTERVAL '30 minutes')",
                (f"vd_{secrets.token_hex(8)}", lo, hi),
            )
            cur.execute(
                "INSERT INTO user_blocks (blocker_email, blocked_email, source_key) "
                "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (v_email, b_email, f"known:{b_email}"),
            )
            cur.execute(
                "INSERT INTO social_reports (id, reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, %s, 'user', %s, 'spam', 'review_pending')",
                (reporter_report_id, v_email, p_email, p_email),
            )
            cur.execute(
                "INSERT INTO social_reports (id, reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, %s, 'user', %s, 'spam', 'closed')",
                (closed_report_id, p_email, v_email, v_email),
            )
            cur.execute(
                "INSERT INTO social_reports (id, reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, %s, 'user', %s, 'harassment', 'review_pending')",
                (open_report_id, p_email, v_email, v_email),
            )
            cur.execute(
                "INSERT INTO social_reports (id, reporter_email, target_email, resource_type, resource_key, category, status, reviewer_email) "
                "VALUES (%s, %s, %s, 'user', %s, 'other', 'under_review', %s)",
                (reviewed_by_victim_id, p_email, b_email, b_email, v_email.upper()),
            )
            cur.execute(
                "INSERT INTO ordo_amoris_entries (id, email, input_text, crisis, analysis_json) "
                "VALUES (%s, %s, 'erasure check', FALSE, '{}'::jsonb)",
                (uuid.uuid4().hex, v_email),
            )

            # 3) Run erase_user_data with mixed-case email input + delete user row
            cur.execute("SELECT table_name, rows_deleted FROM erase_user_data(%s)", (v_email.upper(),))
            erased_summary = dict(cur.fetchall())
            assert erased_summary.get("user_tokens", 0) >= 2
            cur.execute("DELETE FROM users WHERE LOWER(email) = LOWER(%s)", (v_email,))
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_tokens WHERE LOWER(email) = LOWER(%s)", (v_email,))
            assert cur.fetchone()[0] == 0

            cur.execute(
                "SELECT COUNT(*) FROM friendships WHERE LOWER(user_low)=LOWER(%s) OR LOWER(user_high)=LOWER(%s)",
                (v_email, v_email),
            )
            assert cur.fetchone()[0] == 0

            cur.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE LOWER(sender)=LOWER(%s) OR LOWER(recipient)=LOWER(%s)",
                (v_email, v_email),
            )
            assert cur.fetchone()[0] == 0

            cur.execute(
                "SELECT COUNT(*) FROM direct_voice_rooms WHERE LOWER(user_low)=LOWER(%s) OR LOWER(user_high)=LOWER(%s)",
                (v_email, v_email),
            )
            assert cur.fetchone()[0] == 0

            cur.execute(
                "SELECT COUNT(*) FROM user_blocks WHERE LOWER(blocker_email)=LOWER(%s) OR LOWER(blocked_email)=LOWER(%s)",
                (v_email, v_email),
            )
            assert cur.fetchone()[0] == 0

            cur.execute("SELECT COUNT(*) FROM ordo_amoris_entries WHERE LOWER(email)=LOWER(%s)", (v_email,))
            assert cur.fetchone()[0] == 0

            cur.execute("SELECT id FROM social_reports WHERE id IN (%s, %s)", (reporter_report_id, closed_report_id))
            assert cur.fetchall() == []

            cur.execute("SELECT target_email, status FROM social_reports WHERE id = %s", (open_report_id,))
            assert cur.fetchone() == ("[erased]", "review_pending")

            cur.execute("SELECT reviewer_email FROM social_reports WHERE id = %s", (reviewed_by_victim_id,))
            assert cur.fetchone() == (None,)
    finally:
        main._release_db(conn)


# ---------------------------------------------------------------------------
# 5. Mutual Blocks Across Shared Notes, Evangelism, Voice, Realtime & Feed
# ---------------------------------------------------------------------------

def test_pg_05_mutual_blocks_across_shared_notes_evangelism_voice_realtime_and_feed(client, monkeypatch):
    import main

    monkeypatch.setenv("LIVEKIT_URL", "wss://livekit.holiness.test")
    monkeypatch.setenv("LIVEKIT_API_KEY", "lk_industrial_test_key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "lk_industrial_test_secret_32_bytes_minimum!!")

    alice = _register_fresh_user(client, "blk_alice")
    bob = _register_fresh_user(client, "blk_bob")
    carol = _register_fresh_user(client, "blk_carol")
    _ensure_shared_church([alice["email"], bob["email"], carol["email"]])

    # Establish friendship between Alice and Bob
    assert client.post("/api/friends/request", headers=alice["headers"], json={"email": bob["email"]}).status_code == 200
    assert client.post("/api/friends/accept", headers=bob["headers"], json={"email": alice["email"]}).status_code == 200
    assert any(f["email"] == alice["email"] for f in client.get("/api/friends", headers=bob["headers"]).json()["friends"])

    # Alice creates a shared note, an evangelism prayer, a public community post, a shared prayer, and a voice group
    r_note = client.post(
        "/api/personal/notes",
        headers=alice["headers"],
        json={
            "date": "2026-11-18",
            "scripture": "Philippians 4:6",
            "reflection": f"Shared gratitude {secrets.token_hex(4)}",
            "shared": True,
            "author": "Alice",
        },
    )
    assert r_note.status_code == 200, r_note.text
    note_id = r_note.json()["note"]["id"]

    r_evan = client.post(
        "/api/evangelism",
        headers=alice["headers"],
        json={"content": f"Pray for my neighbor {secrets.token_hex(4)}", "is_anonymous": False, "kind": "prayer"},
    )
    assert r_evan.status_code == 200, r_evan.text
    evan_id = r_evan.json()["id"]

    r_feed = client.post(
        "/api/community/feed",
        headers=alice["headers"],
        json={"content": f"Morning peace {secrets.token_hex(4)}", "status_key": "peace", "is_public": True},
    )
    assert r_feed.status_code == 200, r_feed.text
    post_id = r_feed.json()["id"]

    r_prayer = client.post(
        "/api/prayers",
        headers=alice["headers"],
        json={"content": f"Shared intercession {secrets.token_hex(4)}", "is_anonymous": False, "is_public": True},
    )
    assert r_prayer.status_code == 200, r_prayer.text
    prayer_id = r_prayer.json()["id"]
    r_pshare = client.post(f"/api/prayers/{prayer_id}/share", headers=alice["headers"])
    assert r_pshare.status_code == 200
    share_token = r_pshare.json()["share_token"]
    assert client.get(f"/api/prayer-share/{share_token}").status_code == 200

    r_vg = client.post("/api/voice/groups", headers=alice["headers"], json={"name": "Prayer Room", "max_members": 5})
    assert r_vg.status_code == 200, r_vg.text
    vg = r_vg.json()["group"]
    gid, join_code = vg["id"], vg["join_code"]

    assert client.post("/api/voice/groups/join", headers=bob["headers"], json={"join_code": join_code}).status_code == 200
    assert client.post(f"/api/voice/groups/{gid}/token", headers=bob["headers"]).status_code == 200

    # Issue a direct voice room between Alice and Bob
    r_dv = client.post("/api/voice/direct/token", headers=alice["headers"], json={"peer": bob["email"]})
    assert r_dv.status_code == 200, r_dv.text
    direct_room_id = r_dv.json()["room"]

    # Before block: Carol can report shared_note; guests & non-owners never see raw emails on evangelism/community
    r_rep_note = client.post(
        "/api/safety/reports",
        headers=carol["headers"],
        json={"resource_type": "shared_note", "resource_id": note_id, "category": "spam"},
    )
    assert r_rep_note.status_code == 200

    r_evan_guest = client.get("/api/evangelism")
    assert r_evan_guest.status_code == 200
    guest_evan_item = next(it for it in r_evan_guest.json()["items"] if it["id"] == evan_id)
    assert guest_evan_item["email"] == ""

    r_evan_bob_before = client.get("/api/evangelism", headers=bob["headers"])
    bob_evan_item = next(it for it in r_evan_bob_before.json()["items"] if it["id"] == evan_id)
    assert bob_evan_item["email"] == ""

    r_feed_guest = client.get("/api/community/feed")
    assert r_feed_guest.status_code == 200
    guest_post = next(it for it in r_feed_guest.json()["items"] if it["id"] == post_id)
    assert guest_post.get("author_email") in (None, "")

    # Concurrent toggle_amen by Carol never 500s
    def _amen_once(_i: int) -> int:
        from fastapi.testclient import TestClient

        with TestClient(main.app) as local_c:
            resp = local_c.post(f"/api/community/feed/{post_id}/amen", headers=carol["headers"])
            return resp.status_code

    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(_amen_once, range(4)))
    assert all(code == 200 for code in statuses)

    # Alice blocks Bob!
    r_block = client.post("/api/safety/blocks", headers=alice["headers"], json={"email": bob["email"]})
    assert r_block.status_code == 200

    # 1) Direct voice room expired immediately on block
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT expires_at <= NOW() FROM direct_voice_rooms WHERE id = %s", (direct_room_id,))
            assert cur.fetchone()[0] is True
    finally:
        main._release_db(conn)

    # 2) Realtime friends list excludes blocked user in BOTH directions
    assert all(f["email"] != bob["email"] for f in client.get("/api/friends", headers=alice["headers"]).json()["friends"])
    assert all(f["email"] != alice["email"] for f in client.get("/api/friends", headers=bob["headers"]).json()["friends"])

    # 3) Shared notes feed & amen enforce mutual block (404)
    r_notes_bob = client.get("/api/shared/notes", headers=bob["headers"])
    assert r_notes_bob.status_code == 200
    assert all(n["id"] != note_id for n in r_notes_bob.json().get("notes", r_notes_bob.json().get("items", [])))
    assert client.post(f"/api/shared/notes/{note_id}/amen", headers=bob["headers"]).status_code == 404

    # 4) Evangelism feed & amen enforce mutual block (404)
    r_evan_bob_after = client.get("/api/evangelism", headers=bob["headers"])
    assert r_evan_bob_after.status_code == 200
    assert all(it["id"] != evan_id for it in r_evan_bob_after.json()["items"])
    assert client.post(f"/api/evangelism/{evan_id}/amen", headers=bob["headers"]).status_code == 404

    # 5) Shared prayer link enforces mutual block for authenticated blocked viewer (404)
    assert client.get(f"/api/prayer-share/{share_token}", headers=bob["headers"]).status_code == 404

    # 6) Voice groups: blocked member hidden in group_members, rejected in issue_token (403) & new join_group (404)
    r_members_bob = client.get(f"/api/voice/groups/{gid}/members", headers=bob["headers"])
    assert r_members_bob.status_code == 200
    assert len(r_members_bob.json()["members"]) == 1
    assert r_members_bob.json()["members"][0]["is_me"] is True

    assert client.post(f"/api/voice/groups/{gid}/token", headers=bob["headers"]).status_code == 403

    r_vg2 = client.post("/api/voice/groups", headers=alice["headers"], json={"name": "Second Room", "max_members": 3})
    assert r_vg2.status_code == 200
    assert client.post(
        "/api/voice/groups/join",
        headers=bob["headers"],
        json={"join_code": r_vg2.json()["group"]["join_code"]},
    ).status_code == 404


# ---------------------------------------------------------------------------
# 6. Attention Focus Sessions Concurrency, UUID, Idempotency, 0-Min & Timezone
# ---------------------------------------------------------------------------

def test_pg_06_attention_focus_concurrency_uuid_idempotency_zero_minutes_timezone_and_health_db(client):
    import main

    user_f = _register_fresh_user(client, "focus_u")
    headers = user_f["headers"]

    # 1) Invalid UUID returns 404 NOT_FOUND instead of 500 InvalidTextRepresentation
    r_bad_end = client.post("/api/attention/focus-sessions/not-a-valid-uuid/end", headers=headers, json={})
    assert r_bad_end.status_code == 404
    r_bad_int = client.post(
        "/api/attention/focus-sessions/not-a-valid-uuid/interrupt",
        headers=headers,
        json={"interruptionReason": "Invalid UUID probe"},
    )
    assert r_bad_int.status_code == 404

    # 2) Concurrent create_focus_session -> 1x 200 + 3x 409 ACTIVE_FOCUS_SESSION_EXISTS with active DTO
    def _start_concurrent(idx: int) -> tuple[int, dict]:
        from fastapi.testclient import TestClient

        with TestClient(main.app) as local_c:
            resp = local_c.post(
                "/api/attention/focus-sessions",
                headers=headers,
                json={"plannedMinutes": 25, "focusType": "worship", "intention": f"Focus {idx}"},
            )
            return resp.status_code, resp.json()

    with ThreadPoolExecutor(max_workers=4) as pool:
        outcomes = list(pool.map(_start_concurrent, range(4)))

    created = [b for code, b in outcomes if code == 200]
    conflicts = [b for code, b in outcomes if code == 409]
    assert len(created) == 1, outcomes
    assert len(conflicts) == 3, outcomes
    sid = created[0]["session"]["id"]
    for c_body in conflicts:
        detail = c_body["detail"]
        assert detail["error"] == "ACTIVE_FOCUS_SESSION_EXISTS"
        assert detail["active"]["id"] == sid

    # 3) actualMinutes = 0 is preserved, end is idempotent, and interrupt on ended returns 409
    r_end0 = client.post(
        f"/api/attention/focus-sessions/{sid}/end",
        headers=headers,
        json={"actualMinutes": 0, "closingReflection": "Ended within 20 seconds"},
    )
    assert r_end0.status_code == 200, r_end0.text
    ended_dto = r_end0.json()["session"]
    assert ended_dto["actualMinutes"] == 0
    assert ended_dto["endedAt"] is not None

    r_end_again = client.post(
        f"/api/attention/focus-sessions/{sid}/end",
        headers=headers,
        json={"actualMinutes": 45, "closingReflection": "Should not overwrite"},
    )
    assert r_end_again.status_code == 200
    assert r_end_again.json()["session"]["actualMinutes"] == 0
    assert r_end_again.json()["session"]["endedAt"] == ended_dto["endedAt"]

    r_int_after_end = client.post(
        f"/api/attention/focus-sessions/{sid}/interrupt",
        headers=headers,
        json={"interruptionReason": "Late interrupt"},
    )
    assert r_int_after_end.status_code == 409
    assert r_int_after_end.json()["detail"]["error"] == "SESSION_ALREADY_ENDED"

    # 4) Interrupt idempotency on active session
    r_s2 = client.post(
        "/api/attention/focus-sessions",
        headers=headers,
        json={"plannedMinutes": 15, "focusType": "mission", "intention": "Morning prayer"},
    )
    assert r_s2.status_code == 200
    sid2 = r_s2.json()["session"]["id"]

    r_int1 = client.post(
        f"/api/attention/focus-sessions/{sid2}/interrupt",
        headers=headers,
        json={"interruptionReason": "Phone call"},
    )
    assert r_int1.status_code == 200
    assert r_int1.json()["session"]["interrupted"] is True

    r_int2 = client.post(
        f"/api/attention/focus-sessions/{sid2}/interrupt",
        headers=headers,
        json={"interruptionReason": "Duplicate retry"},
    )
    assert r_int2.status_code == 200
    assert r_int2.json()["session"]["interrupted"] is True
    assert r_int2.json()["session"]["interruptionReason"] == "Phone call"

    # 5) X-Timezone boundary filtering via UTC half-open range:
    # 2026-06-01T22:30:00Z == 2026-06-02 06:30 Asia/Shanghai == 2026-06-01 18:30 America/New_York
    tz_sid = str(uuid.uuid4())
    conn = main._get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO attention_focus_sessions "
                "(id, user_id, started_at, ended_at, planned_minutes, actual_minutes, focus_type, intention) "
                "VALUES (%s, %s, %s, %s, 25, 25, 'restoration', 'Timezone boundary session')",
                (
                    tz_sid,
                    user_f["email"],
                    datetime(2026, 6, 1, 22, 30, tzinfo=timezone.utc),
                    datetime(2026, 6, 1, 22, 55, tzinfo=timezone.utc),
                ),
            )
        conn.commit()
    finally:
        main._release_db(conn)

    r_shanghai = client.get(
        "/api/attention/focus-sessions",
        params={"from": "2026-06-02", "to": "2026-06-02"},
        headers={**headers, "X-Timezone": "Asia/Shanghai"},
    )
    assert r_shanghai.status_code == 200
    assert any(s["id"] == tz_sid for s in r_shanghai.json()["sessions"])

    r_ny_june2 = client.get(
        "/api/attention/focus-sessions",
        params={"from": "2026-06-02", "to": "2026-06-02"},
        headers={**headers, "X-Timezone": "America/New_York"},
    )
    assert r_ny_june2.status_code == 200
    assert all(s["id"] != tz_sid for s in r_ny_june2.json()["sessions"])

    r_ny_june1 = client.get(
        "/api/attention/focus-sessions",
        params={"from": "2026-06-01", "to": "2026-06-01"},
        headers={**headers, "X-Timezone": "America/New_York"},
    )
    assert r_ny_june1.status_code == 200
    assert any(s["id"] == tz_sid for s in r_ny_june1.json()["sessions"])

    # 6) /api/health/db exposes pool.pending count
    r_health = client.get("/api/health/db")
    assert r_health.status_code == 200
    pool_stats = r_health.json()["pool"]
    assert "pending" in pool_stats
    assert isinstance(pool_stats["pending"], int) and pool_stats["pending"] >= 0


if __name__ == "__main__":
    unittest.main()
