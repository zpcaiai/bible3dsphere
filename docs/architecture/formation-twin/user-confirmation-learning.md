# User Confirmation Learning

Batch 5 learns how to interpret one user's vocabulary and scope more accurately;
it does not learn how to persuade the user to accept an interpretation.

Supported feedback includes confirmation, partial confirmation, rejection,
relabelling, scope narrowing/expansion, outdated/resolved/still-relevant status,
and do-not-suggest-again. Rejection creates a user-scoped preference keyed to the
pattern signature so rebuild cannot silently reactivate it. Scope feedback is
stored separately from the source pattern.

Interpretation preferences are visible through an owner-only API and can be
revoked individually. They never reduce crisis safety, theological safety,
consent, or review requirements. Third-party and pastoral feedback require a
separate authorization and cannot override current user statements.

Feedback is excluded from shared-model training by default. It cannot be used to
optimize compliance, shame, payment, church profiling, or institutional access.
Events contain IDs and action/status only, not user explanations.
