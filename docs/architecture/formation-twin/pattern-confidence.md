# Pattern Confidence

Pattern confidence means only “how much the current eligible evidence supports
this specific, scoped hypothesis.” It is not severity, personality, maturity,
holiness, truthfulness, or change capacity.

Algorithm `pattern-confidence-1.0`:

1. remove invalidated and superseded evidence;
2. retain the strongest item in each independent-source group;
3. weight by source quality, relevance, and temporal relevance;
4. calculate support and counterevidence separately;
5. adjust support by evidence diversity, scope consistency, and recency;
6. apply only an explicit user-confirmation adjustment;
7. bound the result to `[0,1]` and map it to VERY_LOW, LOW, MODERATE, or HIGH.

The stored numeric value is an internal evidence calculation. The UI presents a
plain-language evidence level and rationale, never a percentage about the user.
New counterevidence lowers confidence. Deleted evidence is invalidated and then
recalculated. Explicit rejection returns zero current support regardless of how
many model or rule observations exist. Every calculation is append-only in
`formation_twin_pattern_confidence_history` with its algorithm version.
