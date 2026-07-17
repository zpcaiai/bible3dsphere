# SLO and Error Budget

## Initial Targets

- Governance read API availability: 99.5% monthly.
- Safety gate decision availability: 99.9% monthly.
- Scenario simulation p95 latency: under 800 ms excluding network.
- Kill switch propagation: under 60 seconds after activation.
- User rights intake availability: 99.5% monthly.

## Error Budget Rules

Safety, privacy, deletion, and crisis errors are not budgetable. They require incident handling and may block release expansion even if aggregate availability remains healthy.

## Measurement Boundary

Current repository evidence includes deterministic unit tests and synthetic rule benchmarks. Production SLOs require live telemetry, dashboards, alerting, and load tests against the deployed stack.
