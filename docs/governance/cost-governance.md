# Cost Governance

## Principles

- Safety, consent, deletion, and crisis checks are never skipped for budget reasons.
- Expensive model calls are routed through purpose-aware policies and feature flags.
- Scenario simulation uses deterministic rules only and must not call a model.
- Shadow and canary traffic require explicit cost ceilings.

## Required Metrics

- Requests by route, purpose, and component version.
- Model calls by family and safety tier.
- Cache hit rate for read-only governance metadata.
- Error budget burn and retry amplification.
- Cost per active user for Formation Twin surfaces.

## Controls

Cost alerts may reduce optional reflection depth, defer non-urgent summaries, or disable experimental variants. They must not disable kill switches, consent checks, deletion enforcement, or crisis routing.
