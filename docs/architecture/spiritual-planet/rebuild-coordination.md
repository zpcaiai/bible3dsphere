# Rebuild coordination

Scopes are single record, single module, Formation Twin state, long-term
patterns, unified context, full user derived state and tenant migration.

Principles:

- never overwrite raw history;
- preserve user confirmations, rejections and corrections;
- never reactivate a rejected hypothesis because a model changed;
- create a new version and an auditable difference report;
- keep engine/rule/schema versions and support operator rollback;
- rate-limit bulk jobs.

Unified context rebuild completes synchronously because platform contexts are
ephemeral and regenerated under current consent. Other scopes remain `QUEUED`
until the owning source module registers a worker. The API reports preserved
review counts and will not claim that a missing worker completed a rebuild.
