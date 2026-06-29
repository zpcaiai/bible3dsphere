"""Spiritual Formation engines (stateless, server-side port of the frontend logic).

Two pure engines mirror the client recommendation and plan generators so the
same "sin pattern -> new creation" guidance can be produced by any client.

- ``recommend_spiritual_response`` scores likely sin patterns from an emotion,
  triggers, free-text behavior, and an optional user-selected pattern, and
  returns possible core lies, gospel truths, target fruits/virtues, and a few
  concrete practices.
- ``generate_transformation_plan`` builds a 7-day / 30-day / 90-day / 1-year
  plan with daily and weekly practices scaled by spiritual intensity.

Nothing here touches the database; the router exposes thin wrappers.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

# ── Pattern metadata (display fields the engines need) ────────────────────────
# Kept in sync with the frontend data/sinPatterns.ts seed content.
PATTERN_META: Dict[str, dict] = {
    "self_centeredness": {
        "name": "Self-Centeredness",
        "core_lie": "My life belongs to me, and I have the right to define what is good for me.",
        "gospel_truth": "I have been crucified with Christ. I no longer live for myself, but Christ lives in me.",
        "opposite_virtues": ["obedience", "humility", "worship", "faith"],
        "target_fruits": ["faithfulness", "gentleness", "self_control"],
        "category": "prayer",
        "daily": ["Morning surrender prayer", "One hidden act of service", "Evening review of self-centered reactions"],
        "emergency": ["Pause before reacting", "Pray: Lord, not my will but Yours", "Ask: Am I protecting my kingdom or seeking God's kingdom?"],
        "weekly": ["Sabbath reflection on control", "Serve someone who cannot repay you", "Share one area of self-rule with accountability"],
    },
    "idolatry": {
        "name": "Idolatry",
        "core_lie": "This created thing can give me the security, identity, joy, or salvation that only God can give.",
        "gospel_truth": "God Himself is my portion, treasure, refuge, and exceeding joy.",
        "opposite_virtues": ["worship", "faith", "contentment", "obedience"],
        "target_fruits": ["love", "joy", "faithfulness"],
        "category": "worship",
        "daily": ["Identify one thing you fear losing", "Pray a surrender prayer over it", "Practice gratitude for God Himself"],
        "emergency": ["Ask: What am I afraid to lose?", "Pray Psalm 73:25-26", "Choose one act of obedience that weakens the idol"],
        "weekly": ["Idol audit journal", "Worship without asking for outcomes", "Give away time, money, or attention to loosen attachment"],
    },
    "greed_consumerism": {
        "name": "Greed and Consumerism",
        "core_lie": "If I have more, I will finally be safe and satisfied.",
        "gospel_truth": "My Father knows what I need. My life does not consist in the abundance of possessions.",
        "opposite_virtues": ["contentment", "generosity", "faith", "righteousness"],
        "target_fruits": ["self_control", "goodness", "joy"],
        "category": "generosity",
        "daily": ["Gratitude list of three provisions", "Pause before purchase", "Pray before checking finances"],
        "emergency": ["Wait 24 hours before buying", "Pray Luke 12:15", "Give a small amount to someone in need"],
        "weekly": ["Review spending with prayer", "Practice generosity", "Fast from non-essential shopping"],
    },
    "sexual_disorder": {
        "name": "Sexual Disorder",
        "core_lie": "My body and desires belong to me, and sexual pleasure can heal, satisfy, or define me.",
        "gospel_truth": "My body is a temple of the Holy Spirit. I was bought with a price, therefore I glorify God with my body.",
        "opposite_virtues": ["holiness", "purity", "faithfulness"],
        "target_fruits": ["self_control", "faithfulness", "love"],
        "category": "body_stewardship",
        "daily": ["Morning body surrender prayer", "Remove one temptation gateway", "Practice seeing people as image-bearers"],
        "emergency": ["Leave the tempting environment immediately", "Contact accountability partner", "Pray 1 Corinthians 6:19-20", "Do a physical reset"],
        "weekly": ["Confession with trusted mature believer if needed", "Digital boundary review", "Scripture memorization on holiness"],
    },
    "pride": {
        "name": "Pride",
        "core_lie": "I must be above others, and I do not truly need correction, mercy, or dependence.",
        "gospel_truth": "God gives grace to the humble. My worth is not in superiority but in Christ's mercy.",
        "opposite_virtues": ["humility", "obedience", "truthfulness"],
        "target_fruits": ["gentleness", "patience", "faithfulness"],
        "category": "confession",
        "daily": ["Pray Philippians 2", "Practice one hidden humility action", "Ask where I defended my ego today"],
        "emergency": ["Pause before defending yourself", "Say: I may be wrong", "Ask one clarifying question before responding"],
        "weekly": ["Invite feedback", "Serve in a low-status task", "Confess pride to God and, if appropriate, to another person"],
    },
    "lies_falsehood": {
        "name": "Lies and Falsehood",
        "core_lie": "Truth is too dangerous, so I must manage reality to protect myself.",
        "gospel_truth": "Because I am accepted in Christ, I do not need to live by lies.",
        "opposite_virtues": ["truthfulness", "righteousness", "humility", "faithfulness"],
        "target_fruits": ["faithfulness", "goodness", "peace"],
        "category": "truth_telling",
        "daily": ["Truth audit", "One honest confession to God", "Speak one truthful sentence you were avoiding"],
        "emergency": ["Pause before answering", "Choose plain truth", "Say: I need to be honest"],
        "weekly": ["Review image-management patterns", "Confess one hidden area to God", "Practice transparent communication"],
    },
    "hatred_division": {
        "name": "Violence, Hatred and Division",
        "core_lie": "My anger is righteous enough to justify contempt, revenge, or destruction.",
        "gospel_truth": "Christ has forgiven me. I can entrust justice to God and pursue peace.",
        "opposite_virtues": ["forgiveness", "mercy"],
        "target_fruits": ["peace", "patience", "gentleness", "love"],
        "category": "reconciliation",
        "daily": ["Bless one difficult person in prayer", "Delay angry responses", "Examine contempt in the heart"],
        "emergency": ["Do not respond for 24 hours if emotionally flooded", "Pray Romans 12:19", "Ask: What would peace require now?"],
        "weekly": ["Reconciliation review", "Forgiveness prayer", "Practice gentle speech"],
    },
    "injustice_oppression": {
        "name": "Injustice and Oppression",
        "core_lie": "My advantage matters more than righteousness, mercy, and the good of my neighbor.",
        "gospel_truth": "God loves righteousness and defends the weak. In Christ, I am called to mercy and justice.",
        "opposite_virtues": ["justice", "mercy", "compassion", "righteousness"],
        "target_fruits": ["goodness", "kindness", "love", "faithfulness"],
        "category": "justice_mercy",
        "daily": ["Pray for one vulnerable person or group", "Choose fairness over advantage", "Notice one person usually ignored"],
        "emergency": ["Ask: Am I using power to serve or exploit?", "Choose the righteous action even if costly"],
        "weekly": ["Mercy action", "Justice audit of work and money", "Serve someone in need"],
    },
    "religious_hypocrisy": {
        "name": "Religious Hypocrisy",
        "core_lie": "If I appear spiritual, I do not need to be truly exposed and changed before God.",
        "gospel_truth": "God desires truth in the inward being, and Christ receives honest sinners.",
        "opposite_virtues": ["truthfulness", "humility", "reverence", "obedience"],
        "target_fruits": ["faithfulness", "gentleness", "love"],
        "category": "confession",
        "daily": ["Pray Psalm 139:23-24", "Name one hidden motive", "Do one unseen act of obedience"],
        "emergency": ["Ask whether I seek God's approval or people's admiration", "Choose hidden faithfulness over visible performance"],
        "weekly": ["Hidden service", "Honest confession", "Review motives in ministry or religious activity"],
    },
    "coldness_lack_of_love": {
        "name": "Coldness and Lack of Love",
        "core_lie": "I am not responsible to love unless it is convenient, safe, or emotionally rewarding.",
        "gospel_truth": "Christ loved me when I was helpless. His love now moves me toward others.",
        "opposite_virtues": ["compassion", "mercy", "kindness"],
        "target_fruits": ["love", "kindness", "goodness", "patience"],
        "category": "service",
        "daily": ["Ask who needs love from me today", "Send one encouragement", "Pray for a suffering person"],
        "emergency": ["When tempted to withdraw, ask what love would require"],
        "weekly": ["Visit, call, or help someone weak or lonely", "Practice mercy giving", "Review relational coldness"],
    },
    "entertainment_escapism": {
        "name": "Entertainment Escapism",
        "core_lie": "Distraction can give me the rest, comfort, and life that only God can give.",
        "gospel_truth": "God Himself is my refuge and rest. I do not need endless stimulation to be safe.",
        "opposite_virtues": ["faith", "reverence", "obedience"],
        "target_fruits": ["self_control", "peace", "joy"],
        "category": "digital_boundary",
        "daily": ["Ten minutes of silence", "No-screen window before sleep", "Scripture before scrolling"],
        "emergency": ["Put phone away physically", "Set a 10-minute prayer timer", "Read one Psalm aloud"],
        "weekly": ["Digital Sabbath block", "Review screen time", "Replace one entertainment block with worship or service"],
    },
    "babel_pride": {
        "name": "Babel-like Technological and Civilizational Pride",
        "core_lie": "Human power, technology, and achievement can secure our future and give us glory without God.",
        "gospel_truth": "Unless the Lord builds the house, those who build it labor in vain.",
        "opposite_virtues": ["humility", "faith", "reverence", "obedience"],
        "target_fruits": ["faithfulness", "self_control", "gentleness"],
        "category": "prayer",
        "daily": ["Pray before work", "Ask if this is for God's glory or my name", "Practice one limit against productivity idolatry"],
        "emergency": ["Pause when ambition becomes restless", "Pray Psalm 127:1", "Ask what obedience looks like, not just optimization"],
        "weekly": ["Review ambition before God", "Sabbath from productivity", "Serve someone without strategic benefit"],
    },
    "spiritual_numbness": {
        "name": "Spiritual Numbness",
        "core_lie": "It is safe to remain spiritually dull, delayed, or indifferent.",
        "gospel_truth": "Today, if I hear His voice, I must not harden my heart. Christ disciplines those He loves and calls them back.",
        "opposite_virtues": ["reverence", "holiness", "obedience", "faith"],
        "target_fruits": ["faithfulness", "self_control", "love"],
        "category": "scripture",
        "daily": ["Pray for conviction", "Read a warning passage slowly", "Do one immediate obedience action"],
        "emergency": ["Say aloud: Today, I will not harden my heart", "Contact a mature believer if numbness persists", "Remove one compromise"],
        "weekly": ["Extended confession", "Accountability conversation", "Review delayed obedience"],
    },
}

SIN_PATTERN_IDS = list(PATTERN_META.keys())

GENERAL_PRACTICES = {
    "morning_surrender": {"id": "practice_morning_surrender", "name": "Morning Surrender Prayer", "category": "prayer", "frequency": "daily"},
    "evening_examen": {"id": "practice_evening_examen", "name": "Evening Examen", "category": "confession", "frequency": "daily"},
    "scripture_meditation": {"id": "practice_scripture_meditation", "name": "Scripture Meditation", "category": "scripture", "frequency": "daily"},
    "confession_prayer": {"id": "practice_confession_prayer", "name": "Confession Prayer", "category": "confession", "frequency": "daily"},
    "hidden_service": {"id": "practice_hidden_service", "name": "Hidden Service", "category": "service", "frequency": "daily"},
    "accountability_checkin": {"id": "practice_accountability_checkin", "name": "Accountability Check-in", "category": "accountability", "frequency": "weekly"},
}

# ── Recommendation rule tables (mirror recommendationEngine.ts) ───────────────
EMOTION_RULES: Dict[str, dict] = {
    "anxiety": {"patterns": ["greed_consumerism", "self_centeredness", "idolatry", "babel_pride"],
                "lies": ["I must be in control to be safe.", "God may not provide what I need.", "If I lose this, I cannot be okay."],
                "fruits": ["peace", "faithfulness", "self_control"]},
    "anger": {"patterns": ["hatred_division", "pride", "self_centeredness"],
              "lies": ["I have the right to punish.", "My will must be honored.", "Contempt will protect me."],
              "fruits": ["patience", "gentleness", "peace"]},
    "envy": {"patterns": ["greed_consumerism", "idolatry", "pride"],
             "lies": ["God has been better to them than to me.", "My worth depends on having what they have.", "I cannot rejoice unless I am above others."],
             "fruits": ["joy", "love", "goodness"]},
    "lust": {"patterns": ["sexual_disorder", "idolatry", "entertainment_escapism"],
             "lies": ["This desire can satisfy me.", "My body belongs to me.", "Secret pleasure will heal my emptiness."],
             "fruits": ["self_control", "faithfulness", "love"]},
    "emptiness": {"patterns": ["entertainment_escapism", "idolatry", "spiritual_numbness"],
                  "lies": ["Distraction can fill me.", "God is not enough right now.", "I cannot face silence."],
                  "fruits": ["joy", "peace", "self_control"]},
    "shame": {"patterns": ["lies_falsehood", "religious_hypocrisy", "spiritual_numbness"],
              "lies": ["I must hide to be safe.", "If I am known, I will be rejected.", "Appearance matters more than truth."],
              "fruits": ["faithfulness", "peace", "gentleness"]},
    "prideful_confidence": {"patterns": ["pride", "babel_pride", "religious_hypocrisy", "self_centeredness"],
                            "lies": ["I do not need correction.", "My wisdom is sufficient.", "My achievements prove my worth."],
                            "fruits": ["gentleness", "faithfulness", "self_control"]},
    "numbness": {"patterns": ["spiritual_numbness", "entertainment_escapism", "religious_hypocrisy"],
                 "lies": ["Delayed obedience is safe.", "This sin is not serious.", "I can return to God later."],
                 "fruits": ["faithfulness", "love", "self_control"]},
}

TRIGGER_RULES: Dict[str, List[str]] = {
    "pressure": ["self_centeredness", "entertainment_escapism", "babel_pride", "greed_consumerism"],
    "loneliness": ["entertainment_escapism", "sexual_disorder", "idolatry", "coldness_lack_of_love"],
    "comparison": ["pride", "greed_consumerism", "idolatry"],
    "success": ["pride", "babel_pride", "religious_hypocrisy"],
    "failure": ["lies_falsehood", "entertainment_escapism", "self_centeredness", "spiritual_numbness"],
    "rejection": ["idolatry", "hatred_division", "lies_falsehood", "pride"],
    "offense": ["hatred_division", "pride", "self_centeredness"],
    "financial_insecurity": ["greed_consumerism", "idolatry", "babel_pride"],
    "sexual_temptation": ["sexual_disorder", "entertainment_escapism", "idolatry"],
    "boredom": ["entertainment_escapism", "spiritual_numbness", "sexual_disorder"],
    "fatigue": ["entertainment_escapism", "coldness_lack_of_love", "self_centeredness"],
    "conflict": ["hatred_division", "pride", "lies_falsehood"],
    "social_media": ["entertainment_escapism", "greed_consumerism", "idolatry", "pride", "sexual_disorder"],
    "power_opportunity": ["injustice_oppression", "pride", "babel_pride"],
    "religious_performance": ["religious_hypocrisy", "pride", "lies_falsehood"],
}

BEHAVIOR_KEYWORDS: Dict[str, List[str]] = {
    "self_centeredness": ["my way", "control", "interrupted", "entitled", "serve me", "my plan"],
    "idolatry": ["can't live without", "obsessed", "ultimate", "must have", "afraid to lose"],
    "greed_consumerism": ["money", "buy", "shopping", "investment", "rich", "house", "stock", "financial", "possessions", "spending"],
    "sexual_disorder": ["porn", "lust", "sexual", "fantasy", "body", "temptation", "impure"],
    "pride": ["better than", "look down", "defensive", "criticized", "prove myself", "superior", "correction"],
    "lies_falsehood": ["lied", "hide", "exaggerate", "fake", "pretend", "cover up", "image"],
    "hatred_division": ["hate", "revenge", "angry", "attack", "insult", "contempt", "unforgive"],
    "injustice_oppression": ["unfair", "exploit", "oppress", "power", "profit", "weak", "worker", "poor"],
    "religious_hypocrisy": ["perform", "spiritual image", "church image", "pretend godly", "judge others", "religious"],
    "coldness_lack_of_love": ["cold", "ignore", "don't care", "indifferent", "avoid needy", "lack compassion"],
    "entertainment_escapism": ["scroll", "video", "game", "netflix", "youtube", "tiktok", "bilibili", "escape", "distract", "procrastinate", "phone"],
    "babel_pride": ["technology", "ai", "build", "scale", "fame", "achievement", "startup", "optimize", "efficiency", "make a name"],
    "spiritual_numbness": ["numb", "no feeling", "delay", "not serious", "don't care", "avoid god", "harden", "obedience"],
}

PASTORAL_NOTES: Dict[str, str] = {
    "entertainment_escapism": "This may be a moment to bring your restlessness to God instead of escaping into stimulation. Do not begin with self-hatred. Begin by returning to Christ and choosing one small act of stillness.",
    "greed_consumerism": "This may be an invitation to examine where money or possession has become a false refuge. God is not against wise provision, but He calls your heart to trust Him above wealth.",
    "hatred_division": "This anger may need to be brought into the light before it becomes contempt. Christ invites you to entrust justice to God and practice one step toward peace.",
}

DEFAULT_PASTORAL_NOTE = (
    "This may indicate a pattern worth bringing before God in prayer. The app "
    "cannot diagnose your heart with certainty, but it can help you come into "
    "the light and choose one concrete act of obedience."
)

INTENSITIES = ["light", "normal", "deep", "battle"]
DURATIONS = ["7_days", "30_days", "90_days", "1_year"]
_DURATION_DAYS = {"7_days": 7, "30_days": 30, "90_days": 90, "1_year": 365}


def _unique(items: List) -> List:
    seen = set()
    out = []
    for item in items:
        key = item if isinstance(item, str) else id(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _build_practice(pattern_id: str, name: str, category: str, frequency: str) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return {
        "id": f"{pattern_id}_{slug}_{frequency}",
        "name": name,
        "category": category,
        "frequency": frequency,
        "estimatedMinutes": 25 if frequency == "weekly" else 5 if frequency == "as_needed" else 10,
    }


def _pattern_practices(pattern_id: str, kind: str, frequency: str) -> List[dict]:
    meta = PATTERN_META[pattern_id]
    return [_build_practice(pattern_id, name, meta["category"], frequency) for name in meta[kind]]


def recommend_spiritual_response(
    *,
    emotion: Optional[str] = None,
    triggers: Optional[List[str]] = None,
    behavior_text: str = "",
    selected_sin_pattern: Optional[str] = None,
) -> dict:
    """Score likely sin patterns and return non-shaming formation guidance."""
    scores: Dict[str, float] = {pid: 0 for pid in SIN_PATTERN_IDS}
    possible_core_lies: List[str] = []
    suggested_fruits: List[str] = []

    def add(pattern: str, points: float) -> None:
        if pattern in scores:
            scores[pattern] += points

    if selected_sin_pattern:
        add(selected_sin_pattern, 6)

    rule = EMOTION_RULES.get(emotion) if emotion else None
    if rule:
        for index, pattern in enumerate(rule["patterns"]):
            add(pattern, 5 - index)
        possible_core_lies.extend(rule["lies"])
        suggested_fruits.extend(rule["fruits"])

    for trigger in (triggers or []):
        for index, pattern in enumerate(TRIGGER_RULES.get(trigger, [])):
            add(pattern, 3 - min(index, 2))

    text = (behavior_text or "").lower()
    for pattern, keywords in BEHAVIOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                add(pattern, 3)

    scored = [(pid, scores[pid]) for pid in SIN_PATTERN_IDS if scores[pid] > 0]
    scored.sort(key=lambda kv: kv[1], reverse=True)
    likely = [pid for pid, _ in scored[:3]]

    top = likely[0] if likely else "self_centeredness"
    top_patterns = likely if likely else [top]

    gospel_truths = [PATTERN_META[p]["gospel_truth"] for p in top_patterns]
    virtues = _unique([v for p in top_patterns for v in PATTERN_META[p]["opposite_virtues"]])
    pattern_fruits = [f for p in top_patterns for f in PATTERN_META[p]["target_fruits"]]
    practices: List[dict] = []
    for p in top_patterns:
        practices.extend(_pattern_practices(p, "daily", "daily")[:2])
    practices = practices[:4]

    return {
        "likelySinPatterns": top_patterns,
        "possibleCoreLies": _unique(possible_core_lies + [PATTERN_META[p]["core_lie"] for p in top_patterns])[:5],
        "suggestedGospelTruths": _unique(gospel_truths),
        "suggestedFruits": _unique(suggested_fruits + pattern_fruits)[:5],
        "suggestedVirtues": virtues[:5],
        "suggestedPractices": practices,
        "pastoralNote": PASTORAL_NOTES.get(top, DEFAULT_PASTORAL_NOTE),
    }


def _add_days(start: str, days: int) -> str:
    y, m, d = (int(x) for x in start.split("-"))
    return (date(y, m, d) + timedelta(days=days)).isoformat()


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _duration_label(duration: str) -> str:
    return {
        "7_days": "7-Day Awareness",
        "30_days": "30-Day Mortification",
        "90_days": "90-Day Formation",
        "1_year": "1-Year New Creation Map",
    }[duration]


def _review_questions(duration: str) -> List[str]:
    if duration == "7_days":
        return ["Which sin pattern appeared most often?", "What emotion usually came before it?", "What trigger usually activated it?", "What lie did I believe?", "Where did I see God's grace?"]
    if duration == "30_days":
        return ["What did I put off this week?", "What did I put on this week?", "When did temptation become strongest?", "What boundary needs strengthening?", "What fruit is beginning to appear?"]
    if duration == "90_days":
        return ["Month 1: where did awareness and confession increase?", "Month 2: what boundaries helped mortification?", "Month 3: what new obedience and fruit are becoming more natural?", "Which relationships show fruit?", "Where do I still resist God?"]
    return ["Quarter 1: where is holiness and self-control needed?", "Quarter 2: where is humility and obedience needed?", "Quarter 3: where is love, mercy, and compassion needed?", "Quarter 4: where is justice, faithfulness, and worship needed?", "What next formation theme is God bringing into the light?"]


def _title_for(duration: str, pattern_name: str, virtue: str) -> str:
    if duration == "7_days":
        return f"7-Day Awareness: Seeing {pattern_name}"
    if duration == "30_days":
        return f"30-Day Mortification: Putting Off {pattern_name} and Putting On {virtue}"
    if duration == "90_days":
        return f"90-Day Formation: From {pattern_name} to Christlike {virtue}"
    return "1-Year New Creation Map: Growing in Holiness, Love, and Obedience"


def get_intensity_description(intensity: str) -> dict:
    return {
        "light": {"title": "Light", "dailyMinutes": "10 minutes", "description": "For beginners, spiritually weak users, or users recovering from burnout."},
        "normal": {"title": "Normal", "dailyMinutes": "25-40 minutes", "description": "For stable believers with a sustainable daily rhythm."},
        "deep": {"title": "Deep", "dailyMinutes": "60-90 minutes", "description": "For mature disciples, leaders, or serious spiritual formation."},
        "battle": {"title": "Battle", "dailyMinutes": "morning + midday + evening check-ins", "description": "For acute temptation or recurring bondage with boundaries and accountability."},
    }[intensity]


def generate_transformation_plan(
    *,
    duration: str,
    intensity: str,
    primary_sin_pattern: str,
    secondary_sin_pattern: Optional[str] = None,
    start_date: Optional[str] = None,
) -> dict:
    """Build a transformation plan scaled by duration and intensity."""
    if duration not in _DURATION_DAYS:
        raise ValueError(f"Unknown duration: {duration}")
    if intensity not in INTENSITIES:
        raise ValueError(f"Unknown intensity: {intensity}")
    if primary_sin_pattern not in PATTERN_META:
        raise ValueError(f"Unknown sin pattern: {primary_sin_pattern}")
    if secondary_sin_pattern and secondary_sin_pattern not in PATTERN_META:
        raise ValueError(f"Unknown sin pattern: {secondary_sin_pattern}")

    primary = PATTERN_META[primary_sin_pattern]
    secondary = PATTERN_META.get(secondary_sin_pattern) if secondary_sin_pattern else None
    start = start_date or _today_iso()
    now = datetime.now(timezone.utc).isoformat()

    primary_daily = _pattern_practices(primary_sin_pattern, "daily", "daily")
    primary_emergency = _pattern_practices(primary_sin_pattern, "emergency", "as_needed")
    primary_weekly = _pattern_practices(primary_sin_pattern, "weekly", "weekly")
    secondary_weekly = _pattern_practices(secondary_sin_pattern, "weekly", "weekly") if secondary_sin_pattern else []

    if duration == "7_days":
        base_daily = [GENERAL_PRACTICES["scripture_meditation"], GENERAL_PRACTICES["evening_examen"], *primary_daily[:2]]
    else:
        base_daily = [GENERAL_PRACTICES["morning_surrender"], GENERAL_PRACTICES["scripture_meditation"], GENERAL_PRACTICES["evening_examen"], *primary_daily[:3]]
    battle_daily = [*base_daily, *primary_emergency[:3]] if intensity == "battle" else base_daily
    deep_daily = [*battle_daily, GENERAL_PRACTICES["confession_prayer"], GENERAL_PRACTICES["hidden_service"]] if intensity == "deep" else battle_daily

    weekly = [GENERAL_PRACTICES["accountability_checkin"], *primary_weekly[:3], *secondary_weekly[:1]]

    target_fruits = _unique([*primary["target_fruits"], *(secondary["target_fruits"] if secondary else [])])
    target_virtues = _unique([*primary["opposite_virtues"], *(secondary["opposite_virtues"] if secondary else [])])

    accountability = (
        " This plan is not meant to be fought alone. If this pattern is recurring or destructive, "
        "invite a mature believer, pastor, counselor, or trusted accountability partner into the process."
        if intensity == "battle" else ""
    )

    return {
        "title": _title_for(duration, primary["name"], target_virtues[0] if target_virtues else "Obedience"),
        "duration": duration,
        "intensity": intensity,
        "primarySinPattern": primary_sin_pattern,
        "secondarySinPattern": secondary_sin_pattern,
        "targetFruits": target_fruits,
        "targetVirtues": target_virtues,
        "dailyPractices": deep_daily[:2] if intensity == "light" else deep_daily,
        "weeklyPractices": weekly[:2] if intensity == "light" else weekly,
        "reviewQuestions": _review_questions(duration),
        "progressSummary": (
            f"{_duration_label(duration)} follows this movement: identify, bring into light, "
            f"confess, repent, put off, put on, practice, bear fruit, and review.{accountability}"
        ),
        "recommendedNextStep": (
            "Invite real accountability today and remove access to the strongest trigger."
            if intensity == "battle" else
            "Begin with today's Scripture, confession, and one concrete obedience action."
        ),
        "startDate": start,
        "endDate": _add_days(start, _DURATION_DAYS[duration]),
        "status": "active",
        "completedPracticeIds": [],
        "createdAt": now,
        "updatedAt": now,
    }


# ===========================================================================
# Holy Life — deep formation engines (William Law "A Serious Call")
# Pure, deterministic, no LLM. Mirrors the client generators so any caller
# (server, scheduler, other Formation OS modules) can produce the same
# Purpose discernment, dynamic Rule of Life, and Horarium streaks.
# ===========================================================================

HOLY_LIFE_SKILL_BRIEF = {
    "morning_consecration": {"short": "晨间奉献", "metric": "Consecration Score",
        "practice": "慢慢读奉献祷告，并写下今天最容易抓在自己手里的一个领域。"},
    "purpose_reset": {"short": "目的重置", "metric": "Purpose Purity",
        "practice": "选今天最重要的一件事，写下真实动机，再把它改写成敬拜的目的。"},
    "presence_of_god": {"short": "神同在练习", "metric": "Living Before God",
        "practice": "点击一次同在暂停，记录一句此刻的归回。"},
    "thought_examination": {"short": "思想监察", "metric": "Thought Map",
        "practice": "写下一个反复出现的思想，并命名它背后的根。"},
    "intention_inspector": {"short": "动机分析", "metric": "Motivation Radar",
        "practice": "记录今天一个决定，区分表面理由和真实动机。"},
    "holy_speech": {"short": "言语训练", "metric": "Speech Holiness Score",
        "practice": "选一句今天说过的话，写下更像基督的重说版本。"},
    "ordinary_life_worship": {"short": "日常敬拜", "metric": "Ordinary Worship %",
        "practice": "记录一个普通任务，用敬拜语言重新定义它。"},
    "self_denial_trainer": {"short": "舍己训练", "metric": "Self-denial Level",
        "practice": "选择一个小型舍己行动，完成后记录阻力和结果。"},
    "humility_detector": {"short": "谦卑检测", "metric": "Humility Index",
        "practice": "写下一个骄傲反应，并写出一个谦卑替代动作。"},
    "charity_practice": {"short": "爱心操练", "metric": "Love Score",
        "practice": "选择一个人，写下今天可执行的爱心行动。"},
    "evening_examen": {"short": "晚间省察", "metric": "Daily Holiness Report",
        "practice": "写下感谢、认罪、顺服、明日更新各一句。"},
    "eternal_perspective": {"short": "永恒视角", "metric": "Eternal Readiness",
        "practice": "用永恒视角写一句今天的评估和明天的调整。"},
}

HOLY_LIFE_SKILL_IDS = list(HOLY_LIFE_SKILL_BRIEF.keys())

# Idol / heart-orientation keyword rules for purpose discernment.
PURPOSE_IDOL_RULES = [
    ("approval", ["认可", "被看见", "被夸", "面子", "好评", "点赞", "approval", "praise",
                  "recognition", "看不起", "丢脸", "肯定"]),
    ("control", ["控制", "掌控", "确定", "把控", "安排", "control", "certainty"]),
    ("security", ["安全", "保障", "失业", "养家", "security", "income", "savings", "退路", "稳定"]),
    ("comfort", ["舒适", "轻松", "逃避", "享受", "comfort", "escape", "avoid", "懒"]),
    ("power", ["权力", "地位", "赢", "胜过", "power", "status", "win", "掌权"]),
    ("comparison", ["比较", "比得过", "超过", "compare", "better than", "不如别人"]),
]

PURPOSE_KINGDOM_KEYWORDS = ["荣耀神", "爱邻舍", "爱人", "忠心", "服侍", "顺服", "glorify",
                            "serve", "faithful", "obey", "神的旨意", "天国", "怜悯", "祝福别人"]

HEART_ADVICE = {
    "approval": "你真正渴望的是被接纳。福音说：在基督里你已被天父完全接纳，不必再用表现去赚取认可。",
    "control": "你想抓住确定与掌控。神是掌权者；今天可以把一个无法掌控的结果交还给祂。",
    "security": "你在寻找安全感。神是你的供应与避难所；忠心去做，把供应交托给祂。",
    "comfort": "你在寻求舒适与逃避。背起十字架的爱，常意味着选择更难但更像基督的一步。",
    "power": "你渴望地位与胜过别人。基督的道路是降卑与服侍；今天可主动选择隐藏的服侍。",
    "comparison": "你被比较捆绑。你的价值不在于胜过谁，而在于神看你为祂所爱的儿女。",
    "kingdom": "你的动机指向神的国与爱邻舍。求主保守这份纯一，并提防把善行变成自我证明。",
    "unexamined": "继续在神面前诚实地追问『我为什么要做这件事』，直到看见心的真实朝向。",
}


def discern_purpose(*, task: str, stated_reason: str = "", answers=None) -> dict:
    """Five-question 'why ladder' purpose discernment. Pure rule-based.

    Detects likely root idols vs. kingdom orientation and returns
    non-shaming formation guidance and a kingdom-alignment score (0-100).
    """
    answers = [str(a) for a in (answers or []) if str(a).strip()]
    blob = " ".join([task or "", stated_reason or "", *answers]).lower()

    idol_hits = []
    for idol, keywords in PURPOSE_IDOL_RULES:
        if any(k.lower() in blob for k in keywords):
            idol_hits.append(idol)

    kingdom = any(k.lower() in blob for k in PURPOSE_KINGDOM_KEYWORDS)

    if idol_hits:
        heart = idol_hits[0]
    elif kingdom:
        heart = "kingdom"
    else:
        heart = "unexamined"

    score = 60
    if kingdom:
        score += 20
    score -= 12 * len(idol_hits)
    if heart == "kingdom" and not idol_hits:
        score = max(score, 82)
    score = max(5, min(100, score))

    deep_reason = answers[-1] if answers else (stated_reason or "尚未追问到更深的动机")

    return {
        "task": task,
        "surfaceReason": stated_reason or (answers[0] if answers else ""),
        "deepReason": deep_reason,
        "heartOrientation": heart,
        "possibleIdols": idol_hits,
        "kingdomAlignment": score,
        "formationAdvice": HEART_ADVICE.get(heart, HEART_ADVICE["unexamined"]),
        "reflectionQuestions": [
            "我真正渴望从这件事得到什么？",
            "如果得不到，我会有什么情绪？这暴露了什么？",
            "这是否符合爱神、并爱邻舍如己？",
            "我愿意把结果交托给神吗？",
            "下一步忠心而具体的行动是什么？",
        ],
        "todayPrayer": "主啊，鉴察我，知道我的心思；试炼我，知道我的意念。洁净我的动机，使我今天所做的归向你的荣耀与爱。",
    }


def weakest_skill_from_entries(entries) -> Optional[str]:
    """Given holy-life entries [{skillId, score}, ...], return the lowest-scoring skill id."""
    best = None
    best_score = None
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        sid = entry.get("skillId") or entry.get("skill_id")
        if sid not in HOLY_LIFE_SKILL_BRIEF:
            continue
        try:
            sc = int(entry.get("score", 0))
        except Exception:
            sc = 0
        if best_score is None or sc < best_score:
            best_score = sc
            best = sid
    return best


def generate_rule_of_life(*, intention: str = "", focus_skill_id=None, weakest_skill_id=None) -> dict:
    """Generate today's Rule of Life from intention + the skill most needing attention.

    Pure rule-based; mirrors the client generator so server and client agree.
    """
    skill_id = focus_skill_id or weakest_skill_id or "purpose_reset"
    if skill_id not in HOLY_LIFE_SKILL_BRIEF:
        skill_id = "purpose_reset"
    skill = HOLY_LIFE_SKILL_BRIEF[skill_id]
    intent = (intention or "").strip() or "今天把普通生活献给神"
    return {
        "theme": f"{skill['short']}：{skill['metric']}",
        "morningPrayer": f"主啊，{intent}。求你洁净我的动机，使今天的时间、言语和选择都归向你。",
        "dailyPractice": skill["practice"],
        "decisionGuardrail": f"今天每个重要决定先问：这是否出于爱、真理、谦卑，并能使我更忠心？当前需警醒：{skill['short']}。",
        "eveningExamen": "今晚回看：我在哪些普通时刻记得神？哪里只是追随自己？明天一步顺服是什么？",
        "focusSkillId": skill_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


# ---- Horarium (fixed-hour prayer) — William Law's hours of prayer ----------

HORARIUM_HOURS = [
    {"id": "early_morning", "time": "06:00", "subject": "Praise", "title": "晨起 · 赞美与奉献",
     "scripture": "诗篇 5:3", "focus": "以赞美和感恩开始，将整天献给神。",
     "prompt": "今晨我要为什么赞美神？我把今天的哪一部分交托给祂？"},
    {"id": "third_hour", "time": "09:00", "subject": "Humility", "title": "第三时 · 谦卑",
     "scripture": "腓立比书 2:5-8", "focus": "求主对付骄傲，操练谦卑。",
     "prompt": "我在哪里想证明自己？如何效法基督的降卑？"},
    {"id": "sixth_hour", "time": "12:00", "subject": "Universal Love", "title": "第六时 · 普世之爱与代祷",
     "scripture": "提摩太前书 2:1", "focus": "为他人代求，操练爱与怜悯。",
     "prompt": "今天我为谁代祷？我可以向谁行出爱？"},
    {"id": "ninth_hour", "time": "15:00", "subject": "Resignation", "title": "第九时 · 顺服神的旨意",
     "scripture": "路加福音 22:42", "focus": "在一切际遇中降服于神的旨意。",
     "prompt": "我此刻在抗拒神的什么安排？我愿意说『愿你的旨意成就』吗？"},
    {"id": "evening", "time": "18:00", "subject": "Confession", "title": "傍晚 · 认罪与省察",
     "scripture": "诗篇 139:23-24", "focus": "认罪、领受赦免、修复关系。",
     "prompt": "今天我亏欠了神或人什么？我要如何认罪与修复？"},
    {"id": "compline", "time": "21:30", "subject": "Eternity", "title": "睡前 · 默想永恒",
     "scripture": "诗篇 90:12", "focus": "数算自己的日子，预备见主。",
     "prompt": "如果今夜见主，我预备好了吗？今天有什么值得感谢与悔改？"},
]

HORARIUM_HOUR_IDS = [h["id"] for h in HORARIUM_HOURS]


def compute_streak(dates) -> dict:
    """Current + longest consecutive-day streak from ISO date strings or date objects.

    'current' counts back from today (or yesterday if today is missing) so a
    not-yet-done today does not reset the streak until it is actually skipped.
    """
    norm = set()
    for d in dates or []:
        if isinstance(d, str):
            try:
                norm.add(date.fromisoformat(d[:10]))
            except Exception:
                continue
        elif isinstance(d, date):
            norm.add(d)
    if not norm:
        return {"current": 0, "longest": 0, "total": 0, "lastDate": None}

    ordered = sorted(norm)
    longest = run = 1
    for i in range(1, len(ordered)):
        run = run + 1 if (ordered[i] - ordered[i - 1]).days == 1 else 1
        longest = max(longest, run)

    today = datetime.now(timezone.utc).date()
    anchor = today if today in norm else (today - timedelta(days=1))
    current = 0
    cursor = anchor
    while cursor in norm:
        current += 1
        cursor = cursor - timedelta(days=1)

    return {"current": current, "longest": longest, "total": len(norm), "lastDate": ordered[-1].isoformat()}
