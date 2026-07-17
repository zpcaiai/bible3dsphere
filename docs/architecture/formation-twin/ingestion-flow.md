# Formation Twin ingestion flow

```mermaid
flowchart LR
  A["Manual input or authorized module event"] --> B["Schema and identity validation"]
  B --> C["Consent and source status check"]
  C --> D["Crisis-first safety scan"]
  D --> E["Field allowlist and minimization"]
  E --> F["Canonical event normalization"]
  F --> G["PostgreSQL event and receipt"]
  G --> H["Metadata-only domain event"]
  A --> I["AES-256-GCM sensitive-content vault"]
  I --> F
  D -->|"risk detected"| J["Crisis route; formation processing stops"]
```

All writes are synchronous and atomic in the current FastAPI transaction. Replays return the existing canonical event through a subject-scoped idempotency key. Module ingestion requires a service identity and an active, user-authorized source connection. Rejected values are discarded; receipts store field names, never rejected values.
