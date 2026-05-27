"""
Tests for backend/preference_vector.py and the fusion logic.
Uses a mock DB pool so no real database is needed.
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, '/sessions/intelligent-dreamy-einstein/mnt/bible3dsphere/backend')
from preference_vector import (
    fuse_query_with_preference,
    get_user_preference_vector,
    ALPHA,
    MIN_FEEDBACK,
)


def _make_pool(rows):
    """Build a minimal mock db_pool that returns given rows."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    pool = MagicMock()
    pool.getconn.return_value = conn
    return pool


class TestFuseQueryWithPreference(unittest.TestCase):

    def test_no_pref_returns_query_unchanged(self):
        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        result = fuse_query_with_preference(q, None)
        np.testing.assert_array_equal(result, q)

    def test_zero_alpha_returns_query_unchanged(self):
        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        p = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        result = fuse_query_with_preference(q, p, alpha=0.0)
        np.testing.assert_array_equal(result, q)

    def test_fused_vector_is_unit_length(self):
        q = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        p = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        result = fuse_query_with_preference(q, p, alpha=0.5)
        self.assertAlmostEqual(float(np.linalg.norm(result)), 1.0, places=5)

    def test_fused_biases_toward_preference(self):
        q = np.array([1.0, 0.0], dtype=np.float32)
        p = np.array([0.0, 1.0], dtype=np.float32)
        # alpha=0.25: result should be closer to q than to p
        result = fuse_query_with_preference(q, p, alpha=0.25)
        self.assertGreater(result[0], result[1])

    def test_full_alpha_approaches_preference(self):
        q = np.array([1.0, 0.0], dtype=np.float32)
        p = np.array([0.0, 1.0], dtype=np.float32)
        result = fuse_query_with_preference(q, p, alpha=1.0)
        self.assertAlmostEqual(float(result[1]), 1.0, places=5)

    def test_default_alpha_constant(self):
        self.assertEqual(ALPHA, 0.25)


class TestGetUserPreferenceVector(unittest.TestCase):

    def test_returns_none_when_no_pool(self):
        pref = get_user_preference_vector("user1", None)
        self.assertIsNone(pref)

    def test_returns_none_when_insufficient_records(self):
        # Only 1 record, MIN_FEEDBACK=2
        pool = _make_pool([([0.1, 0.2, 0.3],)])
        pref = get_user_preference_vector("user1", pool, min_feedback=2)
        self.assertIsNone(pref)

    def test_returns_unit_vector_with_enough_records(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        pool = _make_pool([(v1,), (v2,)])
        pref = get_user_preference_vector("user1", pool, min_feedback=2)
        self.assertIsNotNone(pref)
        self.assertAlmostEqual(float(np.linalg.norm(pref)), 1.0, places=5)

    def test_preference_is_average_direction(self):
        # Both vectors point in same direction → preference == that direction
        v = [1.0, 0.0, 0.0]
        pool = _make_pool([(v,), (v,)])
        pref = get_user_preference_vector("user1", pool, min_feedback=2)
        self.assertAlmostEqual(float(pref[0]), 1.0, places=5)

    def test_returns_none_on_db_error(self):
        pool = MagicMock()
        pool.getconn.side_effect = RuntimeError("connection refused")
        pref = get_user_preference_vector("user1", pool)
        self.assertIsNone(pref)

    def test_output_dtype_float32(self):
        v = [0.5] * 8
        pool = _make_pool([(v,), (v,)])
        pref = get_user_preference_vector("user1", pool, min_feedback=2)
        self.assertIsNotNone(pref)
        self.assertEqual(pref.dtype, np.float32)


class TestEndToEndFusion(unittest.TestCase):
    """Simulate the full query→fusion→score path."""

    def test_fused_vector_shifts_dot_product(self):
        dim = 8
        rng = np.random.default_rng(42)
        feature_embeddings = rng.standard_normal((20, dim)).astype(np.float32)
        # Normalise
        feature_embeddings /= np.linalg.norm(feature_embeddings, axis=1, keepdims=True)

        query_vec = rng.standard_normal(dim).astype(np.float32)
        query_vec /= np.linalg.norm(query_vec)

        pref_vec = feature_embeddings[0].copy()  # strongly biased toward feature 0

        fused = fuse_query_with_preference(query_vec, pref_vec, alpha=0.5)
        scores_query  = np.dot(feature_embeddings, query_vec)
        scores_fused  = np.dot(feature_embeddings, fused)

        # Feature 0 should rank higher with fused vector
        rank_query = int(np.argsort(scores_query)[::-1].tolist().index(0))
        rank_fused = int(np.argsort(scores_fused)[::-1].tolist().index(0))
        self.assertLess(rank_fused, rank_query,
            f"Expected feature 0 to rank higher with fusion. "
            f"rank_query={rank_query} rank_fused={rank_fused}")


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().loadTestsFromModule(
        __import__('test_preference_vector')
    ))
    sys.exit(0 if result.wasSuccessful() else 1)
