# Crisis-first processing

Formation Twin reuses the platform bilingual crisis scanner for user-submitted check-in notes, journal text, manual summaries, and confirmed voice transcripts.

When risk is detected, the event is marked `ROUTED_TO_CRISIS`, the API returns the crisis response, and the UI presents the safety entry before any formation action. Crisis content is never copied into the canonical event or domain-event payload. Source adapters may emit only crisis case reference, risk level, status, and whether ordinary formation flow can resume.

The subsystem does not diagnose, replace emergency services, or substitute for a trusted person, pastor, counselor, or clinician.
