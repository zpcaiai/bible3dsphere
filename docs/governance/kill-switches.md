# Kill Switches

## Required Switches

- Scenario simulation.
- Reflection interventions.
- Temptation and relapse early warning.
- Relational collaboration.
- Model-generated spiritual guidance.
- Shadow and canary execution.

## Behavior

Kill switches must fail closed. When disabled, affected routes return a degraded, non-harmful response and write an audit event. They must not silently continue execution.

## Ownership

Every switch requires owner, reason, activation time, and review time. Re-enabling requires release-gate checks when the switch was activated for safety, privacy, or quality reasons.
