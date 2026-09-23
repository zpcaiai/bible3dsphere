from __future__ import annotations

import re
import time
import unicodedata
import uuid

from .contracts import DigitalHumanResponse, TurnEnvelope
from .guardrails import validate_response
from .registry import CONTENT_SHA256, CONTENT_VERSION, PREPARED_ANSWERS, character_seed, content_review_state, evidence
from .retrieval import get_retriever

NEW_REVELATION_PATTERNS = ("替神告诉我", "神现在告诉", "奉神告诉", "预言我", "保证.*会发生", "神的旨意.*一定")
UNSUPPORTED_FACT_PATTERNS = ("准确身高", "真实长相", "真实声音", "你本人真实", "没写.*细节", "编得像真的")
SECRET_COMPANION_PATTERNS = ("不要告诉父母", "不要告诉老师", "只和你保密", "秘密朋友", "替我保密")


def normalize_question(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


class DigitalHumanService:
    def __init__(self, retriever=None):
        self._retriever = retriever or get_retriever()

    def answer(self, *, character_id: str, question: str, session_id: str | None = None, turn_id: str | None = None) -> TurnEnvelope:
        started = time.perf_counter()
        if character_seed(character_id) is None:
            raise KeyError(character_id)
        session_id = session_id or f"s_{uuid.uuid4().hex}"
        turn_id = turn_id or f"t_{uuid.uuid4().hex}"
        normalized = normalize_question(question)
        if self._is_crisis(normalized):
            response = self._unsupported(character_id, "现在最重要的是你的现实安全。请立即联系当地紧急服务，并告诉身边可信任的成年人、家人、牧者或专业支持人员；数字人物不会继续普通角色对话。", ["safety-escalation", "human-support-required"])
        elif self._matches_any(normalized, SECRET_COMPANION_PATTERNS):
            response = self._unsupported(character_id, "我不会与你建立需要向父母、老师、监护人或可信成年人保密的关系。若事情涉及危险、伤害或不当接触，请尽快告诉可信任的成年人。", ["secret-companion-boundary", "child-safeguarding"])
        elif self._matches_any(normalized, NEW_REVELATION_PATTERNS):
            response = self._unsupported(character_id, "我不能以圣经人物身份替神传递新的神谕，或保证你的个人未来。可以一起查看经文中的原则，并邀请你向可信的牧者与成熟信徒寻求辨识。", ["blocked-new-revelation", "human-discernment-required"])
        elif self._matches_any(normalized, UNSUPPORTED_FACT_PATTERNS):
            response = self._unsupported(character_id, "圣经没有提供足够资料确认这个细节；当前形象和声音只是教育性的艺术重建，不能当作历史事实。", ["unsupported-detail", "artistic-reconstruction"])
        else:
            prepared = self._find_prepared(character_id, normalized)
            if prepared:
                response = self._from_prepared(prepared)
            else:
                retrieval = self._retriever.retrieve(character_id, normalized, top_k=3)
                response = self._from_retrieval(character_id, retrieval)
        response = validate_response(response)
        state = "READY_TO_SPEAK" if response.speechApproved else ("BLOCKED" if response.groundingLevel == "G0_UNSUPPORTED" else "TEXT_ONLY")
        return TurnEnvelope(
            sessionId=session_id, turnId=turn_id, traceId=uuid.uuid4().hex, state=state,
            response=response, latencyMs=round((time.perf_counter() - started) * 1000, 3),
        )

    @staticmethod
    def _matches_any(question: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, question, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _is_crisis(question: str) -> bool:
        try:
            from safety_scan import scan_crisis
            result = scan_crisis(question)
            if result and (result.get("is_crisis") or result.get("riskLevel") in {"orange", "red", "high", "critical"}):
                return True
        except Exception:
            pass
        return bool(re.search(r"自杀|自残|不想活|结束生命|伤害自己", question))

    @staticmethod
    def _find_prepared(character_id: str, question: str):
        candidates = [item for item in PREPARED_ANSWERS if item.character_id == character_id]
        return next((item for item in candidates if all(keyword in question for keyword in item.keywords)), None) or next((item for item in candidates if any(keyword in question for keyword in item.keywords)), None)

    @staticmethod
    def _from_prepared(prepared) -> DigitalHumanResponse:
        review_state = content_review_state()
        return DigitalHumanResponse(
            characterId=prepared.character_id, answerType=prepared.answer_type,
            spokenText=prepared.spoken_text, displayText=prepared.spoken_text,
            references=[evidence(locator, support) for locator, support in prepared.references],
            groundingLevel=prepared.grounding_level, relatedCharacters=list(prepared.related_characters),
            relatedEvents=[prepared.id], warnings=[*prepared.warnings, "education-not-revelation", "artistic-reconstruction"],
            contentVersion=CONTENT_VERSION, contentSha256=CONTENT_SHA256,
            contentReviewState=review_state, speechApproved=review_state == "APPROVED",
        )

    @staticmethod
    def _from_retrieval(character_id: str, retrieval: dict[str, object]) -> DigitalHumanResponse:
        hits = retrieval.get("hits") or []
        best = hits[0] if hits else None
        if not isinstance(best, dict) or float(best.get("score") or 0.0) < 0.45:
            return DigitalHumanService._unsupported(
                character_id,
                "目前没有足够且已经过验证的经文证据回答这个问题。为了避免把推断说成事实，本次回答保持关闭。",
                ["no-reviewed-truth-case", "human-review-required"],
            )
        references = [str(value) for value in best.get("references") or []]
        if not references or best.get("grounding") == "G0_UNSUPPORTED":
            return DigitalHumanService._unsupported(
                character_id,
                "检索命中了相关审核用例，但该用例要求保持不确定或拒绝断言；本次不会生成角色化回答。",
                ["retrieved-unsupported-case", "human-review-required"],
            )
        graph_paths = retrieval.get("graphPaths") or []
        related = []
        for path in graph_paths:
            if isinstance(path, dict) and path.get("target") and path["target"] not in related:
                related.append(str(path["target"]))
        locators = "、".join(references[:4])
        text = f"检索系统找到与问题相关的审核证据定位：{locators}。完整人物回答尚未通过独立神学审核，因此这里只显示证据入口，不以人物身份补写经文没有明说的内容。"
        return DigitalHumanResponse(
            characterId=character_id, answerType="FACT", spokenText=text, displayText=text,
            references=[evidence(locator, "CONTEXT_ONLY") for locator in references],
            groundingLevel="G1_INTERPRETIVE_POSSIBILITY", relatedCharacters=related[:24],
            relatedEvents=[str(best.get("truthCaseId"))],
            warnings=[
                "retrieval-only", "human-theology-review-required",
                str(retrieval.get("mode") or "LEXICAL_GRAPH_DEGRADED").lower(),
            ],
            contentVersion=CONTENT_VERSION, contentSha256=CONTENT_SHA256,
            contentReviewState="THEOLOGY_REVIEW", speechApproved=False,
        )

    @staticmethod
    def _unsupported(character_id: str, message: str, warnings: list[str]) -> DigitalHumanResponse:
        return DigitalHumanResponse(
            characterId=character_id, answerType="UNSUPPORTED", spokenText=message, displayText=message,
            references=[], groundingLevel="G0_UNSUPPORTED", relatedCharacters=[], relatedEvents=[], warnings=warnings,
            contentVersion=CONTENT_VERSION, contentSha256=CONTENT_SHA256,
            contentReviewState=content_review_state(), speechApproved=False,
        )
