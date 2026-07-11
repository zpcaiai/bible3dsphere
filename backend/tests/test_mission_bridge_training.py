from pathlib import Path
from mission_bridge_training import evaluate_trainer_evidence,REQUIRED_TRAINER_EVIDENCE
def test_training_never_auto_approves():
 result=evaluate_trainer_evidence({key:True for key in REQUIRED_TRAINER_EVIDENCE});assert result['eligibleForHumanReview'];assert result['automaticApproval'] is False
def test_missing_participant_feedback_blocks_review():
 evidence={key:True for key in REQUIRED_TRAINER_EVIDENCE if key!='participant_feedback'};assert 'participant_feedback' in evaluate_trainer_evidence(evidence)['missing']
def test_schema_covers_full_replication_loop():
 sql=(Path(__file__).parents[1]/'migrations'/'0159_mission_bridge_training.sql').read_text();
 for table in ('cohorts','cohort_members','sessions','session_attendance','mentor_profiles','mentor_assignments','mentor_supervisions','facilitator_profiles','facilitator_certifications','facilitator_observations','trainer_candidates','trainer_approvals'):assert f'mission_bridge_{table}' in sql
