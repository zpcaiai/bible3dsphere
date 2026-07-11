"""Canonical Mission OS subdomain names used by flags, events and ownership checks."""

SUBDOMAINS = frozenset({
    "field_intelligence",
    "calling_and_readiness",
    "training",
    "sending",
    "teams_and_partnerships",
    "deployment",
    "field_operations",
    "content_and_localization",
    "member_care",
    "incidents",
    "local_leadership",
    "evaluation",
})

OWNED_AGGREGATES = frozenset({
    "MissionField", "PeopleGroup", "FieldResearchProject", "CallingJourney",
    "WorkerReadinessAssessment", "MissionTrainingPlan", "SendingJourney",
    "MissionTeam", "MissionPartnership", "DeploymentPlan", "MemberCarePlan",
    "MissionIncident", "LocalLeaderDevelopmentPlan", "MissionProgram",
    "MissionEvaluation",
})

EXTERNAL_AGGREGATES = frozenset({
    "User", "IdentityProfile", "GiftProfile", "FormationPlan", "HabitPlan",
    "DiscipleshipJourney", "CrisisCase", "ContentItem", "NotificationPreference",
})
