from __future__ import annotations

from copy import deepcopy
from typing import Any

from .safety import classify_resistance, precheck


DIFFICULTY_ORDER = ["D0", "D1", "D2", "D3", "D4", "D5"]


def _one_question(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    pieces = [piece for piece in __import__("re").split(r"(?<=[？?])", cleaned) if piece.strip()]
    if not pieces:
        return "最近一次发生这种情况时，具体发生了什么？"
    first = pieces[0].strip()
    if not first.endswith(("?", "？")):
        first = first.rstrip("。.!！") + "？"
    return first


class DialogueEngine:
    """Consent-aware one-question-at-a-time dialogue state machine."""

    def initialize(self, *, session_id: str, case_id: str, report: dict[str, Any], faith_context: str) -> dict[str, Any]:
        questions = [deepcopy(item) for item in report.get("socratic_questions", [])]
        if not questions:
            questions = [{
                "stage": "CLARIFY", "difficulty": "D0",
                "text": "最近一次发生这种情况时，具体发生了什么？",
                "purpose": "获取可观察事实", "requires_consent": False,
            }]
        for question in questions:
            question["text"] = _one_question(question.get("text", ""))
        first = questions[0]
        return {
            "session_id": session_id,
            "case_id": case_id,
            "faith_context": faith_context,
            "status": "QUESTION_ASKED",
            "stage": first.get("stage", "CLARIFY").upper(),
            "difficulty": first.get("difficulty", "D0"),
            "gospel_consent": "not_asked",
            "question_index": 0,
            "questions": questions,
            "current_question": first,
            "turns": [{"speaker": "assistant", "content": first["text"], "stage": first.get("stage", "CLARIFY").upper()}],
            "hypothesis_impacts": [],
            "safety_events": [],
        }

    def receive(self, session: dict[str, Any], *, answer: str, gospel_consent: str | None, sensitivity: str = "normal") -> dict[str, Any]:
        state = deepcopy(session)
        state["turns"].append({"speaker": "user", "content": answer})
        if gospel_consent:
            state["gospel_consent"] = gospel_consent

        safety = precheck(answer, subject_type="self_reflection", sensitivity=sensitivity)
        if safety.status in {"blocked", "safety_hold"}:
            state["status"] = "SAFETY_HOLD" if safety.status == "safety_hold" else "BLOCKED"
            state["current_question"] = None
            state["safety_events"].append(safety.as_dict())
            return state

        resistance = classify_resistance(answer)
        if resistance["type"] == "boundary_setting":
            state["status"] = "PAUSED_BY_USER"
            state["current_question"] = None
            return state

        current_difficulty = state.get("difficulty", "D0")
        current_index = DIFFICULTY_ORDER.index(current_difficulty) if current_difficulty in DIFFICULTY_ORDER else 0
        if resistance["type"] in {"confusion", "fatigue", "fear", "shame_flooding", "trauma_activation", "scrupulosity"}:
            current_index = max(0, current_index - 1)
        elif len(answer.strip()) >= 40 and resistance["type"] == "none":
            current_index = min(len(DIFFICULTY_ORDER) - 1, current_index + 1)
        state["difficulty"] = DIFFICULTY_ORDER[current_index]
        state["last_answer_evaluation"] = {
            "answer_quality": "reflective" if len(answer.strip()) >= 40 else "brief",
            "directness": "unknown_without_model",
            "evidence_value": "user_self_report",
            "resistance_type": resistance["type"],
            "disagreement_is_not_pathology": resistance["type"] == "disagreement",
            "limitations": ["确定性引擎不推断隐藏动机。"],
        }

        next_index = int(state.get("question_index", 0)) + 1
        questions = state.get("questions", [])
        while next_index < len(questions):
            candidate = questions[next_index]
            requires = bool(candidate.get("requires_consent")) or candidate.get("stage", "").lower() == "gospel"
            if requires and state.get("gospel_consent") == "declined":
                next_index += 1
                continue
            if requires and state.get("gospel_consent") != "accepted":
                invitation = {
                    "stage": "GOSPEL_INVITATION", "difficulty": "D4",
                    "text": "你愿意看看基督如何回应这个困境吗？",
                    "purpose": "请求进入福音探索的明确同意", "requires_consent": True,
                }
                state.update(status="QUESTION_ASKED", stage="GOSPEL_INVITATION", current_question=invitation)
                state["turns"].append({"speaker": "assistant", "content": invitation["text"], "stage": "GOSPEL_INVITATION"})
                return state
            break

        if next_index >= len(questions):
            state.update(status="COMPLETED", stage="REVIEW", current_question=None, question_index=next_index)
            return state

        question = deepcopy(questions[next_index])
        question["text"] = _one_question(question["text"])
        state.update(
            status="QUESTION_ASKED",
            stage=question.get("stage", "CLARIFY").upper(),
            current_question=question,
            question_index=next_index,
        )
        state["turns"].append({"speaker": "assistant", "content": question["text"], "stage": state["stage"]})
        return state
