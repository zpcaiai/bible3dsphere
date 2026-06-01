"""Unit tests for sm2_engine (pure SM-2)."""
import sm2_engine as s


def test_good_progression_1_6_then_grows():
    c = {"ease": 2.5, "interval_days": 0, "repetitions": 0}
    r1 = s.review(c["ease"], c["interval_days"], c["repetitions"], 2)
    assert r1["interval_days"] == 1 and r1["repetitions"] == 1
    r2 = s.review(r1["ease"], r1["interval_days"], r1["repetitions"], 2)
    assert r2["interval_days"] == 6 and r2["repetitions"] == 2
    r3 = s.review(r2["ease"], r2["interval_days"], r2["repetitions"], 2)
    assert r3["interval_days"] > 6 and r3["repetitions"] == 3


def test_forget_resets():
    r = s.review(2.5, 15, 3, 0)   # grade 0 = 忘了
    assert r["interval_days"] == 0 and r["repetitions"] == 0


def test_ease_floor_1_3():
    ease = 2.5
    for _ in range(10):
        r = s.review(ease, 1, 1, 0)
        ease = r["ease"]
    assert ease >= 1.3
