from __future__ import annotations


def build_meeting_prep(
    case_id: str,
    meeting_purpose: str,
    user_selected_focus: list[str],
    last_agreements: list[str],
    evidence_summary: list[dict],
    uncertainties: list[str],
    priority_question: str,
    gospel_truth: str,
    action_option: str,
    do_not_use_language: list[str],
) -> dict:
    if priority_question.count("?") + priority_question.count("？") > 1:
        raise ValueError("Meeting prep must contain one priority question.")

    return {
        "prep_id": f"prep-{case_id}",
        "case_id": case_id,
        "meeting_purpose": meeting_purpose,
        "user_selected_focus": user_selected_focus,
        "last_agreements": last_agreements,
        "evidence_summary": evidence_summary,
        "uncertainties": uncertainties,
        "priority_question": priority_question,
        "gospel_truth": gospel_truth,
        "action_option": action_option,
        "do_not_use_language": do_not_use_language,
        "referral_check": {"required": False},
        "post_meeting_recording_scope": [
            "user-approved-summary",
            "agreed-next-step",
            "safety-or-referral-decision",
        ],
    }
