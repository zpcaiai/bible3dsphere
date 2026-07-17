# Scenario Evidence Policy

Scenario evidence is a compact reference matrix, not a copied journal or a complete life profile.

Allowed evidence levels are user-confirmed effect, repeated observation, and user-provided context. Each record stores a source reference, a short minimized summary, whether it supports or contradicts a branch, and user confirmation.

Disallowed inputs include unconfirmed inference, deleted/revoked data, another person's private content, full journal text, crisis content, embeddings as hidden evidence, and production data copied into test/evaluation datasets without authorization.

Evidence retention follows the source consent and deletion lifecycle. A deletion or consent withdrawal invalidates dependent scenarios; rebuild must preserve user denials and deletion tombstones. Empty or contradictory evidence is surfaced as uncertainty rather than silently filled by a model.
