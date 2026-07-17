# Early Warning Policy

Internal risk bands select safety routing but are never exposed as a score.
User-visible levels are `AWARENESS`, `PROTECTION_SUGGESTED`,
`IMMEDIATE_SUPPORT_SUGGESTED` and `CRISIS_HANDOFF`; `NO_WARNING` produces no
delivery.

A single ordinary condition is capped at awareness. Multiple independent
conditions from a user-confirmed cycle may suggest protection. An explicit
current urge, behavior-start report or request for help can enter immediate
support without waiting for a complete match. Crisis Care remains authoritative.

Every warning names bounded conditions, active protection/counterevidence,
unknowns and uncertainty. Default cooldowns are 12 hours for awareness and four
hours for protection suggestions. Quiet hours, pause and false-positive
recalibration suppress ordinary delivery. Copy is not optimized for clicks or
fear, and no relapse probability is calculated or displayed.
