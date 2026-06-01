"""
sm2_engine.py — 背经间隔重复（SM-2 改良版，纯函数）

评分 grade：0=忘了(again) 1=吃力(hard) 2=记得(good) 3=轻松(easy)
忘了 → 当天再背一次（interval 0，repetitions 归零）；其余按 SM-2 推进。
"""
from __future__ import annotations

from typing import Dict

_GRADE_Q = {0: 2, 1: 3, 2: 4, 3: 5}   # SM-2 quality 0–5


def review(ease: float, interval_days: int, repetitions: int, grade: int) -> Dict[str, float]:
    q = _GRADE_Q.get(int(grade), 4)
    ease = float(ease or 2.5)
    interval = int(interval_days or 0)
    reps = int(repetitions or 0)

    if grade == 0:                       # 忘了：当天重背
        reps, interval = 0, 0
    else:
        if reps == 0:
            interval = 1
        elif reps == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        reps += 1

    ease = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease = max(1.3, round(ease, 3))
    return {"ease": ease, "interval_days": interval, "repetitions": reps,
            "due_offset_days": interval}
