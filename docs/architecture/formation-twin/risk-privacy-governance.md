# Risk Privacy Governance

Risk data is owner-scoped by tenant/profile/email and PostgreSQL RLS. It cannot
be used for church rosters, spouse surveillance, pastoral discipline, employment,
insurance, advertising, pricing, conversion or user comparison. No role receives
default access.

Safe events contain record IDs, version/status, visible warning level, action
type, target module and delivery status. They exclude cycle titles, behavior /
confession/journal bodies, contact/message text, internal risk band, probability
and third-party identity. Lockscreen copy is always generic for sensitive data.

Scoped erasure covers cycles/nodes/edges, conditions, snapshots, warnings,
feedback, actions, plans, contacts/requests, recovery and settings. PostgreSQL
deletion is implemented; optional embedding, graph, cache and external-delivery
cleanup must report their real adapter state rather than imply success.
