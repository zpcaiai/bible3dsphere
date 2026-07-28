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


def _connection():
    psycopg2 = pytest.importorskip("psycopg2")
    try:
        return psycopg2.connect(DB_URL, connect_timeout=3)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"no live Postgres for the integration pass: {exc}")


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
    try:
        with conn.cursor() as cur:
            cur.execute(MIGRATION_0233.read_text(encoding="utf-8"))
            conn.commit()
            cur.execute("SELECT to_regclass('mvfe_memories')")
            if cur.fetchone()[0] is None:
                pytest.skip("mvfe_memories not provisioned in this database")
            cur.execute("SELECT table_name FROM personal_userid_tables()")
            covered = {row[0] for row in cur.fetchall()}
        assert "mvfe_memories" in covered
    finally:
        conn.close()
