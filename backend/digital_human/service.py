from __future__ import annotations

import re
import time
import unicodedata
import uuid

from .contracts import DigitalHumanResponse, TurnEnvelope
from .guardrails import validate_response
from .registry import CONTENT_SHA256, CONTENT_VERSION, PREPARED_ANSWERS, catalog_artifact, character_seed, content_review_state, evidence
from .retrieval import get_retriever

NEW_REVELATION_PATTERNS = ("替神告诉我", "神现在告诉", "奉神告诉", "预言我", "保证.*会发生", "神的旨意.*一定")
UNSUPPORTED_FACT_PATTERNS = ("准确身高", "真实.{0,12}(?:外貌|长相|声音|原声)", "长什么样", "多高", "你本人真实", "没写.*细节", "编得像真的")
SECRET_COMPANION_PATTERNS = ("不要告诉父母", "不要告诉老师", "只和你保密", "秘密朋友", "替我保密")
PREPARED_TOPICS = {"moses-call": "moses-burning-bush"}


def question_key(value: str) -> str:
    return "".join(ch for ch in normalize_question(value).casefold() if ch.isalnum())


def normalize_question(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


class DigitalHumanService:
    def __init__(self, retriever=None):
        self._retriever = retriever or get_retriever()

    def answer(self, *, character_id: str, question: str, session_id: str | None = None, turn_id: str | None = None, context_topic_ids: list[str] | None = None) -> TurnEnvelope:
        started = time.perf_counter()
        if character_seed(character_id) is None:
            raise KeyError(character_id)
        session_id = session_id or f"s_{uuid.uuid4().hex}"
        turn_id = turn_id or f"t_{uuid.uuid4().hex}"
        normalized = normalize_question(question)
        character = next(item for item in catalog_artifact()["characters"] if item["id"] == character_id)
        topics = {item["id"]: item for item in character["truthCases"]}
        context_ids = context_topic_ids or []
        if len(context_ids) > 4 or any(topic_id not in topics for topic_id in context_ids):
            raise ValueError("context topics must belong to the active character")
        exact = next((item for item in topics.values() if question_key(item["question"]) == question_key(normalized)), None)
        followup = not exact and bool(context_ids) and bool(re.fullmatch(
            r"(?:请|那|再|继续|那么|能否|可以)?(?:解释一下|展开说明|详细说说|相关经文|经文出处|出处|证据|还有哪些经文|继续这个话题|再解释一下)(?:呢|吗|是什么)?[？?。.!！]*", normalized,
        ))
        known_scriptural_question = exact and exact["expected"].get("mustReference") and exact["expected"].get("grounding") != "G0_UNSUPPORTED"
        if not known_scriptural_question and self._is_crisis(normalized):
            response = self._unsupported(character_id, "现在最重要的是你的现实安全。请立即联系当地紧急服务，并告诉身边可信任的成年人、家人、牧者或专业支持人员；数字人物不会继续普通角色对话。", ["safety-escalation", "human-support-required"])
        elif self._matches_any(normalized, SECRET_COMPANION_PATTERNS):
            response = self._unsupported(character_id, "我不会与你建立需要向父母、老师、监护人或可信成年人保密的关系。若事情涉及危险、伤害或不当接触，请尽快告诉可信任的成年人。", ["secret-companion-boundary", "child-safeguarding"])
        elif self._matches_any(normalized, NEW_REVELATION_PATTERNS):
            response = self._unsupported(character_id, "我不能以圣经人物身份替神传递新的神谕，或保证你的个人未来。可以一起查看经文中的原则，并邀请你向可信的牧者与成熟信徒寻求辨识。", ["blocked-new-revelation", "human-discernment-required"])
        elif self._matches_any(normalized, UNSUPPORTED_FACT_PATTERNS):
            if known_scriptural_question:
                response = self._from_retrieval(character_id, self._retriever.retrieve(character_id, normalized, top_k=3))
                response.warnings.append("artistic-reconstruction-not-authentic")
            else:
                response = self._unsupported(character_id, "圣经没有提供足够资料确认这个细节；当前形象和声音只是教育性的艺术重建，不能当作历史事实。", ["unsupported-detail", "artistic-reconstruction"])
        elif exact and (exact["expected"].get("grounding") == "G0_UNSUPPORTED" or not exact["expected"].get("mustReference")):
            response = self._unsupported(character_id, "这个目录用例要求保持不确定：现有材料不足以作出确定回答，也不会把传统、推测或艺术重建说成经文事实。", ["truth-case-unsupported", "human-review-required"])
            response.relatedEvents = [exact["id"]]
        elif followup:
            topic = topics[context_ids[-1]]
            if topic["expected"].get("grounding") == "G0_UNSUPPORTED" or not topic["expected"].get("mustReference"):
                response = self._unsupported(character_id, "上一个话题仍缺少足够证据，追问不会使不确定内容成为事实。", ["context-unsupported", "human-review-required"])
            else:
                response = self._from_retrieval(character_id, self._retriever.retrieve(character_id, topic["question"], top_k=3))
                response.warnings.append("session-topic-context")
        else:
            retrieval = self._retriever.retrieve(character_id, normalized, top_k=3)
            best = next(iter(retrieval.get("hits") or []), {})
            unsupported_match = float(best.get("score") or 0) >= 0.45 and (best.get("grounding") == "G0_UNSUPPORTED" or not best.get("references"))
            prepared = self._find_prepared(character_id, normalized, exact)
            if unsupported_match:
                response = self._from_retrieval(character_id, retrieval)
            elif prepared:
                response = self._from_prepared(prepared)
            else:
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
    def _find_prepared(character_id: str, question: str, exact=None):
        candidates = [item for item in PREPARED_ANSWERS if item.character_id == character_id]
        if exact:
            return next((item for item in candidates if PREPARED_TOPICS.get(item.id, item.id) == exact["id"]), None)
        anchors = {
            "moses-call": ("荆棘", "燃烧", "呼召"),
            "david-spare-saul": ("扫罗",), "david-goliath": ("歌利亚",),
            "peter-restoration": ("不认", "恢复"), "paul-conversion": ("大马士革", "归信", "从逼迫"),
        }
        for item in candidates:
            if not any(anchor in question for anchor in anchors[item.id]):
                continue
            if item.id == "david-spare-saul" and not any(word in question for word in ("杀", "伤害", "放过", "克制")):
                continue
            return item
        return None

    @staticmethod
    def _from_prepared(prepared) -> DigitalHumanResponse:
        review_state = content_review_state()
        return DigitalHumanResponse(
            characterId=prepared.character_id, answerType=prepared.answer_type,
            spokenText=prepared.spoken_text, displayText=prepared.spoken_text,
            references=[evidence(locator, support) for locator, support in prepared.references],
            groundingLevel=prepared.grounding_level, relatedCharacters=list(prepared.related_characters),
            relatedEvents=[PREPARED_TOPICS.get(prepared.id, prepared.id)], warnings=[*prepared.warnings, "education-not-revelation", "artistic-reconstruction"],
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
