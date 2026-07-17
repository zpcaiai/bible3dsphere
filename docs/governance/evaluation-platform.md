# Evaluation Platform

The Batch 10 evaluation registry versions datasets, cases, runs, component references, metrics, and blocker codes. `backend/production_governance/evaluation.py` provides the deterministic runner and built-in safety suite; database records are defined in migration 0220.

Evaluation families are model, prompt, rule, policy, workflow, agent, theological safety, psychological/medical/crisis safety, privacy/consent, relational safety, and tenant isolation. Severe safety failures veto a release even if aggregate quality scores pass. Replays carry a checksum so the same fixed inputs and component versions can be compared without silently changing the test.

The registry does not claim that a dataset is representative, clinically validated, or legal for training. Those are separately reviewed facts.
