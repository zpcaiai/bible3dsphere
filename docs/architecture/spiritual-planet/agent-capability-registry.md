# Agent capability registry

The code registry and `spiritual_planet_agent_capabilities` identify an agent's
owner, version, role, input/output schemas, purposes, projections, sensitivity
access, proposal/execute rights, confirmation requirement and safety policies.

Roles are analyzer, reflection generator, recommendation generator, safety
classifier, command executor, context provider, notification generator and
report generator.

Hard separation:

- analyzers cannot execute commands;
- recommendation generators create proposals only;
- executors act only on confirmed commands;
- safety classifiers route safety and do not issue spiritual verdicts;
- no agent may expand its projection or call an unregistered capability;
- agents do not compete for the user's attention or vote on God's will.

Unregistered capability calls fail closed. Registry visibility is user-safe;
integration health with operational failure details is admin-only.
