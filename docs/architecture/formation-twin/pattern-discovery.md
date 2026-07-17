# Pattern Discovery

Pattern discovery consumes already-structured, user-eligible Formation Chains.
It does not scan a user's complete diary corpus and does not infer a hidden
motive from a repeated emotion word.

The deterministic rule engine groups the metadata-only chain signature:

- ordered Formation Node types;
- ordered non-causal relation types;
- independent source/life-event group;
- optional confirmed Life Season and life domain.

A candidate requires at least three independent events or two user-confirmed
Formation Chains. Multiple nodes derived from one journal share an
`independence_group` and count once. A structure limited to one confirmed Life
Season is `LIFE_SEASON_SPECIFIC`; it is never promoted to a global profile.

Grace evidence, protective factors, and recovery responses generate first-class
positive candidates. Alternative chains remain marked as alternative responses.
Every candidate includes reasons, limitations, supporting references, a review
date, and a user-confirmation requirement. Rejected signatures are preserved and
not reactivated by rebuild.

Optional model inference is disabled by default and may receive only authorized,
redacted summaries plus support, counterevidence, scope, and prior rejection
feedback. Model failure cannot block deterministic updates.
