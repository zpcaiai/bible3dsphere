from __future__ import annotations
REQUIRED_TRAINER_EVIDENCE=('leadership_observation','safeguarding_training','power_boundaries_training','supervisor_recommendation','trial_period','participant_feedback')
FORBIDDEN_SOLE_SIGNALS=('attendance','quiz_score','ai_score','donation','people_recruited')
def evaluate_trainer_evidence(evidence:dict)->dict:
 missing=[key for key in REQUIRED_TRAINER_EVIDENCE if not evidence.get(key)]
 return {'eligibleForHumanReview':not missing,'missing':missing,'automaticApproval':False,'forbiddenSoleSignals':list(FORBIDDEN_SOLE_SIGNALS)}
