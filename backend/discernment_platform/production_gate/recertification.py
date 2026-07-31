from __future__ import annotations


TRIGGERS = {
    "model_change": {
        "theology_gospel_quality",
        "model_prompt_rag_governance",
        "pastoral_psychological_spiritual_safety",
    },
    "prompt_change": {
        "model_prompt_rag_governance",
        "theology_gospel_quality",
    },
    "policy_change": {
        "pastoral_psychological_spiritual_safety",
        "privacy_consent_data_rights",
        "security_authorization_tenant_isolation",
    },
    "pack_change": {
        "theology_gospel_quality",
        "scripture_exegesis_evidence_quality",
    },
    "new_jurisdiction": {"privacy_consent_data_rights"},
    "new_high_risk_feature": {"ALL"},
    "incident": {"ALL"},
    "authorization_change": {
        "privacy_consent_data_rights",
        "security_authorization_tenant_isolation",
    },
    "data_migration": {
        "privacy_consent_data_rights",
        "reliability_observability_incident",
    },
    "scheduled_expiry": {"ALL"},
}


def required_domains_for_trigger(trigger_type: str) -> list[str]:
    if trigger_type not in TRIGGERS:
        raise ValueError(f"Unknown trigger: {trigger_type}")
    return sorted(TRIGGERS[trigger_type])
