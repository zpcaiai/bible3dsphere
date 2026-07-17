# Time Decay Policy

Time decay changes current relevance; it does not erase history. The configurable
default half-lives are seven days for emotion observations, thirty days for
short-term coping behavior, sixty days for a Formation Chain, 120 days for a
confirmed season pattern, and 365 days for a confirmed long-term pattern.

The standard function is `exp(-ln(2) * age_days / half_life_days)`. A small
positive floor distinguishes old evidence from invalidated evidence. User
“still relevant” feedback overrides ordinary decay and is auditable.

Grief, serious health events, trauma, relationship or church rupture, long-term
care, crisis recovery, relocation, and major calling transitions use
`NON_STANDARD_DECAY`. The engine does not silently decide when these events stop
being relevant. Closing a Life Season triggers review rather than carrying its
patterns into the next season.

Half-life configuration and algorithm version are infrastructure policy. They
must never be exposed as a spiritual score or used to compare users.
