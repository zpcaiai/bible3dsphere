"""
theological_safety.py — Advanced Batch · Module 1
TheologicalSafetyService + crisis-language detection.

Two responsibilities:
  1. detect_crisis(text)         — scan USER text for self-harm / danger signals
                                    and return a risk_level the agents must honour.
  2. TheologicalSafetyService    — gate AGENT output against the product's
                                    theological red lines (no prosperity gospel,
                                    no shaming, no "spiritual score = worth",
                                    no "AI replaces your pastor", etc.).

Product line (enforced here, not just hoped for):
  - AI is not a shepherd; it never claims to replace church / pastor / companions.
  - Crisis must connect to a real human; output may never be scripture-only.
  - No legalism, shame, prosperity gospel, or mystical manipulation.

Import-light (re + stdlib + optional db accessor) so it is unit-testable
under ``-m no_db``.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# ── Pluggable DB logging (set by main.py / engines at startup) ───────────────
_get_db: Optional[Callable] = None
_release_db: Optional[Callable] = None


def set_db_accessors(get_db: Callable, release_db: Callable) -> None:
    global _get_db, _release_db
    _get_db, _release_db = get_db, release_db


# ── Crisis detection (scans the USER's words) ────────────────────────────────
# Ordered: critical (imminent danger) first, then high.
_CRITICAL_PATTERNS = [
    r"自杀", r"想死", r"不想活", r"活不下去", r"结束(自己的)?生命", r"了结(自己|生命)",
    r"自残", r"自伤", r"伤害自己", r"轻生",
    r"kill myself", r"end (my|it all|my life)", r"want to die", r"suicid",
    r"i('?m| am) going to (kill|hurt) myself", r"self[\s-]?harm", r"take my (own )?life",
]
_HIGH_PATTERNS = [
    r"没有(任何)?希望", r"绝望", r"撑不下去", r"喘不过气", r"崩溃", r"精神崩溃",
    r"家暴", r"被(家暴|殴打|威胁|虐待)", r"暴力威胁", r"成瘾(失控)?", r"戒不掉", r"吸毒", r"酗酒到失控",
    r"hopeless", r"can('?t| not) go on", r"no reason to live", r"abus(e|ed|ing)",
    r"beaten", r"overdose", r"can('?t| not) stop drinking|using", r"breaking down",
]
_CRITICAL_RE = re.compile("|".join(_CRITICAL_PATTERNS), re.IGNORECASE)
_HIGH_RE = re.compile("|".join(_HIGH_PATTERNS), re.IGNORECASE)

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def max_risk(a: str, b: str) -> str:
    return a if _RISK_ORDER.get(a, 0) >= _RISK_ORDER.get(b, 0) else b


def detect_crisis(text: str) -> Dict[str, object]:
    """Return {'risk_level','matched'} from scanning *text* for danger signals."""
    text = text or ""
    matched: List[str] = []
    risk = "low"
    for m in _CRITICAL_RE.finditer(text):
        matched.append(m.group(0))
        risk = "critical"
    if risk != "critical":
        for m in _HIGH_RE.finditer(text):
            matched.append(m.group(0))
            risk = "high"
    return {"risk_level": risk, "matched": sorted(set(matched))}


# ── Theological red lines (scan the AGENT's output) ──────────────────────────
# Each: (code, compiled regex, severity). severity 'block' => must not ship.
_FORBIDDEN = [
    ("prosperity_faith_blame", r"你?(的)?痛苦.{0,6}(是因为|源于).{0,4}信心不足|因为你信心不够|信心不足.{0,6}(才|所以|导致)", "block"),
    ("toxic_positivity", r"不要(难过|伤心).{0,8}基督徒(应该|就该|要)(喜乐|快乐)|基督徒不(应该|该)(难过|哭|伤心)", "block"),
    ("magic_prayer", r"只要(祷告|祷告就).{0,6}(就会|便会|马上|立刻|立即|一定)(好|痊愈|没事|解决)", "block"),
    ("ai_replaces_pastor", r"(我|AI|本系统).{0,4}(可以|能够|就能).{0,4}(替代|取代|代替).{0,4}(牧者|牧师|教会|辅导员)", "block"),
    ("sin_reductionism", r"(你的)?苦难.{0,6}(一定|必定|肯定|就)是.{0,6}(某个|某种|具体的)?罪(导致|造成|引起)", "block"),
    ("spiritual_score_worth", r"(属灵)?分数.{0,6}(决定|定义|代表).{0,4}(你的)?(价值|好坏)|你的价值.{0,6}取决于.{0,6}(表现|成功|分数)", "block"),
    ("shaming", r"你(真是|就是|这么)(没用|失败|不属灵|糟糕|差劲)|这都是你活该", "block"),
    ("absolute_prophecy", r"神(一定|必定|肯定)(会)?呼召你(去)?做|这(一定|就)是神给你(唯一)?的呼召", "flag"),
]
_FORBIDDEN_RE = [(code, re.compile(pat, re.IGNORECASE), sev) for code, pat, sev in _FORBIDDEN]


@dataclass
class ReviewResult:
    verdict: str = "pass"            # pass | flagged | blocked
    risk_level: str = "low"
    flags: List[dict] = field(default_factory=list)
    redacted_excerpt: str = ""

    @property
    def ok(self) -> bool:
        return self.verdict != "blocked"


def _redact_excerpt(text: str, limit: int = 280) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"…[+{len(text) - limit} chars]"


# Map this module's verdicts/flag-codes onto the concurrent 0075 schema vocab.
_REVIEW_STATUS = {"pass": "approved", "flagged": "needs_revision", "blocked": "blocked"}
_DIMENSION_MAP = {
    "prosperity_faith_blame": "prosperity_gospel",
    "toxic_positivity": "spiritual_shaming",
    "magic_prayer": "prosperity_gospel",
    "ai_replaces_pastor": "ai_replaces_pastor",
    "sin_reductionism": "scripture_misuse",
    "spiritual_score_worth": "spiritual_scoring",
    "shaming": "spiritual_shaming",
    "absolute_prophecy": "mysticism_manipulation",
}


def _to_detected_issues(flags):
    out = []
    for f in flags or []:
        sev = 5 if f.get("severity") == "block" else 3
        out.append({"dimension": _DIMENSION_MAP.get(f.get("code"), f.get("code")),
                    "severity": sev, "note": f.get("code")})
    return out


class TheologicalSafetyService:
    """Reviews user-visible AI content; logs to theological_review_logs."""

    def review(
        self,
        text: str,
        *,
        agent_name: str,
        skill_name: str = "",
        email: Optional[str] = None,
        agent_run_id: Optional[int] = None,
        user_risk_hint: str = "low",
        log: bool = True,
    ) -> ReviewResult:
        flags: List[dict] = []
        verdict = "pass"
        for code, rx, sev in _FORBIDDEN_RE:
            if rx.search(text or ""):
                flags.append({"code": code, "severity": sev})
                verdict = "blocked" if sev == "block" else (verdict if verdict == "blocked" else "flagged")

        # Risk is the max of any caller hint and crisis signals found in the text.
        crisis = detect_crisis(text or "")
        risk = max_risk(user_risk_hint or "low", str(crisis["risk_level"]))

        result = ReviewResult(
            verdict=verdict,
            risk_level=risk,
            flags=flags,
            redacted_excerpt=_redact_excerpt(text),
        )
        if log:
            self._log(result, agent_name=agent_name, skill_name=skill_name,
                      email=email, agent_run_id=agent_run_id)
        return result

    # ── persistence (best-effort; no-op when no DB accessor) ────────────────
    def _log(self, result: ReviewResult, *, agent_name, skill_name, email, agent_run_id) -> None:
        if _get_db is None:
            return
        conn = None
        try:
            import json as _json
            conn = _get_db()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO theological_review_logs
                      (email, agent_run_id, content_type, content_excerpt,
                       review_status, detected_issues, reviewer_notes, reviewer)
                    VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,'agent')
                    """,
                    (email, agent_run_id, (skill_name or agent_name),
                     result.redacted_excerpt, _REVIEW_STATUS.get(result.verdict, 'approved'),
                     _json.dumps(_to_detected_issues(result.flags)),
                     f"agent={agent_name}; risk_level={result.risk_level}"),
                )
            conn.commit()
        except Exception:
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn is not None and _release_db is not None:
                _release_db(conn)


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:12]
