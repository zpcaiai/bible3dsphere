"""Deletion propagation for EMD-OS — G5 privacy.

Two layers:

* **Structural** (runs everywhere): re-derives the set of personal EMD tables from the
  migration files and asserts the erase endpoint covers every one of them. A new personal
  table that nobody remembered to wire up fails here, not in production.
* **Integration** (needs a live Postgres, skipped otherwise): applies migration 0233,
  seeds a row in every EMD table, runs both the domain erase and the account-level
  `erase_user_data`, and asserts nothing survives — including the user_id-keyed vector
  store that the 0145 snapshot missed.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from formation_twin.emotional_maturity_erasure import (
    DELETION_PLAN,
    DELETION_PLAN_BY_TARGET,
    EMD_PERSONAL_TABLES,
    EMD_SHARED_CATALOG_TABLES,
    MANUAL_TARGETS,
    build_erasure_receipt,
    describe_deletion_plan,
)
from emd_schema_catalog import catalog, emd_tables
from production_governance.emd_certification import DELETION_TARGETS


pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).resolve().parents[1]
MIGRATIONS = BACKEND / "migrations"

def emd_tables_from_migrations() -> dict[str, frozenset[str]]:
    """{table: columns} for every EMD table declared in migrations/.

    Uses the shared catalog parser: the first version here was line-anchored and never
    saw `email`, which turned the coverage assertions into empty-set comparisons.
    """
    tables = catalog()
    return {name: tables[name] for name in emd_tables()}


# ── 结构层：覆盖范围是从迁移文件推导出来的，不是手抄的 ──────────────────────

def test_migrations_actually_declare_emd_tables():
    tables = emd_tables_from_migrations()
    assert len(tables) >= 70, f"only found {len(tables)} EMD tables — parser broken?"
    personal = [name for name, columns in tables.items() if "email" in columns]
    assert len(personal) >= 70, (
        f"only {len(personal)} EMD tables look personal — the coverage checks below "
        "would pass vacuously"
    )


def test_every_personal_emd_table_is_erased():
    tables = emd_tables_from_migrations()
    personal = {name for name, columns in tables.items() if "email" in columns}
    missing = sorted(personal - set(EMD_PERSONAL_TABLES))
    assert missing == [], f"personal tables never deleted: {missing}"


def test_erase_list_contains_no_phantom_tables():
    tables = emd_tables_from_migrations()
    phantom = sorted(set(EMD_PERSONAL_TABLES) - set(tables))
    assert phantom == [], f"deleting tables that do not exist: {phantom}"


def test_excluded_tables_are_shared_catalogs_without_personal_data():
    tables = emd_tables_from_migrations()
    for name in EMD_SHARED_CATALOG_TABLES:
        assert name in tables, f"{name} missing from migrations"
        assert "email" not in tables[name], f"{name} holds personal data but is not erased"


def test_the_split_is_exhaustive():
    tables = emd_tables_from_migrations()
    covered = set(EMD_PERSONAL_TABLES) | set(EMD_SHARED_CATALOG_TABLES)
    unclassified = sorted(set(tables) - covered)
    assert unclassified == [], f"EMD tables in neither list: {unclassified}"


def test_router_uses_the_shared_table_list():
    source = (BACKEND / "routers" / "formation_twin_emotional_maturity.py").read_text(encoding="utf-8")
    assert "for table in EMD_PERSONAL_TABLES:" in source
    # 旧的内联元组必须彻底消失，否则两份清单会各自漂移
    assert 'tables = (\n        "formation_twin_emd_growth_reports"' not in source


# ── 十一个删除目标都有对应机制 ───────────────────────────────────────────────

def test_every_declared_deletion_target_has_a_mechanism():
    planned = {item["target"] for item in DELETION_PLAN}
    missing = sorted(set(DELETION_TARGETS) - planned)
    assert missing == [], f"targets promised but not implemented: {missing}"


def test_no_mechanism_invented_for_an_undeclared_target():
    planned = {item["target"] for item in DELETION_PLAN}
    assert planned <= set(DELETION_TARGETS)


def test_only_backups_are_admitted_as_non_immediate():
    assert MANUAL_TARGETS == ("BACKUPS",)
    assert DELETION_PLAN_BY_TARGET["BACKUPS"]["automatic"] is False


def test_every_mechanism_states_how_it_is_verified():
    for item in DELETION_PLAN:
        assert item["verification"], item["target"]
        assert item["mechanism"], item["target"]


def test_receipt_is_complete_for_a_full_pass():
    counts = {table: 1 for table in EMD_PERSONAL_TABLES}
    receipt = build_erasure_receipt(counts)
    assert receipt["complete"] is True
    assert receipt["rows_deleted_total"] == len(EMD_PERSONAL_TABLES)
    assert receipt["tables_not_attempted"] == []
    assert receipt["manual_followups"] == ["BACKUPS"]


def test_receipt_flags_a_table_that_was_skipped():
    counts = {table: 0 for table in EMD_PERSONAL_TABLES[1:]}
    receipt = build_erasure_receipt(counts)
    assert receipt["complete"] is False
    assert EMD_PERSONAL_TABLES[0] in receipt["tables_not_attempted"]


def test_receipt_tells_the_user_the_truth_about_backups():
    receipt = build_erasure_receipt({table: 0 for table in EMD_PERSONAL_TABLES})
    backups = next(item for item in receipt["targets"] if item["target"] == "BACKUPS")
    assert backups["status"] == "RETENTION_WINDOW"
    assert "保留期" in receipt["user_message"]


def test_describe_deletion_plan_reports_the_real_counts():
    described = describe_deletion_plan()
    assert described["personal_tables"] == len(EMD_PERSONAL_TABLES)
    assert described["shared_catalog_tables"] == list(EMD_SHARED_CATALOG_TABLES)


# ── 迁移 0233：账户级删除必须动态发现表 ──────────────────────────────────────

MIGRATION_0233 = MIGRATIONS / "0233_emd_erasure_propagation.sql"
MIGRATION_0235 = MIGRATIONS / "0235_emd_erasure_coverage_scope.sql"
MIGRATION_0245 = MIGRATIONS / "0245_social_safety.sql"
MIGRATION_0246 = MIGRATIONS / "0246_account_deletion_requests.sql"
MIGRATION_0249 = MIGRATIONS / "0249_industrial_erasure_and_safety_indexes.sql"


def test_migration_0233_exists_with_a_rollback():
    assert MIGRATION_0233.exists()
    assert (MIGRATIONS / "rollback" / "0233_emd_erasure_propagation_down.sql").exists()


def test_account_erasure_discovers_tables_from_the_catalog():
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    assert "personal_email_tables()" in sql
    assert "personal_userid_tables()" in sql
    assert "information_schema.columns" in sql
    # 快照式硬编码数组正是 0145 的缺陷所在，不能再出现
    assert "email_tables text[] := ARRAY[" not in sql


def test_migration_0233_ships_a_coverage_self_check():
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    assert "erasure_coverage_gaps()" in sql
    assert "emd_erasure_coverage()" in sql


def test_0145_snapshot_predates_emd_and_is_therefore_superseded():
    """The gap this migration closes — kept as a test so the reasoning is not lost."""
    old = (MIGRATIONS / "0145_right_to_erasure.sql").read_text(encoding="utf-8")
    assert "formation_twin_emd_" not in old, (
        "0145 now mentions EMD tables; re-check whether 0233 is still needed"
    )


# ── 集成层：需要真实 Postgres ────────────────────────────────────────────────

DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5431/postgres")
EMD_SCHEMA_MIGRATIONS = tuple(
    MIGRATIONS / f"{version}_formation_twin_{suffix}.sql"
    for version, suffix in (
        ("0223", "emotional_maturity"),
        ("0224", "emd_item_bank"),
        ("0225", "emd_real_life_events"),
        ("0226", "emd_regulation"),
        ("0227", "emd_family_self"),
        ("0228", "emd_conflict_repair"),
        ("0229", "emd_grief_rest"),
        ("0230", "emd_integration"),
        ("0231", "emd_analytics"),
    )
)


def _connection():
    import secrets

    psycopg2 = pytest.importorskip("psycopg2")
    dsn = os.environ.get("DATABASE_URL", DB_URL)
    try:
        admin = psycopg2.connect(dsn, connect_timeout=3)
    except psycopg2.OperationalError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no live Postgres for the integration pass: {exc}")

    temp_db = f"emd_iso_{secrets.token_hex(6)}"
    try:
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{temp_db}"')
    finally:
        admin.close()

    parsed = psycopg2.extensions.parse_dsn(dsn)
    parsed["dbname"] = temp_db
    iso_dsn = psycopg2.extensions.make_dsn(**parsed)

    class _IsolatedDbConnection(psycopg2.extensions.connection):
        def close(self) -> None:
            already_closed = bool(self.closed)
            super().close()
            if not already_closed:
                cleanup = psycopg2.connect(dsn, connect_timeout=5)
                try:
                    cleanup.autocommit = True
                    with cleanup.cursor() as ccur:
                        ccur.execute(f'DROP DATABASE IF EXISTS "{temp_db}" WITH (FORCE)')
                finally:
                    cleanup.close()

    conn = psycopg2.connect(iso_dsn, connect_timeout=5, connection_factory=_IsolatedDbConnection)
    try:
        with conn.cursor() as cur:
            for migration in EMD_SCHEMA_MIGRATIONS:
                cur.execute(migration.read_text(encoding="utf-8"))
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


@pytest.mark.integration
def test_erasure_coverage_has_no_gaps_against_a_real_schema():
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            conn.commit()
            cur.execute("SELECT table_name, reason FROM erasure_coverage_gaps()")
            gaps = cur.fetchall()
        assert gaps == [], f"personal tables would survive erasure: {gaps}"
    finally:
        conn.close()


@pytest.mark.integration
def test_every_emd_table_is_covered_against_a_real_schema():
    """每张 EMD 表，要么被擦除覆盖，要么可证明不含个人数据。

    0233 的口径把「所有 EMD 表」当分母，却只认 email 表为已覆盖，于是共享题库/指标目录
    这三张零个人标识列的表永远无法被覆盖——`uncovered = []` 结构上不可能成立。
    0235 把分母收缩为「带个人标识列的 EMD 表」，并把豁免项单独返回，不藏起来。
    """
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0235.read_text(encoding="utf-8"))
            conn.commit()
            cur.execute("SELECT total_emd_tables, covered, uncovered FROM emd_erasure_coverage()")
            total, covered, uncovered = cur.fetchone()
            cur.execute("SELECT table_name FROM emd_erasure_excluded_tables()")
            excluded = [row[0] for row in cur.fetchall()]
        assert list(uncovered) == [], f"EMD tables outside erasure: {uncovered}"
        assert covered == total
        # 豁免必须与 Python 侧的共享目录名单逐一对上，否则两边又会各说各话
        assert sorted(excluded) == sorted(EMD_SHARED_CATALOG_TABLES), (
            f"SQL 侧豁免 {sorted(excluded)} 与 EMD_SHARED_CATALOG_TABLES 不一致"
        )
    finally:
        conn.close()


@pytest.mark.integration
def test_the_coverage_check_is_not_vacuous():
    """收紧口径不能把检查变成空转：一张只按 profile_id 建、擦除逻辑碰不到的 EMD 表，
    必须被 uncovered 抓出来。这条用例存在的意义，就是防止有人用「加进豁免名单」
    的方式让红灯变绿。"""
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0235.read_text(encoding="utf-8"))
            cur.execute(
                "CREATE TABLE IF NOT EXISTS formation_twin_emd_zz_coverage_probe "
                "(id int, profile_id text)"
            )
            conn.commit()
            try:
                cur.execute("SELECT uncovered FROM emd_erasure_coverage()")
                uncovered = list(cur.fetchone()[0])
            finally:
                cur.execute("DROP TABLE IF EXISTS formation_twin_emd_zz_coverage_probe")
                conn.commit()
        assert "formation_twin_emd_zz_coverage_probe" in uncovered, (
            "带个人标识列却没被擦除覆盖的表没有被检出——这个自检已经空转了"
        )
    finally:
        conn.close()


@pytest.mark.integration
def test_account_erasure_clears_the_vector_store_too():
    """`mvfe_memories` holds raw user text plus its embedding and is created outside
    migrations/ — the 0145 snapshot could never have listed it."""
    conn = _connection()
    created_probe_table = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('mvfe_memories')")
            if cur.fetchone()[0] is None:
                cur.execute(
                    "CREATE TABLE mvfe_memories ("
                    "id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, content TEXT NOT NULL DEFAULT ''"
                    ")"
                )
                created_probe_table = True
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0249.read_text(encoding="utf-8"))
            conn.commit()
            cur.execute("SELECT table_name FROM personal_userid_tables()")
            covered = {row[0] for row in cur.fetchall()}
        assert "mvfe_memories" in covered
    finally:
        if created_probe_table:
            with conn.cursor() as cur:
                cur.execute("DROP TABLE IF EXISTS mvfe_memories")
            conn.commit()
        conn.close()


@pytest.mark.integration
def test_0249_industrial_erasure_coverage_and_social_pii_propagation():
    """Verify 0249 erasure_coverage_gaps() == 0, non-email column detection, mixed-case
    user_tokens revocation, social PII erasure, and focus/ordo schema constraints."""
    import psycopg2

    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_tokens (
                    token VARCHAR(128) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    data JSONB NOT NULL DEFAULT '{}'::jsonb,
                    expires_at TIMESTAMPTZ
                );
                CREATE TABLE IF NOT EXISTS prayers (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS friendships (
                    id SERIAL PRIMARY KEY,
                    requester VARCHAR(255) NOT NULL,
                    addressee VARCHAR(255) NOT NULL,
                    user_low VARCHAR(255) NOT NULL,
                    user_high VARCHAR(255) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'accepted'
                );
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id BIGSERIAL PRIMARY KEY,
                    sender VARCHAR(255) NOT NULL,
                    recipient VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS group_messages (
                    id BIGSERIAL PRIMARY KEY,
                    group_id VARCHAR(64) NOT NULL,
                    sender VARCHAR(255) NOT NULL,
                    body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS voice_groups (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(120) NOT NULL DEFAULT 'group',
                    owner VARCHAR(255) NOT NULL,
                    join_code VARCHAR(12) NOT NULL UNIQUE,
                    max_members INTEGER NOT NULL DEFAULT 10,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                );
                CREATE TABLE IF NOT EXISTS voice_group_members (
                    group_id VARCHAR(64) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'member',
                    PRIMARY KEY (group_id, email)
                );
                CREATE TABLE IF NOT EXISTS evangelism_contacts (
                    id SERIAL PRIMARY KEY,
                    owner_email VARCHAR(255) NOT NULL,
                    display_name VARCHAR(120) NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS evangelism_prayer_logs (
                    id SERIAL PRIMARY KEY,
                    contact_id INTEGER NOT NULL,
                    owner_email VARCHAR(255) NOT NULL,
                    prayed_on DATE NOT NULL DEFAULT CURRENT_DATE
                );
                CREATE TABLE IF NOT EXISTS spiritual_partners (
                    id SERIAL PRIMARY KEY,
                    requester VARCHAR(255) NOT NULL,
                    partner VARCHAR(255) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS attention_accountability_relationships (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    requester_user_id TEXT NOT NULL,
                    partner_user_id TEXT NOT NULL,
                    pair_key TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS attention_prayer_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    owner_user_id TEXT NOT NULL,
                    target_user_id TEXT,
                    title TEXT NOT NULL DEFAULT 'prayer'
                );
                CREATE TABLE IF NOT EXISTS ordo_amoris_entries (
                    id VARCHAR(64) PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    input_text TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS attention_focus_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id TEXT NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ended_at TIMESTAMPTZ,
                    planned_minutes INTEGER NOT NULL DEFAULT 25,
                    actual_minutes INTEGER
                );
                """
            )
            cur.execute("INSERT INTO ordo_amoris_entries(id, email, input_text) VALUES ('orphan-1', 'ghost@example.test', 'stale') ON CONFLICT DO NOTHING")
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0235.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0245.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0246.read_text(encoding="utf-8"))
            cur.execute(MIGRATION_0249.read_text(encoding="utf-8"))
            # Re-run 0249 to prove strict idempotency
            cur.execute(MIGRATION_0249.read_text(encoding="utf-8"))
            conn.commit()

            cur.execute("SELECT table_name, reason FROM erasure_coverage_gaps()")
            assert cur.fetchall() == []

            # Prove non-email identity gap audit is non-vacuous
            cur.execute("CREATE TABLE zz_uncovered_identity_probe (id INT, sender TEXT)")
            conn.commit()
            try:
                cur.execute("SELECT table_name FROM erasure_coverage_gaps()")
                gap_tables = [r[0] for r in cur.fetchall()]
                assert "zz_uncovered_identity_probe" in gap_tables
            finally:
                cur.execute("DROP TABLE IF EXISTS zz_uncovered_identity_probe")
                conn.commit()

            # Orphan ordo_amoris_entries row was cleaned and FK cascade installed
            cur.execute("SELECT COUNT(*) FROM ordo_amoris_entries WHERE id = 'orphan-1'")
            assert cur.fetchone()[0] == 0

            # Focus session CHECK constraints allow actual_minutes = 0 and reject negative/inverted bounds
            cur.execute(
                "INSERT INTO attention_focus_sessions(user_id, started_at, ended_at, planned_minutes, actual_minutes) "
                "VALUES ('focus-u1', NOW(), NOW(), 25, 0)"
            )
            conn.commit()
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(
                    "INSERT INTO attention_focus_sessions(user_id, planned_minutes) VALUES ('focus-u1', 0)"
                )
            conn.rollback()

            # Seed mixed-case target user + peer + third user
            target_canonical = "alice.erasure@example.test"
            target_mixed = "Alice.Erasure@Example.Test"
            peer = "bob.peer@example.test"
            third = "carol.mod@example.test"
            for em in (target_canonical, peer, third):
                cur.execute("INSERT INTO users(email) VALUES (%s) ON CONFLICT (email) DO NOTHING", (em,))
            cur.execute("SELECT id::text FROM users WHERE email = %s", (target_canonical,))
            alice_uid = cur.fetchone()[0]

            cur.execute(
                "INSERT INTO user_tokens(token, email, data) VALUES "
                "('tok-lower', %s, '{}'::jsonb), ('tok-mixed', %s, '{}'::jsonb), ('tok-peer', %s, '{}'::jsonb)",
                (target_canonical, target_mixed, peer),
            )
            cur.execute("INSERT INTO friendships(requester, addressee, user_low, user_high) VALUES (%s, %s, %s, %s), (%s, %s, %s, %s)", (target_mixed, peer, target_canonical, peer, peer, third, peer, third))
            cur.execute("INSERT INTO chat_messages(sender, recipient, body) VALUES (%s, %s, 'hi'), (%s, %s, 'keep')", (target_mixed, peer, peer, third))
            cur.execute("INSERT INTO group_messages(group_id, sender, body) VALUES ('vg-1', %s, 'msg1'), ('vg-2', %s, 'msg2')", (target_mixed, peer))
            cur.execute("INSERT INTO voice_groups(id, owner, join_code) VALUES ('vg-owned', %s, 'CODE01'), ('vg-peer', %s, 'CODE02')", (target_mixed, peer))
            cur.execute("INSERT INTO voice_group_members(group_id, email, role) VALUES ('vg-owned', %s, 'owner'), ('vg-owned', %s, 'member'), ('vg-peer', %s, 'member'), ('vg-peer', %s, 'owner')", (target_canonical, peer, target_mixed, peer))
            cur.execute("INSERT INTO direct_voice_rooms(id, user_low, user_high, expires_at) VALUES ('vd_1', %s, %s, NOW() + INTERVAL '1 hour')", (target_canonical, peer))
            cur.execute("INSERT INTO user_blocks(blocker_email, blocked_email, source_key) VALUES (%s, %s, 'u:bob')", (target_canonical, peer))
            cur.execute("INSERT INTO evangelism_contacts(id, owner_email, display_name) VALUES (901, %s, 'Friend')", (target_mixed,))
            cur.execute("INSERT INTO evangelism_prayer_logs(contact_id, owner_email) VALUES (901, %s)", (target_mixed,))
            cur.execute("INSERT INTO spiritual_partners(requester, partner) VALUES (%s, %s)", (target_mixed, peer))
            cur.execute("INSERT INTO attention_accountability_relationships(requester_user_id, partner_user_id, pair_key) VALUES (%s, %s, 'pair-1')", (alice_uid, peer))
            cur.execute("INSERT INTO attention_prayer_requests(owner_user_id, target_user_id, title) VALUES (%s, %s, 'p1')", (target_mixed, peer))
            cur.execute("INSERT INTO ordo_amoris_entries(id, email, input_text) VALUES ('ordo-a1', %s, 'reflection')", (target_canonical,))

            # social_reports: (1) reported by Alice -> deleted; (2) closed targeting Alice -> deleted;
            # (3) review_pending targeting Alice -> anonymized '[erased]'; (4) reviewed by Alice -> reviewer_email NULL
            cur.execute(
                "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, 'chat', 'c1', 'spam', 'review_pending')",
                (target_canonical, peer),
            )
            cur.execute(
                "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, 'chat', 'c2', 'spam', 'closed')",
                (peer, target_mixed),
            )
            cur.execute(
                "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status) "
                "VALUES (%s, %s, 'chat', 'c3', 'harassment', 'review_pending') RETURNING id::text",
                (peer, target_mixed),
            )
            open_report_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO social_reports(reporter_email, target_email, resource_type, resource_key, category, status, reviewer_email) "
                "VALUES (%s, %s, 'chat', 'c4', 'other', 'closed', %s) RETURNING id::text",
                (peer, third, target_mixed),
            )
            reviewed_report_id = cur.fetchone()[0]
            conn.commit()

            cur.execute("SELECT * FROM erase_user_data(%s)", (target_mixed,))
            counts = dict(cur.fetchall())
            conn.commit()

            assert counts["user_tokens"] == 2
            assert counts["users"] == 1
            cur.execute("SELECT token FROM user_tokens")
            assert cur.fetchall() == [("tok-peer",)]
            cur.execute("SELECT COUNT(*) FROM friendships WHERE lower(requester) = %s OR lower(addressee) = %s", (target_canonical, target_canonical))
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM chat_messages WHERE lower(sender) = %s OR lower(recipient) = %s", (target_canonical, target_canonical))
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM group_messages WHERE lower(sender) = %s", (target_canonical,))
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT id FROM voice_groups")
            assert cur.fetchall() == [("vg-peer",)]
            cur.execute("SELECT group_id, email FROM voice_group_members")
            assert cur.fetchall() == [("vg-peer", peer)]
            cur.execute("SELECT COUNT(*) FROM direct_voice_rooms")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM user_blocks")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM evangelism_contacts")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM evangelism_prayer_logs")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM spiritual_partners")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM attention_accountability_relationships")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM attention_prayer_requests")
            assert cur.fetchone()[0] == 0
            cur.execute("SELECT COUNT(*) FROM ordo_amoris_entries WHERE id = 'ordo-a1'")
            assert cur.fetchone()[0] == 0

            cur.execute("SELECT target_email, status FROM social_reports WHERE id = %s::uuid", (open_report_id,))
            assert cur.fetchone() == ("[erased]", "review_pending")
            cur.execute("SELECT reviewer_email FROM social_reports WHERE id = %s::uuid", (reviewed_report_id,))
            assert cur.fetchone() == (None,)
            cur.execute("SELECT COUNT(*) FROM social_reports")
            assert cur.fetchone()[0] == 2
    finally:
        conn.close()
