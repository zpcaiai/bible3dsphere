"""Erasure verification that does not need a running database.

The integration pass in `test_emd_deletion_propagation.py` needs a live Postgres, so on
most machines it skips — and a check that always skips is not a check. This module gets
as close as is honestly possible without a server:

1. **Real PostgreSQL grammar.** Every EMD migration is parsed with `pglast` (libpg_query,
   the actual server parser). A typo that would only surface at deploy time fails here.
2. **The coverage logic, replayed against the real DDL.** `personal_email_tables()` and
   friends are set operations over the catalog. This module rebuilds that catalog from
   every `CREATE TABLE` in `migrations/`, replays the same set logic, and asserts zero
   gaps — using the exclusion lists **parsed out of the migration**, not copied into the
   test, so the two cannot drift apart.

What this deliberately does **not** claim: that the plpgsql bodies execute. `pglast` sees
the function body as a string literal. Executing it needs a server, which is why
`scripts/verify_emd_erasure.py` exists — one command, run it against staging.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

pglast = pytest.importorskip("pglast", reason="pglast provides the real PostgreSQL parser")

from emd_schema_catalog import catalog, columns_of  # noqa: E402
from formation_twin.emotional_maturity_erasure import (  # noqa: E402
    EMD_PERSONAL_TABLES,
    EMD_SHARED_CATALOG_TABLES,
)


pytestmark = pytest.mark.no_db
BACKEND = Path(__file__).resolve().parents[1]
MIGRATIONS = BACKEND / "migrations"
MIGRATION_0233 = MIGRATIONS / "0233_emd_erasure_propagation.sql"

# ── 1) 真实 PostgreSQL 语法 ──────────────────────────────────────────────────

def emd_migrations() -> list[Path]:
    paths = set(MIGRATIONS.glob("*emd*.sql"))
    paths.add(MIGRATIONS / "0223_formation_twin_emotional_maturity.sql")
    return sorted(path for path in paths if path.exists())


@pytest.mark.parametrize("path", emd_migrations(), ids=lambda p: p.name)
def test_migration_parses_as_real_postgresql(path):
    pglast.parse_sql(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", sorted((MIGRATIONS / "rollback").glob("*emd*.sql")), ids=lambda p: p.name)
def test_rollback_parses_as_real_postgresql(path):
    pglast.parse_sql(path.read_text(encoding="utf-8"))


def test_the_parser_would_actually_catch_a_typo():
    """A guard against the check silently degrading into a no-op."""
    with pytest.raises(Exception):
        pglast.parse_sql("CREATE TALBE oops (id int);")


# ── 2) 从迁移重建目录，回放覆盖逻辑 ──────────────────────────────────────────

def scrub_only_tables() -> set[str]:
    """Read the exclusion list out of the migration rather than restating it."""
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    block = sql.split("erasure_scrub_only_tables()")[1]
    array = block[block.index("ARRAY["): block.index("]::text[]")]
    return set(re.findall(r"'([a-z_]+)'", array))


def userid_excluded_tables() -> set[str]:
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    block = sql.split("erasure_userid_excluded_tables()")[1]
    array = block[block.index("ARRAY["): block.index("]::text[]")]
    return set(re.findall(r"'([a-z_]+)'", array))


def simulated_personal_email_tables() -> set[str]:
    return {
        name for name, columns in catalog().items()
        if "email" in columns and name not in scrub_only_tables()
    }


def simulated_personal_userid_tables() -> set[str]:
    email_tables = simulated_personal_email_tables()
    excluded = scrub_only_tables() | userid_excluded_tables()
    return {
        name for name, columns in catalog().items()
        if "user_id" in columns and name not in excluded and name not in email_tables
    }


def test_the_parser_sees_columns_packed_onto_one_line():
    """The bug this parser was rewritten to fix: EMD migrations put several columns on
    one line, so a line-anchored regex found no `email` column anywhere — and the
    "is every personal table erased?" check silently became an empty-set comparison."""
    body = "    id UUID PRIMARY KEY, tenant_id TEXT NOT NULL, email TEXT NOT NULL,\n    note TEXT"
    assert {"id", "tenant_id", "email", "note"} <= columns_of(body)


def test_commas_inside_types_do_not_split_columns():
    assert columns_of("    amount NUMERIC(10, 2) NOT NULL,\n    email TEXT") == {"amount", "email"}


def test_table_constraints_are_not_mistaken_for_columns():
    columns = columns_of("    email TEXT,\n    UNIQUE(email, tag),\n    PRIMARY KEY (id)")
    assert "email" in columns and "unique" not in columns and "primary" not in columns


def test_the_catalog_rebuild_is_plausible():
    tables = catalog()
    assert len(tables) >= 400, f"only parsed {len(tables)} tables — parser broken?"
    # `users` 本身不在 migrations/ 里（与 mvfe_* 一样建在别处），这正是
    # 快照式清单会漏东西、而目录发现不会的原因。
    assert "users" not in tables
    assert "formation_twin_emd_consents" in tables
    # 空集会让下面每一条覆盖断言都变成真空真理
    email_keyed = sum(1 for columns in tables.values() if "email" in columns)
    assert email_keyed > 200, f"only {email_keyed} email-keyed tables — parser regressed"


def test_no_personal_table_escapes_erasure():
    """This is the assertion `erasure_coverage_gaps()` makes, replayed offline."""
    covered = simulated_personal_email_tables() | simulated_personal_userid_tables()
    excluded = scrub_only_tables() | userid_excluded_tables()
    gaps = sorted(
        name for name, columns in catalog().items()
        if ("email" in columns or "user_id" in columns)
        and name not in covered and name not in excluded
    )
    assert gaps == [], f"personal tables that would survive account erasure: {gaps}"


def test_every_emd_table_is_covered():
    """`emd_erasure_coverage()`: uncovered must be empty."""
    emd = {name for name in catalog() if name.startswith("formation_twin_emd_")}
    covered = simulated_personal_email_tables()
    uncovered = sorted(name for name in emd if name not in covered)
    # 共享题库/指标目录本就无 email 列，属于预期之外
    assert uncovered == sorted(EMD_SHARED_CATALOG_TABLES), (
        f"unexpected EMD tables outside erasure: {set(uncovered) - set(EMD_SHARED_CATALOG_TABLES)}"
    )


def test_the_domain_erase_list_matches_the_catalog():
    """The endpoint's list and the account-level function must agree about EMD."""
    from_catalog = {
        name for name in simulated_personal_email_tables()
        if name.startswith("formation_twin_emd_")
    }
    assert from_catalog == set(EMD_PERSONAL_TABLES), {
        "only_in_catalog": sorted(from_catalog - set(EMD_PERSONAL_TABLES)),
        "only_in_endpoint": sorted(set(EMD_PERSONAL_TABLES) - from_catalog),
    }


# ── 3) 之前漏掉的几张表，逐一钉死 ────────────────────────────────────────────

def test_the_vector_store_is_covered_now():
    """`mvfe_memories` 存用户原文与向量，且建在 migrations/ 之外——
    正因如此，任何快照式清单都不可能列到它，只有目录发现能覆盖。"""
    excluded = scrub_only_tables() | userid_excluded_tables()
    assert "mvfe_memories" not in excluded, "vector store must not be excluded from erasure"
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    assert "personal_userid_tables()" in sql
    assert "mvfe_memories" in sql, "the reason this matters should stay documented in the migration"


@pytest.mark.parametrize("family", ["attention_", "mission_bridge_", "safeguarding_"])
def test_the_userid_only_families_are_covered(family):
    """0145 的快照只列了 4 张 user_id 表，这几族当时全在覆盖之外。"""
    covered = simulated_personal_userid_tables()
    members = {name for name in catalog() if name.startswith(family)}
    if not members:
        pytest.skip(f"no {family}* tables in this schema")
    missed = sorted(
        name for name in members
        if "user_id" in catalog()[name] and name not in covered
        and name not in (scrub_only_tables() | userid_excluded_tables())
        and name not in simulated_personal_email_tables()
    )
    assert missed == [], f"{family}* still outside erasure: {missed}"


def test_shared_content_is_scrubbed_not_deleted():
    """删除共享内容会毁掉其他成员的数据，这几张表必须留在 scrub 名单里。"""
    expected = {
        "accountability_groups", "church_profiles", "churches",
        "formation_tenants", "organizations", "prayer_templates", "users",
    }
    assert expected <= scrub_only_tables()


def test_users_is_handled_last_not_skipped():
    sql = MIGRATION_0233.read_text(encoding="utf-8")
    assert "DELETE FROM users WHERE email = p_email" in sql


# ── 4) 仍然需要真实数据库的部分，明确写出来 ──────────────────────────────────

def test_a_runnable_staging_verifier_exists():
    """离线检查到此为止；plpgsql 能否执行只有服务器能回答。"""
    script = BACKEND / "scripts" / "verify_emd_erasure.py"
    assert script.exists(), "需要一个能对 staging 一键验证的脚本"
    text = script.read_text(encoding="utf-8")
    assert "erasure_coverage_gaps" in text
    assert "emd_erasure_coverage" in text
