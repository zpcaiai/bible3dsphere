"""Closed ontology for Formation Twin spiritual-formation records.

The ontology is intentionally descriptive.  It does not contain diagnosis,
salvation status, maturity grades, holiness scores, or causal verdicts.
"""
from __future__ import annotations

from enum import Enum


class FormationNodeType(str, Enum):
    LIFE_EVENT = "LIFE_EVENT"
    INTERPRETATION = "INTERPRETATION"
    IDENTITY_STATEMENT = "IDENTITY_STATEMENT"
    BELIEF_STATEMENT = "BELIEF_STATEMENT"
    DESIRE = "DESIRE"
    FEAR = "FEAR"
    EMOTION = "EMOTION"
    TEMPTATION = "TEMPTATION"
    CHOICE = "CHOICE"
    BEHAVIOR = "BEHAVIOR"
    SPIRITUAL_PRACTICE = "SPIRITUAL_PRACTICE"
    OUTCOME = "OUTCOME"
    GRACE_EVIDENCE = "GRACE_EVIDENCE"
    PROTECTIVE_FACTOR = "PROTECTIVE_FACTOR"
    RECOVERY_RESPONSE = "RECOVERY_RESPONSE"
    FORMATION_DIRECTION = "FORMATION_DIRECTION"


class FormationSourceKind(str, Enum):
    USER_REPORT = "USER_REPORT"
    OBSERVATION = "OBSERVATION"
    RULE = "RULE"
    MODEL = "MODEL"
    USER_CONFIRMED = "USER_CONFIRMED"


class FormationStatementType(str, Enum):
    USER_REPORTED_FACT = "USER_REPORTED_FACT"
    OBSERVED_EVENT = "OBSERVED_EVENT"
    RULE_DERIVED_RELATION = "RULE_DERIVED_RELATION"
    MODEL_EXTRACTED_EXPLICIT_EXPRESSION = "MODEL_EXTRACTED_EXPLICIT_EXPRESSION"
    MODEL_FORMATION_HYPOTHESIS = "MODEL_FORMATION_HYPOTHESIS"
    USER_CONFIRMED_FORMATION_PATTERN = "USER_CONFIRMED_FORMATION_PATTERN"


class FormationScope(str, Enum):
    THIS_EVENT_ONLY = "THIS_EVENT_ONLY"
    THIS_SEASON = "THIS_SEASON"
    RECURRING_CONTEXT = "RECURRING_CONTEXT"
    USER_DEFINED = "USER_DEFINED"


class FormationRelation(str, Enum):
    PRECEDED = "PRECEDED"
    FOLLOWED_BY = "FOLLOWED_BY"
    USER_ASSOCIATED_WITH = "USER_ASSOCIATED_WITH"
    USER_DESCRIBED_AS = "USER_DESCRIBED_AS"
    OBSERVED_IN_SAME_EVENT = "OBSERVED_IN_SAME_EVENT"
    POSSIBLY_ASSOCIATED_WITH = "POSSIBLY_ASSOCIATED_WITH"
    USER_CONFIRMED_RELATION = "USER_CONFIRMED_RELATION"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"


NODE_TYPES = tuple(item.value for item in FormationNodeType)
SOURCE_KINDS = tuple(item.value for item in FormationSourceKind)
STATEMENT_TYPES = tuple(item.value for item in FormationStatementType)
SCOPES = tuple(item.value for item in FormationScope)
RELATIONS = tuple(item.value for item in FormationRelation)

DEEP_FORMATION_TYPES = {
    FormationNodeType.INTERPRETATION.value,
    FormationNodeType.IDENTITY_STATEMENT.value,
    FormationNodeType.BELIEF_STATEMENT.value,
    FormationNodeType.DESIRE.value,
    FormationNodeType.FEAR.value,
    FormationNodeType.TEMPTATION.value,
    FormationNodeType.FORMATION_DIRECTION.value,
}

GRACE_AND_RECOVERY_TYPES = {
    FormationNodeType.GRACE_EVIDENCE.value,
    FormationNodeType.PROTECTIVE_FACTOR.value,
    FormationNodeType.RECOVERY_RESPONSE.value,
}

# Only these neutral relations may be created by deterministic rules.
RULE_RELATIONS = {
    FormationRelation.PRECEDED.value,
    FormationRelation.FOLLOWED_BY.value,
    FormationRelation.OBSERVED_IN_SAME_EVENT.value,
}

# Context modules receive codes and short user-confirmed summaries only.
CONTEXT_FIELD_ALLOWLISTS = {
    "formation": {
        "snapshot_id", "window_start", "window_end", "confirmed_patterns",
        "user_reported_items", "observed_relations", "grace_and_recovery",
        "reflective_questions", "limitations",
    },
    "prayer": {
        "snapshot_id", "window_start", "window_end", "user_confirmed_prayer_context",
        "grace_and_recovery", "reflective_questions", "limitations",
    },
    "habit": {
        "snapshot_id", "window_start", "window_end", "user_confirmed_practice_context",
        "protective_factors", "reflective_questions", "limitations",
    },
    "attention": {
        "snapshot_id", "window_start", "window_end", "user_confirmed_attention_context",
        "protective_factors", "reflective_questions", "limitations",
    },
}


def is_known_node_type(value: str) -> bool:
    return value in NODE_TYPES


def is_known_relation(value: str) -> bool:
    return value in RELATIONS
