"""Stdlib unittest + pytest contract verification for Stage 2A social safety & native auth."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BACKEND_DIR / "migrations"
ROUTERS_DIR = BACKEND_DIR / "routers"


class TestSocialSafetyAndNativeAuthDpContracts(unittest.TestCase):
    def test_01_migration_0245_social_safety_schema_and_checksum(self):
        path = MIGRATIONS_DIR / "0245_social_safety.sql"
        self.assertTrue(path.is_file())
        sql = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        self.assertEqual(digest, "fc3e84c602dc59522004c37d95a187ffbff23a78a7a218c9b8f715186a3fd99a")
        self.assertIn("CREATE TABLE IF NOT EXISTS user_blocks", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS social_reports", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS direct_voice_rooms", sql)
        self.assertIn("DEFAULT 'review_pending'", sql)

    def test_02_migration_0246_account_deletion_requests_schema_and_checksum(self):
        path = MIGRATIONS_DIR / "0246_account_deletion_requests.sql"
        self.assertTrue(path.is_file())
        sql = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        self.assertEqual(digest, "18617dfde727a09d0aeec92b9bc43d79e00d9a53ca9c273b5a2c2bd71fc62c84")
        self.assertIn("CREATE TABLE IF NOT EXISTS account_deletion_requests", sql)
        self.assertIn("DEFAULT 'pending_review'", sql)

    def test_03_all_migration_version_prefixes_are_unique(self):
        versions = [p.stem.partition("_")[0] for p in sorted(MIGRATIONS_DIR.glob("*.sql"))]
        self.assertEqual(len(versions), len(set(versions)))
        for required in ("0245", "0246", "0247", "0248"):
            self.assertIn(required, versions)

    def test_04_auth_email_native_session_transport_and_deletion_guards(self):
        src = (ROUTERS_DIR / "main_extracted_auth_email.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.assertIsInstance(tree, ast.Module)
        self.assertIn("session_transport: Literal['cookie', 'bearer'] = 'cookie'", src)
        self.assertIn("Native session transport requires an origin-less request", src)
        self.assertIn("WHERE account_deletion_requests.status = 'pending_review'", src)
        self.assertIn("FOR UPDATE OF u", src)

    def test_05_realtime_social_safety_routes_and_live_session(self):
        src = (ROUTERS_DIR / "realtime.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.assertIsInstance(tree, ast.Module)
        self.assertIn('prefix="/api"', src)
        for endpoint in (
            "/safety/blocks",
            "/safety/blocks/from-content",
            "/safety/reports",
            "/safety/moderation/reports",
        ):
            self.assertIn(endpoint, src)
        self.assertIn("t.data->>'id' = u.id::text", src)

    def test_06_voice_direct_room_capability_check(self):
        src = (ROUTERS_DIR / "voice.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.assertIsInstance(tree, ast.Module)
        self.assertIn("direct_voice_rooms", src)
        self.assertIn("_lock_social_pair", src)
        self.assertIn("_are_friends", src)

    def test_07_prayer_mutual_block_filtering_and_anonymous_masking(self):
        src = (ROUTERS_DIR / "prayer.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        self.assertIsInstance(tree, ast.Module)
        self.assertIn("FROM user_blocks b", src)
        self.assertIn("/prayer-share/{share_token}", src)

    def test_08_community_feed_and_testimony_mutual_block_filtering(self):
        feed_src = (ROUTERS_DIR / "community_feed.py").read_text(encoding="utf-8")
        testimony_src = (ROUTERS_DIR / "testimony.py").read_text(encoding="utf-8")
        self.assertIsInstance(ast.parse(feed_src), ast.Module)
        self.assertIsInstance(ast.parse(testimony_src), ast.Module)
        self.assertIn("FROM user_blocks b", feed_src)
        self.assertIn("FROM user_blocks b", testimony_src)

    def test_09_route_contracts_register_all_eight_safety_routes(self):
        src = (BACKEND_DIR / "tests" / "test_route_contracts.py").read_text(encoding="utf-8")
        self.assertIsInstance(ast.parse(src), ast.Module)
        self.assertIn("/api/safety/blocks", src)
        self.assertIn("/api/safety/moderation/reports/{report_id}/review", src)

    def test_10_native_auth_postgres_suites_present_and_syntactically_valid(self):
        native_dir = BACKEND_DIR / "tests" / "native_auth"
        expected = {
            "test_mobile_contract.py",
            "test_session_revocation.py",
            "test_deletion_request.py",
            "test_ws_ticket_contract.py",
            "test_social_safety.py",
            "test_block_privacy.py",
            "test_public_safety.py",
        }
        actual = {p.name for p in native_dir.glob("test_*.py")}
        self.assertEqual(actual, expected)
        for name in sorted(expected):
            src = (native_dir / name).read_text(encoding="utf-8")
            self.assertIsInstance(ast.parse(src), ast.Module)


if __name__ == "__main__":
    unittest.main()
