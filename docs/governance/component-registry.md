# Component Registry

The registry covers model, prompt, rule, policy, workflow, and agent components. Each version records an immutable identifier, owner, checksum/reference, risk tier, evaluation reports, approvals, activation, deprecation, and rollback target.

Production activation requires a fixed version; `latest`, missing evaluation evidence, and unapproved high-risk versions fail closed. Rollback activates a previously approved fixed version and writes an audit event. Registration alone never authorizes production use.
